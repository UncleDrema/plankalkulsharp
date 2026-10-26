const test = require("node:test"),
  assert = require("node:assert/strict"),
  fs = require("node:fs");
const { JSDOM } = require("jsdom");
function surface(view) {
  const messages = [];
  const dom = new JSDOM(
    `<body data-view="${view}"><main id="app"></main></body>`,
    { runScripts: "outside-only" },
  );
  dom.window.acquireVsCodeApi = () => ({
    postMessage: (m) => messages.push(m),
  });
  dom.window.eval(
    fs.readFileSync(require.resolve("../media/workbench.js"), "utf8"),
  );
  const receive = (data) =>
    dom.window.dispatchEvent(new dom.window.MessageEvent("message", { data }));
  return { dom, document: dom.window.document, messages, receive };
}
test("notation navigates by version, escapes source and disables stale formulas", () => {
  const v = surface("notation");
  v.receive({
    kind: "notation",
    uri: "file:///x.pk",
    documentVersion: 7,
    rows: [
      {
        kind: "Assignment",
        line: 2,
        column: 0,
        endLine: 2,
        endColumn: 8,
        depth: 0,
        cells: [
          {
            text: "<script>bad</script>",
            index: "0",
            component: "",
            structure: "1.32",
          },
          { text: "→\u0323" },
          { text: "W³" },
        ],
      },
    ],
  });
  const formula = v.document.querySelector(".formula");
  assert.equal(v.document.querySelectorAll("script").length, 0);
  assert.equal(
    v.document.querySelector(".conditional-arrow circle").getAttribute("cx"),
    "15",
  );
  assert.equal(v.document.querySelector("sup").textContent, "3");
  v.receive({
    kind: "execution",
    uri: "file:///x.pk",
    version: 7,
    line: 2,
    column: 0,
  });
  assert.ok(formula.classList.contains("executing"));
  assert.equal(formula.getAttribute("aria-current"), "step");
  v.receive({
    kind: "execution",
    uri: "file:///other.pk",
    version: 7,
    line: 2,
  });
  assert.ok(!formula.classList.contains("executing"));
  v.receive({ kind: "execution", uri: "file:///x.pk", version: 6, line: 2 });
  assert.ok(!formula.classList.contains("executing"));
  formula.click();
  assert.equal(v.messages.at(-1).version, 7);
  assert.equal(v.messages.at(-1).range.line, 2);
  v.receive({ kind: "loading", text: "pending" });
  assert.ok(formula.classList.contains("stale"));
  v.receive({ kind: "error", text: "syntax" });
  assert.equal(v.document.querySelectorAll(".formula").length, 0);
  v.dom.window.close();
});
test("monitor keeps active tab, exact Int64 fields, snapshot ownership and final data", () => {
  const v = surface("monitor");
  const run = {
    id: "a",
    name: "x.pk",
    state: "paused",
    started: Date.now(),
    delay: 2,
    heapSize: 64,
    memory: [],
    sequence: 2,
    output: "2",
    stats: {
      stats: {
        allocations: 1,
        frees: 0,
        usedBytes: 8,
        freeBytes: 56,
        peakUsedBytes: 8,
        largestFreeBlock: 56,
      },
      objects: [
        {
          handle: "1",
          typeName: "node",
          offset: 0,
          size: 8,
          location: "x.pk:2",
        },
      ],
      blocks: [],
    },
    inspection: {
      handle: "1",
      snapshotSequence: 2,
      fields: [{ path: "0", kind: "int64", value: "9223372036854775807" }],
    },
    heapPage: {
      offset: 0,
      bytes: [7, 0, 0, 0, 0, 0, 0, 0, null],
      objects: [{ handle: "1", offset: 0, size: 8, typeName: "node" }],
      snapshotSequence: 2,
    },
    selectedObject: "1",
  };
  const receive = () =>
    v.receive({
      kind: "monitor",
      selected: "a",
      runs: [{ id: "a", name: "x.pk", state: run.state }],
      run,
    });
  receive();
  v.document.querySelector("[data-tab=memory]").click();
  assert.match(v.document.body.textContent, /9223372036854775807/);
  v.document.querySelector("[data-tab=hex]").click();
  assert.equal(v.document.querySelectorAll(".chosen").length, 8);
  const offset = v.document.querySelector("[data-heap-offset]");
  offset.focus();
  offset.value = "32";
  offset.dispatchEvent(new v.dom.window.Event("input"));
  receive();
  assert.equal(v.document.activeElement.value, "32");
  run.finished = Date.now();
  run.state = "завершён";
  receive();
  assert.ok(
    v.document.querySelector("[data-tab=hex]").classList.contains("active"),
  );
  assert.equal(v.document.querySelectorAll(".chosen").length, 8);
  v.dom.window.close();
});
test("library templates are searchable without a source", () => {
  const v = surface("library");
  v.receive({
    kind: "library",
    plans: [
      {
        name: "reverse",
        types: ["item"],
        source: "P0",
        description: "Разворот списка",
        example: "reverse([1])",
      },
    ],
  });
  assert.match(v.document.body.textContent, /Разворот/);
  const input = v.document.querySelector("input");
  input.value = "missing";
  input.dispatchEvent(new v.dom.window.Event("input"));
  assert.match(v.document.body.textContent, /не найдены/);
  v.dom.window.close();
});

test("inline launch keeps edited fields across snapshots and submits exact JSON", () => {
  const v = surface("monitor");
  const state = {
    kind: "monitor",
    runs: [],
    launch: {
      key: 1,
      path: "example.pk",
      argumentsText: "[]",
      heapSize: 1024,
      delay: 0,
      startPaused: true,
    },
  };
  v.receive(state);
  const args = v.document.querySelector('[name="argumentsText"]');
  args.value = "[9223372036854775807]";
  args.dispatchEvent(new v.dom.window.Event("input"));
  args.focus();
  v.receive(state);
  assert.equal(v.document.activeElement, args);
  assert.equal(args.value, "[9223372036854775807]");
  v.document
    .querySelector("form")
    .dispatchEvent(new v.dom.window.Event("submit", { cancelable: true }));
  assert.equal(v.messages.at(-1).command, "launch");
  assert.equal(
    v.messages.at(-1).options.argumentsText,
    "[9223372036854775807]",
  );
  assert.equal(v.messages.at(-1).options.startPaused, true);
  v.receive({ kind: "launchError", text: "Ошибка проверки" });
  assert.match(
    v.document.querySelector('[role="alert"]').textContent,
    /Ошибка/,
  );
  assert.equal(v.document.querySelector('[type="submit"]').disabled, false);
  v.dom.window.close();
});
