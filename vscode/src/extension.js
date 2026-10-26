"use strict";
const vscode = require("vscode");
const { LanguageClient } = require("vscode-languageclient/node");
const { spawn } = require("node:child_process");
const fs = require("node:fs/promises");
const path = require("node:path");
const { prepareSession } = require("./sessions");
const {
  HoverNavigation,
  COMMAND: HOVER_COMMAND,
} = require("./hover-navigation");
const hoverNavigation = new HoverNavigation(vscode, (method, params) =>
  client.sendRequest(method, params),
);
let sessionDirectory;
const { randomBytes, randomUUID } = require("node:crypto");
const {
  WorkerClient,
  killTree,
  bounded,
  parseArguments,
} = require("./worker-client");
let client,
  context,
  log,
  notation,
  monitor,
  library,
  helpPanel,
  activeDocument,
  notationTimer,
  notationRequest = 0,
  cancellation;
const runs = new Map(),
  librarySources = new Map();
let launchTarget,
  launchRevision = 0;
let selectedRun,
  renderTimer,
  libraryTimer,
  libraryRequest = 0;
const highlight = vscode.window.createTextEditorDecorationType({
  backgroundColor: new vscode.ThemeColor("editor.selectionHighlightBackground"),
  border: "1px solid",
  borderColor: new vscode.ThemeColor("editor.selectionHighlightBorder"),
});
const execution = vscode.window.createTextEditorDecorationType({
  isWholeLine: true,
  backgroundColor: new vscode.ThemeColor(
    "editor.stackFrameHighlightBackground",
  ),
});
const settings = () => vscode.workspace.getConfiguration("plankalkul");
async function python() {
  const configured = settings().get("python");
  if (configured) return configured;
  for (const folder of vscode.workspace.workspaceFolders || []) {
    const candidate = path.join(
      folder.uri.fsPath,
      ".venv",
      process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
    );
    try {
      await fs.access(candidate);
      return candidate;
    } catch {}
  }
  return "python";
}
function panel(kind, title, column = vscode.ViewColumn.Beside) {
  const media = vscode.Uri.joinPath(context.extensionUri, "media");
  const p = vscode.window.createWebviewPanel(
    "plankalkul." + kind,
    title,
    column,
    {
      enableScripts: true,
      localResourceRoots: [media],
      retainContextWhenHidden: true,
    },
  );
  configureWebview(p.webview, kind);
  return p;
}
function configureWebview(webview, kind) {
  const media = vscode.Uri.joinPath(context.extensionUri, "media");
  webview.options = { enableScripts: true, localResourceRoots: [media] };
  const nonce = randomBytes(16).toString("hex");
  const css = webview.asWebviewUri(vscode.Uri.joinPath(media, "workbench.css"));
  const js = webview.asWebviewUri(vscode.Uri.joinPath(media, "workbench.js"));
  webview.html = `<!doctype html><html lang="ru"><head><meta charset="UTF-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource}; script-src 'nonce-${nonce}';"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="${css}"></head><body data-view="${kind}"><main id="app"></main><script nonce="${nonce}" src="${js}"></script></body></html>`;
}
async function startClient() {
  if (client) await client.stop();
  client = new LanguageClient(
    "plankalkul",
    "Plankalkül",
    {
      command: await python(),
      args: ["-m", "plankalkulsharp.lsp"],
      options: {
        env: { ...process.env, PYTHONIOENCODING: "utf-8" },
        windowsHide: true,
      },
    },
    {
      documentSelector: [
        { language: "plankalkul", scheme: "file" },
        { language: "plankalkul", scheme: "untitled" },
        { language: "plankalkul", scheme: "plankalkul-run" },
      ],
      outputChannel: log,
      middleware: {
        provideHover: (doc, position, token, next) =>
          hoverNavigation.provide(doc, position, token, next),
      },
    },
  );
  await client.start();
}
async function projectNotation() {
  if (!notation || !activeDocument || !client) return;
  const doc = activeDocument,
    version = doc.version,
    id = ++notationRequest;
  cancellation?.cancel();
  cancellation?.dispose();
  cancellation = new vscode.CancellationTokenSource();
  notation.webview.postMessage({
    kind: "loading",
    text: "Построение нотации…",
  });
  try {
    const result = await client.sendRequest(
      "plankalkul/notation",
      { textDocument: { uri: doc.uri.toString() } },
      cancellation.token,
    );
    if (
      id !== notationRequest ||
      doc.version !== version ||
      result.documentVersion !== version
    )
      return;
    notation?.webview.postMessage({ kind: "notation", ...result });
    sendExecutionPosition();
  } catch (error) {
    if (id === notationRequest)
      notation?.webview.postMessage({
        kind: "error",
        text: "Нотация недоступна для текущего текста: " + error.message,
      });
  }
}
function scheduleNotation() {
  clearTimeout(libraryTimer);
  libraryRequest++;
  if (library) {
    library.webview.postMessage({
      kind: "loading",
      text: "Обновление подстановок…",
    });
    libraryTimer = setTimeout(refreshLibrary, 250);
  }
  clearTimeout(notationTimer);
  notationRequest++;
  cancellation?.cancel();
  if (notation) {
    notation.webview.postMessage({
      kind: "loading",
      text: "Текст изменён. Обновление…",
    });
    notationTimer = setTimeout(projectNotation, 250);
  }
}
async function openNotation(document) {
  const doc = document || vscode.window.activeTextEditor?.document;
  if (doc?.uri.scheme === "plankalkul-library")
    throw Error(
      "Для шаблона без конкретных типов используйте «Стандартные планы» и выберите подстановку.",
    );
  if (doc?.languageId === "plankalkul") activeDocument = doc;
  if (!activeDocument) throw Error("Откройте файл .pk");
  if (notation) {
    notation.reveal(vscode.ViewColumn.Two, true);
    await projectNotation();
    return;
  }
  notation = panel("notation", "Нотация Plankalkül", vscode.ViewColumn.Two);
  notation.onDidDispose(() => {
    notation = undefined;
    cancellation?.cancel();
    for (const e of vscode.window.visibleTextEditors)
      e.setDecorations(highlight, []);
  });
  notation.webview.onDidReceiveMessage(async (m) => {
    if (m.command === "ready") await projectNotation();
    if (
      m.command === "source" &&
      activeDocument &&
      m.uri === activeDocument.uri.toString() &&
      m.version === activeDocument.version
    ) {
      const r = m.range;
      if (
        !r ||
        !Number.isInteger(r.line) ||
        r.line < 1 ||
        r.line > activeDocument.lineCount
      )
        return;
      const editor = await vscode.window.showTextDocument(activeDocument, {
        viewColumn: vscode.ViewColumn.One,
        preserveFocus: true,
      });
      const range = editor.document.validateRange(
        new vscode.Range(
          r.line - 1,
          Math.max(0, r.column),
          Math.max(r.line - 1, (r.endLine || r.line) - 1),
          Math.max(0, r.endColumn ?? r.column + 1),
        ),
      );
      editor.setDecorations(highlight, [range]);
      editor.revealRange(
        range,
        vscode.TextEditorRevealType.InCenterIfOutsideViewport,
      );
      if (m.pin)
        editor.selection = new vscode.Selection(range.start, range.end);
    }
    if (m.command === "clear")
      for (const e of vscode.window.visibleTextEditors)
        e.setDecorations(highlight, []);
  });
}
function snapshotUri(run) {
  return (
    "plankalkul-run:/" +
    run.id +
    "/" +
    encodeURIComponent(
      run.name.replace(/\.pk$/i, "") + " — снимок #" + run.number + ".pk",
    )
  );
}
function configureLaunch(doc, previous) {
  launchTarget = {
    key: ++launchRevision,
    path: doc.uri.fsPath,
    name: path.basename(doc.uri.fsPath),
    argumentsText:
      previous?.argumentsText ?? context.workspaceState.get("arguments", "[]"),
    heapSize: previous?.heapSize ?? settings().get("heapSize"),
    delay: previous?.delay ?? settings().get("delayMs"),
    startPaused: previous?.startPaused ?? settings().get("startPaused"),
  };
  refreshMonitor();
}
async function prepareLaunch() {
  let doc = vscode.window.activeTextEditor?.document || activeDocument;
  if (doc?.uri.scheme === "plankalkul-run") {
    const previous = runs.get(doc.uri.path.split("/")[1]);
    if (previous)
      doc = await vscode.workspace.openTextDocument(
        vscode.Uri.file(previous.path),
      );
  }
  if (!doc || doc.uri.scheme !== "file" || doc.languageId !== "plankalkul")
    throw Error("Откройте исходный файл .pk");
  configureLaunch(doc);
  await openMonitor();
}
function matchesExecution(doc, run) {
  if (!doc || !run) return false;
  if (doc.uri.toString() === snapshotUri(run)) return true;
  return (
    doc.uri.scheme === "file" &&
    doc.uri.fsPath === run.path &&
    doc.getText() === run.text
  );
}
function decorateExecution() {
  const run = runs.get(selectedRun);
  for (const editor of vscode.window.visibleTextEditors) {
    editor.setDecorations(
      execution,
      run &&
        followsExecution(run) &&
        run.line > 0 &&
        matchesExecution(editor.document, run)
        ? [new vscode.Range(run.line - 1, 0, run.line - 1, 0)]
        : [],
    );
  }
}
function sendExecutionPosition() {
  const run = runs.get(selectedRun);
  const matches = matchesExecution(activeDocument, run);
  notation?.webview.postMessage({
    kind: "execution",
    uri: activeDocument?.uri.toString(),
    version: activeDocument?.version,
    line: matches && followsExecution(run) ? run.line : 0,
    column: matches ? run.column || 0 : 0,
  });
}
function followsExecution(run) {
  return (
    !run.finished &&
    (run.state === "paused" || (run.state === "running" && run.delay > 0))
  );
}
let pauseNavigation = 0;
async function showPausedPosition(run) {
  const ticket = ++pauseNavigation;
  const current = () =>
    ticket === pauseNavigation &&
    selectedRun === run.id &&
    followsExecution(run);
  let doc = run.sourceDocument;
  if (!doc || doc.isClosed) {
    try {
      doc = await vscode.workspace.openTextDocument(vscode.Uri.file(run.path));
    } catch {
      doc = undefined;
    }
  }
  if (!matchesExecution(doc, run)) {
    doc = await vscode.workspace.openTextDocument(
      vscode.Uri.parse(snapshotUri(run)),
    );
    await vscode.languages.setTextDocumentLanguage(doc, "plankalkul");
  }
  if (!current()) return;
  const editor = await vscode.window.showTextDocument(doc, {
    viewColumn: vscode.ViewColumn.One,
    preserveFocus: true,
  });
  if (!current()) return;
  const range = doc.validateRange(
    new vscode.Range(
      Math.max(0, run.line - 1),
      0,
      Math.max(0, run.line - 1),
      0,
    ),
  );
  editor.setDecorations(execution, [range]);
  editor.revealRange(
    range,
    vscode.TextEditorRevealType.InCenterIfOutsideViewport,
  );
  if (
    !run.navigationShown ||
    activeDocument?.uri.toString() !== doc.uri.toString() ||
    !notation ||
    !notation.visible
  ) {
    run.navigationShown = true;
    activeDocument = doc;
    // Keep controls visible alongside the source and notation.
    // The monitor is a bottom-panel view; editor groups remain code + notation.
    await openNotation(doc);
  }
  if (current()) sendExecutionPosition();
}
async function openHelp() {
  if (helpPanel) {
    helpPanel.reveal();
    return;
  }
  helpPanel = panel("help", "Справка Plankalkül");
  helpPanel.onDidDispose(() => (helpPanel = undefined));
  helpPanel.webview.onDidReceiveMessage(async (m) => {
    if (m.command === "ready")
      try {
        helpPanel?.webview.postMessage({
          kind: "help",
          topics: await client.sendRequest("plankalkul/help"),
        });
      } catch (e) {
        helpPanel?.webview.postMessage({ kind: "error", text: e.message });
      }
  });
}
async function getLibrary() {
  const plans = await client.sendRequest("plankalkul/library");
  for (const p of plans)
    librarySources.set("plankalkul-library:/" + p.name + ".pk", p.source);
  return plans;
}
async function refreshLibrary() {
  if (!library) return;
  const request = ++libraryRequest,
    doc = activeDocument,
    version = doc?.version;
  try {
    const plans = await getLibrary();
    let specializations = [];
    if (doc)
      try {
        const result = await client.sendRequest("plankalkul/notation", {
          textDocument: { uri: doc.uri.toString() },
        });
        if (result.documentVersion === version)
          specializations = result.libraries;
      } catch {}
    if (request !== libraryRequest || doc?.version !== version) return;
    library?.webview.postMessage({
      kind: "library",
      plans,
      specializations,
      sourceLabel: doc
        ? doc.uri.toString() + " · версия " + version
        : "Без программы",
    });
  } catch (e) {
    if (request === libraryRequest)
      library?.webview.postMessage({ kind: "error", text: e.message });
  }
}
async function openLibrary() {
  if (library) {
    library.reveal();
    await refreshLibrary();
    return;
  }
  library = panel("library", "Стандартные планы");
  library.onDidDispose(() => {
    library = undefined;
    libraryRequest++;
  });
  library.webview.onDidReceiveMessage(async (m) => {
    if (m.command === "ready") await refreshLibrary();
    if (m.command === "openPlan" && typeof m.name === "string") {
      const uri = vscode.Uri.parse("plankalkul-library:/" + m.name + ".pk");
      if (librarySources.has(uri.toString()))
        await vscode.window.showTextDocument(
          await vscode.workspace.openTextDocument(uri),
          vscode.ViewColumn.One,
        );
    }
  });
}
function snapshot(run) {
  return {
    id: run.id,
    name: run.name,
    state: run.state,
    exitCode: run.exitCode,
    incomplete: run.incomplete,
    forced: run.forced,
    output: run.output,
    diagnostics: run.diagnostics,
    buildDiagnostics: run.buildDiagnostics,
    memory: run.memory,
    stats: run.snapshot,
    sequence: run.sequence,
    heapPage: run.heapPage,
    inspection: run.inspection,
    process: run.processMetrics,
    selectedObject: run.selectedObject,
    delay: run.delay,
    heapSize: run.heapSize,
    line: run.line,
    started: run.started,
    finished: run.finished,
  };
}
function refreshMonitor() {
  if (renderTimer) return;
  renderTimer = setTimeout(() => {
    renderTimer = undefined;
    monitor?.webview.postMessage({
      kind: "monitor",
      launch: launchTarget,
      runs: [...runs.values()].map((r, index) => ({
        id: r.id,
        name: `#${index + 1} ${r.name}`,
        state: r.state,
      })),
      selected: selectedRun,
      run: runs.has(selectedRun) ? snapshot(runs.get(selectedRun)) : null,
    });
  }, 200);
}
async function openMonitor() {
  await vscode.commands.executeCommand("workbench.action.positionPanelBottom");
  await vscode.commands.executeCommand("plankalkul.monitorView.focus");
  refreshMonitor();
}
function resolveMonitor(view) {
  monitor = view;
  configureWebview(view.webview, "monitor");
  monitor.onDidDispose(() => (monitor = undefined));
  monitor.webview.onDidReceiveMessage(async (m) => {
    if (m.command === "ready") {
      refreshMonitor();
      return;
    }
    if (m.command === "selectRun" && runs.has(m.id)) {
      selectedRun = m.id;
      const selected = runs.get(m.id);
      decorateExecution();
      configureLaunch({ uri: { fsPath: selected.path } }, selected);
      if (followsExecution(selected))
        showPausedPosition(selected).catch((e) => log.appendLine(e.message));
      else sendExecutionPosition();
      refreshMonitor();
      return;
    }
    if (m.command === "settings") {
      await vscode.commands.executeCommand(
        "workbench.action.openSettings",
        "@ext:plankalkulsharp.plankalkulsharp",
      );
      return;
    }
    if (m.command === "launch") {
      try {
        if (!launchTarget || m.key !== launchTarget.key)
          throw Error(
            "Файл запуска изменился. Проверьте параметры и нажмите запуск ещё раз.",
          );
        const doc = await vscode.workspace.openTextDocument(
          vscode.Uri.file(launchTarget.path),
        );
        await runProgram(doc, m.options);
        monitor?.webview.postMessage({ kind: "launchReady" });
      } catch (e) {
        monitor?.webview.postMessage({ kind: "launchError", text: e.message });
      }
      return;
    }
    const run = runs.get(m.id);
    if (!run) return;
    if (m.command === "snapshot" || m.command === "location") {
      const doc = await vscode.workspace.openTextDocument(
        vscode.Uri.parse(snapshotUri(run)),
      );
      await vscode.languages.setTextDocumentLanguage(doc, "plankalkul");
      const editor = await vscode.window.showTextDocument(
        doc,
        vscode.ViewColumn.One,
      );
      if (!run.finished && run.line > 0) {
        const current = new vscode.Range(run.line - 1, 0, run.line - 1, 0);
        editor.setDecorations(execution, [current]);
        editor.revealRange(current);
      }
      if (m.command === "location" && Number.isInteger(m.line) && m.line > 0) {
        const point = doc.validatePosition(
          new vscode.Position(m.line - 1, Math.max(0, m.column || 0)),
        );
        editor.selection = new vscode.Selection(point, point);
        editor.revealRange(new vscode.Range(point, point));
      }
      return;
    }
    if (m.command === "stop") {
      stopRun(run);
      return;
    }
    if (["pause", "resume", "step"].includes(m.command))
      run.worker?.send(m.command);
    if (
      m.command === "delay" &&
      Number.isInteger(m.value) &&
      m.value >= 0 &&
      m.value <= 1000
    ) {
      run.delay = m.value;
      run.worker?.send("delay", { delayMs: m.value });
    }
    if (
      m.command === "inspect" &&
      typeof m.handle === "string" &&
      /^\d+$/.test(m.handle)
    ) {
      run.selectedObject = m.handle;
      run.inspection = run.inspections?.[m.handle];
      if (run.state === "paused")
        run.worker?.send("inspect", { handle: m.handle });
      const object = run.snapshot?.objects?.find((o) => o.handle === m.handle);
      if (object && !run.finished)
        run.worker?.send("inspectHeap", { offset: object.offset });
      refreshMonitor();
    }
    if (
      m.command === "heap" &&
      Number.isInteger(m.offset) &&
      m.offset >= 0 &&
      m.offset < run.heapSize &&
      !run.finished
    )
      run.worker?.send("inspectHeap", { offset: m.offset });
  });
}
function stopRun(run) {
  if (run.finished) return;
  run.stopping = true;
  run.state = "остановка";
  if (run.build) killTree(run.build);
  else run.worker?.stop();
  refreshMonitor();
}
function build(pythonPath, run) {
  return new Promise((resolve, reject) => {
    const child = spawn(
      pythonPath,
      [
        "-m",
        "plankalkulsharp",
        "build",
        run.path,
        "--stdin",
        "-o",
        run.directory,
        "--json",
      ],
      { windowsHide: true, env: { ...process.env, PYTHONIOENCODING: "utf-8" } },
    );
    run.build = child;
    let stdout = "";
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (s) => (stdout += s));
    child.stderr.on("data", (s) => {
      run.diagnostics = bounded(run.diagnostics, s);
      log.append(s);
      refreshMonitor();
    });
    child.on("error", reject);
    child.on("close", () => {
      run.build = undefined;
      try {
        const result = JSON.parse(stdout);
        if (!result.ok) {
          run.buildDiagnostics = result.diagnostics;
          throw Error(result.diagnostics.map((d) => d.message).join("\n"));
        }
        resolve(result);
      } catch (e) {
        reject(e);
      }
    });
    child.stdin.on("error", () => {});
    child.stdin.end(run.text, "utf8");
  });
}
async function runProgram(document, options) {
  const doc = document || vscode.window.activeTextEditor?.document;
  if (!doc || doc.languageId !== "plankalkul" || doc.uri.scheme !== "file")
    throw Error(
      "Откройте именованный .pk. Для нового файла сначала выберите «Сохранить как».",
    );
  // Capture the current buffer when the inline launch form is submitted.
  const text = doc.getText(),
    sourcePath = doc.uri.fsPath;
  const { argumentsText, heapSize, delay, startPaused } = options || {};
  if (typeof argumentsText !== "string")
    throw Error("Укажите JSON-массив аргументов");
  parseArguments(argumentsText);
  if (typeof startPaused !== "boolean") throw Error("Укажите режим запуска");
  if (
    !Number.isInteger(heapSize) ||
    heapSize <= 0 ||
    heapSize % 8 ||
    heapSize > 2147483640
  )
    throw Error(
      "Размер кучи должен быть положительным, кратным 8, не больше 2147483640.",
    );
  if (!Number.isInteger(delay) || delay < 0 || delay > 1000)
    throw Error("Задержка должна быть целым числом от 0 до 1000 мс.");
  const run = {
    id: randomUUID(),
    number: runs.size + 1,
    name: path.basename(sourcePath),
    argumentsText,
    startPaused,
    path: sourcePath,
    sourceDocument: doc,
    text,
    state: "сборка",
    output: "",
    diagnostics: "",
    memory: [],
    sequence: 0,
    delay,
    heapSize,
    started: Date.now(),
  };
  await context.workspaceState.update("arguments", argumentsText);
  runs.set(run.id, run);
  selectedRun = run.id;
  await openMonitor();
  refreshMonitor();
  try {
    run.directory = await fs.mkdtemp(path.join(sessionDirectory, "run-"));
    const result = await build(await python(), run);
    if (run.stopping) throw Error("Сборка отменена");
    run.worker = new WorkerClient(
      result.artifact.assemblyPath,
      result.artifact.workerPath,
      {
        heapSize,
        delayMs: delay,
        startPaused,
        arguments: parseArguments(argumentsText),
      },
    );
    run.worker.on("diagnostic", (s) => {
      run.diagnostics = bounded(run.diagnostics, s + "\n");
      refreshMonitor();
    });
    run.worker.on("event", (event) => {
      if (event.event === "output") {
        const field = event.stream === "stderr" ? "diagnostics" : "output";
        run[field] = bounded(run[field], event.text);
      }
      if (event.event === "diagnostic")
        run.diagnostics = bounded(run.diagnostics, event.message + "\n");
      if (event.event === "state") {
        run.state = event.state;
        run.line = event.line;
        run.column = event.column;
        if (event.state === "paused" && selectedRun === run.id)
          showPausedPosition(run).catch((e) => log.appendLine(e.message));
        else sendExecutionPosition();
        if (event.state === "paused" && run.selectedObject)
          run.worker.send("inspect", { handle: run.selectedObject });
      }
      if (event.event === "snapshot" && event.sequence >= run.sequence) {
        run.sequence = event.sequence;
        run.snapshot = event.snapshot;
        run.processMetrics = event.process;
        run.line = event.line;
        run.column = event.column;
        if (event.heapPage)
          run.heapPage = { ...event.heapPage, objects: event.snapshot.objects };
      }
      if (
        event.event === "heapPage" &&
        event.snapshotSequence === run.sequence &&
        event.snapshotSequence >= (run.heapPage?.snapshotSequence || 0)
      )
        run.heapPage = { ...event, objects: run.snapshot?.objects || [] };
      if (event.event === "inspection") {
        run.inspections ??= {};
        run.inspections[event.handle] = event;
        if (!run.selectedObject || run.selectedObject === event.handle)
          run.inspection = event;
      }
      if (event.event === "memory") {
        run.memory.push(event.text);
        if (run.memory.length > 5000) {
          run.memory.splice(0, run.memory.length - 4999);
          run.memory[0] = "[… предыдущие события усечены …]";
        }
      }
      if (event.event === "completed") {
        run.exitCode = event.exitCode;
        run.forced = event.forced;
        run.incomplete = event.incomplete;
        run.finished = Date.now();
        run.state = event.forced
          ? "принудительно остановлен"
          : event.exitCode === 0
            ? "завершён"
            : event.exitCode === 130
              ? "остановлен"
              : "ошибка";
        sendExecutionPosition();
      }
      decorateExecution();
      if (
        event.event === "snapshot" &&
        selectedRun === run.id &&
        followsExecution(run)
      ) {
        // Navigation is asynchronous; coalesce frequent snapshots to the newest
        // position rather than repeatedly cancelling document opens.
        if (!run.navigating) {
          run.navigating = true;
          showPausedPosition(run)
            .catch((e) => log.appendLine(e.message))
            .finally(() => {
              run.navigating = false;
            });
        }
        sendExecutionPosition();
      }
      refreshMonitor();
    });
    run.worker.on("exit", () =>
      fs
        .rm(run.directory, { recursive: true, force: true })
        .catch((e) => log.appendLine(e.message)),
    );
    await run.worker.start();
  } catch (error) {
    run.state = run.stopping ? "остановлен" : "ошибка сборки";
    run.exitCode = run.stopping ? 130 : 1;
    run.finished = Date.now();
    run.diagnostics = bounded(run.diagnostics, error.message + "\n");
    if (run.directory)
      await fs
        .rm(run.directory, { recursive: true, force: true })
        .catch(() => {});
    refreshMonitor();
  }
}
async function activate(ctx) {
  context = ctx;
  log = vscode.window.createOutputChannel("Plankalkül");
  ctx.subscriptions.push(log, highlight, execution);
  ctx.subscriptions.push(
    vscode.commands.registerCommand(HOVER_COMMAND, (id, target) =>
      hoverNavigation
        .navigate(id, target)
        .catch((e) => log.appendLine(e.message)),
    ),
  );
  if (!vscode.workspace.isTrusted) return;
  sessionDirectory = await prepareSession(ctx.globalStorageUri.fsPath);
  ctx.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      "plankalkul.monitorView",
      { resolveWebviewView: resolveMonitor },
      { webviewOptions: { retainContextWhenHidden: true } },
    ),
  );
  const provider = {
    provideTextDocumentContent: async (uri) => {
      if (uri.scheme === "plankalkul-run")
        return runs.get(uri.path.split("/")[1])?.text || "";
      if (!librarySources.has(uri.toString())) await getLibrary();
      return librarySources.get(uri.toString()) || "";
    },
  };
  ctx.subscriptions.push(
    vscode.workspace.registerTextDocumentContentProvider(
      "plankalkul-run",
      provider,
    ),
    vscode.workspace.registerTextDocumentContentProvider(
      "plankalkul-library",
      provider,
    ),
  );
  for (const [name, fn] of Object.entries({
    help: openHelp,
    notation: openNotation,
    library: openLibrary,
    run: prepareLaunch,
    monitor: openMonitor,
    restart: startClient,
    settings: () =>
      vscode.commands.executeCommand(
        "workbench.action.openSettings",
        "@ext:plankalkulsharp.plankalkulsharp",
      ),
  }))
    ctx.subscriptions.push(
      vscode.commands.registerCommand("plankalkul." + name, () =>
        Promise.resolve(fn()).catch((e) =>
          vscode.window.showErrorMessage("Plankalkül: " + e.message),
        ),
      ),
    );
  ctx.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (
        editor?.document.languageId === "plankalkul" &&
        ["file", "untitled", "plankalkul-run"].includes(
          editor.document.uri.scheme,
        )
      ) {
        activeDocument = editor.document;
        scheduleNotation();
      }
    }),
  );
  ctx.subscriptions.push(
    vscode.workspace.onDidChangeTextDocument((e) => {
      const run = runs.get(selectedRun);
      if (
        run &&
        e.document.uri.scheme === "file" &&
        e.document.uri.fsPath === run.path
      ) {
        run.sourceDocument = e.document;
        decorateExecution();
        sendExecutionPosition();
        if (followsExecution(run))
          showPausedPosition(run).catch((error) =>
            log.appendLine(error.message),
          );
      }
      if (activeDocument?.uri.toString() === e.document.uri.toString())
        scheduleNotation();
    }),
  );
  ctx.subscriptions.push(
    vscode.window.onDidChangeTextEditorSelection((e) => {
      if (
        notation &&
        activeDocument?.uri.toString() === e.textEditor.document.uri.toString()
      )
        notation.webview.postMessage({
          kind: "selection",
          line: e.selections[0].active.line + 1,
        });
    }),
  );
  await startClient();
}
async function deactivate() {
  clearTimeout(notationTimer);
  clearTimeout(libraryTimer);
  clearTimeout(renderTimer);
  cancellation?.cancel();
  for (const run of runs.values()) stopRun(run);
  await Promise.all([client?.stop(), new Promise((r) => setTimeout(r, 2100))]);
  for (const run of runs.values())
    if (!run.finished) killTree(run.worker?.child);
}
module.exports = { activate, deactivate };
