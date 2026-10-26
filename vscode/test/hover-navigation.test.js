const test = require("node:test");
const assert = require("node:assert/strict");
const { HoverNavigation, COMMAND } = require("../src/hover-navigation");

function setup(request) {
  const commands = [];
  const doc = { uri: { toString: () => "file:///test.pk" }, version: 1 };
  const editor = { document: doc };
  const vscode = {
    MarkdownString: class {
      constructor(value) {
        this.value = value;
      }
    },
    Hover: class {
      constructor(content, range) {
        this.contents = [content];
        this.range = range;
      }
    },
    Selection: class {
      constructor(start, end) {
        this.start = start;
        this.end = end;
      }
    },
    window: { activeTextEditor: editor },
    commands: { executeCommand: async (...args) => commands.push(args) },
  };
  return { nav: new HoverNavigation(vscode, request), doc, editor, commands };
}
const position = { line: 2, character: 4 };
const token = { isCancellationRequested: false };
const next = async () => ({
  contents: [{ value: "Root [pair](plankalkul-type:pair)" }],
});

test("nested types replace the same hover with back navigation and restricted commands", async () => {
  const calls = [];
  const s = setup(async (method, params) => {
    calls.push(params.name);
    return { contents: { value: params.name + " [int](plankalkul-type:int)" } };
  });
  const root = await s.nav.provide(s.doc, position, token, next);
  assert.deepEqual(root.contents[0].isTrusted, { enabledCommands: [COMMAND] });
  assert.match(root.contents[0].value, /command:plankalkul.hoverType/);
  const id = s.nav.state.id;
  await s.nav.navigate(id, "pair");
  let card = await s.nav.provide(s.doc, position, token, () => {
    throw Error("unexpected server hover");
  });
  assert.match(card.contents[0].value, /Назад/);
  await s.nav.navigate(id, "int");
  assert.equal(s.nav.state.pages.length, 3);
  await s.nav.navigate(id, "@back");
  assert.match(s.nav.state.pages.at(-1), /^pair/);
  await s.nav.navigate(id, "@root");
  assert.equal(s.nav.state.pages.length, 1);
  assert.deepEqual(calls, ["pair", "int"]);
  assert.deepEqual(s.editor.selection.start, position);
  assert.ok(
    s.commands.every((c) =>
      ["editor.action.hideHover", "editor.action.showHover"].includes(c[0]),
    ),
  );
});

test("stale documents and superseded type responses do not update hover", async () => {
  let resolve;
  const s = setup(
    () =>
      new Promise((r) => {
        resolve = r;
      }),
  );
  await s.nav.provide(s.doc, position, token, next);
  const pending = s.nav.navigate(s.nav.state.id, "pair");
  s.doc.version++;
  resolve({ contents: { value: "old" } });
  await pending;
  assert.equal(s.commands.length, 0);
  assert.equal(s.nav.state.pages.length, 1);
  await s.nav.navigate(s.nav.state.id, "@back");
  assert.equal(s.commands.length, 0);
});
