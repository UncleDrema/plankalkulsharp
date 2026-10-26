const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const { createRequire } = require("node:module");

function extension() {
  const commands = [],
    prompts = [],
    messages = [];
  const vscode = {
    ThemeColor: class {},
    window: {
      createTextEditorDecorationType: () => ({}),
      showInputBox: async (p) => {
        prompts.push(p);
        return p.title.includes("Задержка") ? undefined : p.value;
      },
      showQuickPick: async (choices) => choices[0],
    },
    commands: { executeCommand: async (...args) => commands.push(args) },
    workspace: {
      getConfiguration: () => ({
        get: (key) =>
          ({ heapSize: 1048576, delayMs: 0, startPaused: true })[key],
      }),
    },
  };
  const filename = require.resolve("../src/extension.js");
  const realRequire = createRequire(filename);
  const sandbox = {
    require: (id) =>
      id === "vscode"
        ? vscode
        : id === "vscode-languageclient/node"
          ? {}
          : realRequire(id),
    module: { exports: {} },
    setTimeout,
    clearTimeout,
  };
  vm.createContext(sandbox);
  vm.runInContext(
    fs.readFileSync(filename, "utf8") +
      `
    module.exports = { openMonitor, runProgram, followsExecution, sendExecutionPosition, configureLaunch, snapshotUri, getLaunch: () => launchTarget, matchesExecution, setDocument: doc => activeDocument = doc,
      setup(run) {
        context = { workspaceState: { get: () => "[]", update: async () => {} } };
        runs.set(run.id, run); selectedRun = run.id;
        activeDocument = { uri: { toString: () => snapshotUri(run) }, version: 1 };
        notation = { webview: { postMessage: m => __messages.push(m) } };
      }
    };`,
    Object.assign(sandbox, { __messages: messages }),
  );
  return { api: sandbox.module.exports, commands, prompts, messages };
}

test("monitor uses the bottom panel rather than a third editor column", async () => {
  const { api, commands } = extension();
  await api.openMonitor();
  assert.deepEqual(
    commands.map((c) => c[0]),
    ["workbench.action.positionPanelBottom", "plankalkul.monitorView.focus"],
  );
  const manifest = require("../package.json");
  assert.equal(
    manifest.contributes.viewsContainers.panel[0].id,
    "plankalkul-machine",
  );
  assert.equal(
    manifest.contributes.views["plankalkul-machine"][0].type,
    "webview",
  );
});

test("delayed execution updates notation and completion clears it", () => {
  const { api, messages } = extension();
  const run = {
    id: "a",
    name: "example.pk",
    number: 1,
    state: "running",
    delay: 250,
    line: 9,
    column: 2,
  };
  api.setup(run);
  api.sendExecutionPosition();
  assert.equal(messages.at(-1).line, 9);
  run.line = 10;
  api.sendExecutionPosition();
  assert.equal(messages.at(-1).line, 10);
  run.finished = 1;
  api.sendExecutionPosition();
  assert.equal(messages.at(-1).line, 0);
});

test("original source is eligible only while its exact buffer matches the run", () => {
  const { api, messages } = extension();
  const run = {
    id: "r",
    name: "sample.pk",
    number: 1,
    path: "C:/sample.pk",
    text: "old text",
    state: "paused",
    line: 3,
  };
  let text = run.text;
  const doc = {
    uri: {
      scheme: "file",
      fsPath: run.path,
      toString: () => "file:///C:/sample.pk",
    },
    version: 1,
    getText: () => text,
  };
  api.setup(run);
  api.setDocument(doc);
  assert.equal(api.matchesExecution(doc, run), true);
  api.sendExecutionPosition();
  assert.equal(messages.at(-1).line, 3);
  text = "edited text";
  doc.version++;
  assert.equal(api.matchesExecution(doc, run), false);
  api.sendExecutionPosition();
  assert.equal(messages.at(-1).line, 0);
  const snapshot = {
    uri: { toString: () => api.snapshotUri(run) },
    version: 1,
  };
  api.setDocument(snapshot);
  api.sendExecutionPosition();
  assert.equal(messages.at(-1).line, 3);
  text = run.text;
  assert.equal(api.matchesExecution(doc, run), true);
  assert.equal(
    api.matchesExecution(doc, { ...run, text: "another run" }),
    false,
  );
});

test("inline launch validates before building and snapshot keeps recognizable filename", async () => {
  const { api, prompts } = extension();
  api.setup({ id: "old", name: "sample.pk", number: 1 });
  const doc = {
    languageId: "plankalkul",
    uri: { scheme: "file", fsPath: "sample.pk" },
    getText: () => "source",
  };
  api.configureLaunch(doc, {
    argumentsText: "[8,4]",
    heapSize: 2048,
    delay: 300,
    startPaused: false,
  });
  assert.equal(api.getLaunch().argumentsText, "[8,4]");
  await assert.rejects(
    api.runProgram(doc, {
      argumentsText: "[]",
      heapSize: 9,
      delay: 0,
      startPaused: false,
    }),
    /кратным 8/,
  );
  assert.equal(prompts.length, 0);
  assert.match(
    decodeURIComponent(
      api.snapshotUri({ id: "a", name: "пример.pk", number: 2 }),
    ),
    /пример — снимок #2.pk$/,
  );
});
