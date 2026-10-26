"use strict";
const COMMAND = "plankalkul.hoverType";

// Native Markdown hovers have no mutable DOM. Refresh the same anchored hover
// through a provider, retaining a small navigation stack for named types.
class HoverNavigation {
  constructor(vscode, request) {
    this.vscode = vscode;
    this.request = request;
    this.serial = 0;
    this.pending = 0;
  }
  sameDocument(doc, state) {
    return (
      state && doc.uri.toString() === state.uri && doc.version === state.version
    );
  }
  async provide(doc, position, token, next) {
    const state = this.state;
    if (
      this.sameDocument(doc, state) &&
      state.pages.length > 1 &&
      position.line === state.position.line &&
      position.character === state.position.character
    )
      return this.render(state);
    const ticket = ++this.serial;
    const hover = await next(doc, position, token);
    if (!hover || token.isCancellationRequested || ticket !== this.serial)
      return hover;
    this.state = {
      id: ticket,
      uri: doc.uri.toString(),
      version: doc.version,
      position,
      range: hover.range,
      pages: [
        hover.contents
          .map((c) => (typeof c === "string" ? c : c.value || ""))
          .join("\n\n"),
      ],
    };
    return this.render(this.state);
  }
  link(state, target, label) {
    return `[${label}](command:${COMMAND}?${encodeURIComponent(JSON.stringify([state.id, target]))})`;
  }
  render(state) {
    let text = state.pages
      .at(-1)
      .replace(
        /\(plankalkul-type:([A-Za-z_]\w*)\)/g,
        (_, name) =>
          `(command:${COMMAND}?${encodeURIComponent(JSON.stringify([state.id, name]))})`,
      );
    if (state.pages.length > 1)
      text =
        this.link(state, "@back", "Назад") +
        " · " +
        this.link(state, "@root", "К исходной подсказке") +
        "\n\n" +
        text;
    const markdown = new this.vscode.MarkdownString(text);
    markdown.isTrusted = { enabledCommands: [COMMAND] };
    return new this.vscode.Hover(markdown, state.range);
  }
  async navigate(id, target) {
    const state = this.state,
      editor = this.vscode.window.activeTextEditor;
    if (
      !state ||
      state.id !== id ||
      state.id !== this.serial ||
      !editor ||
      !this.sameDocument(editor.document, state)
    )
      return;
    if (
      typeof target !== "string" ||
      !/^(?:[A-Za-z_]\w*|@back|@root)$/.test(target)
    )
      return;
    const ticket = ++this.pending;
    if (target === "@back") {
      if (state.pages.length > 1) state.pages.pop();
    } else if (target === "@root") state.pages.splice(1);
    else {
      const result = await this.request("plankalkul/type", {
        textDocument: { uri: state.uri },
        name: target,
        position: state.position,
      });
      if (
        ticket !== this.pending ||
        this.state !== state ||
        state.id !== this.serial ||
        this.vscode.window.activeTextEditor !== editor ||
        !this.sameDocument(editor.document, state)
      )
        return;
      if (!result?.contents?.value) return;
      if (state.pages.length >= 32) state.pages.splice(1, 1);
      state.pages.push(result.contents.value);
    }
    // showHover anchors at the caret. Keep it at the original hovered symbol,
    // never navigate to the type declaration or open another document.
    editor.selection = new this.vscode.Selection(
      state.position,
      state.position,
    );
    await this.vscode.commands.executeCommand("editor.action.hideHover");
    await this.vscode.commands.executeCommand("editor.action.showHover", {
      focus: "autoFocusImmediately",
    });
  }
}
module.exports = { HoverNavigation, COMMAND };
