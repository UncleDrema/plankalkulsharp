"use strict";
const vscode = acquireVsCodeApi(),
  app = document.getElementById("app"),
  view = document.body.dataset.view;
const send = (command, data = {}) => vscode.postMessage({ command, ...data });
const el = (tag, text, cls) => {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = text;
  if (cls) n.className = cls;
  return n;
};
const button = (label, fn) => {
  const b = el("button", label);
  b.type = "button";
  b.onclick = fn;
  return b;
};
let projection,
  run,
  runList = [],
  tab = "output",
  chosenPlan,
  plans = [],
  selectedRun;
let executionPosition;
function highlightExecution() {
  const p = executionPosition;
  const formulas = [...app.querySelectorAll(".formula")];
  formulas.forEach((n) => {
    n.classList.remove("executing");
    n.removeAttribute("aria-current");
  });
  if (
    !p?.line ||
    p.uri !== projection?.uri ||
    p.version !== projection?.documentVersion
  )
    return;
  // Select the most specific statement, not every enclosing loop/procedure.
  const candidates = formulas.filter(
    (n) =>
      Number(n.dataset.line) <= p.line &&
      Number(n.dataset.endLine) >= p.line &&
      n.dataset.kind !== "Interface",
  );
  candidates.sort((a, b) => {
    const exact = (n) =>
      Number(n.dataset.line) === p.line &&
      Number(n.dataset.column) === p.column;
    return (
      Number(exact(b)) - Number(exact(a)) ||
      Number(a.dataset.endLine) -
        Number(a.dataset.line) -
        (Number(b.dataset.endLine) - Number(b.dataset.line)) ||
      Number(b.dataset.depth) - Number(a.dataset.depth)
    );
  });
  const selected = candidates[0];
  if (selected) {
    selected.classList.add("executing");
    selected.setAttribute("aria-current", "step");
    selected.scrollIntoView?.({ block: "nearest" });
  }
}
const heapDrafts = new Map();
function mathText(text) {
  // The conditional arrow has a centred dot below the shaft. Combining marks
  // depend on font fallback, so draw this historical sign as one scalable unit.
  if (text === "→\u0323") {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 30 24");
    svg.setAttribute("class", "conditional-arrow");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Условное выполнение");
    const path = document.createElementNS(svg.namespaceURI, "path");
    path.setAttribute("d", "M2 10H27 M21 5L27 10L21 15");
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "currentColor");
    path.setAttribute("stroke-width", "1.4");
    const dot = document.createElementNS(svg.namespaceURI, "circle");
    dot.setAttribute("cx", "15");
    dot.setAttribute("cy", "18");
    dot.setAttribute("r", "1.5");
    dot.setAttribute("fill", "currentColor");
    svg.append(path, dot);
    return svg;
  }
  const node = el("span", undefined, "math-text");
  const powers = "⁰¹²³⁴⁵⁶⁷⁸⁹";
  for (const part of text.split(/([⁰¹²³⁴⁵⁶⁷⁸⁹]+)/)) {
    if (part && powers.includes(part[0]))
      node.append(el("sup", [...part].map((c) => powers.indexOf(c)).join("")));
    else node.append(document.createTextNode(part));
  }
  return node;
}
function table(cells) {
  const t = el("table");
  for (const [key, label] of [
    ["text", ""],
    ["index", "V"],
    ["component", "K"],
    ["structure", "S"],
  ]) {
    if (
      key !== "text" &&
      !cells.some(
        (c) => c[key] || (key === "component" && c.component_cells?.length),
      )
    )
      continue;
    const tr = el("tr");
    tr.append(el("th", label));
    for (const c of cells) {
      const td = el("td", undefined, c.extension ? "extension" : "");
      if (key === "component" && c.component_cells?.length)
        td.append(table(c.component_cells));
      else td.append(mathText(c[key] || ""));
      td.dataset.row = key;
      if (c.hint) td.title = c.hint;
      tr.append(td);
    }
    t.append(tr);
  }
  return t;
}
function notation(data) {
  projection = data;
  app.replaceChildren(
    el("h1", "Нотация Plankalkül"),
    el(
      "p",
      "V — номер · K — компонент · S — структура. Наведите на формулу для подсветки исходника; нажмите, чтобы выбрать участок.",
      "status",
    ),
  );
  const rows = el("section");
  for (const row of data.rows) {
    if (["EndBlock", "EndProgram"].includes(row.kind)) continue;
    const b = button("", () =>
      send("source", {
        uri: data.uri,
        version: data.documentVersion,
        range: row,
        pin: true,
      }),
    );
    b.className = "formula depth" + Math.min(row.depth, 5);
    b.dataset.line = row.line;
    b.dataset.endLine = row.endLine || row.line;
    b.dataset.column = row.column || 0;
    b.dataset.kind = row.kind;
    b.dataset.depth = row.depth;
    if (row.caption) b.append(el("div", row.caption, "caption"));
    b.append(table(row.cells));
    b.onmouseenter = () =>
      send("source", {
        uri: data.uri,
        version: data.documentVersion,
        range: row,
      });
    b.onmouseleave = () => send("clear");
    b.onfocus = b.onmouseenter;
    b.onblur = b.onmouseleave;
    rows.append(b);
  }
  app.append(rows);
  highlightExecution();
}
function library(data, specializations = [], sourceLabel = "") {
  plans = data;
  app.replaceChildren(
    el("h1", "Стандартные планы"),
    el("p", sourceLabel, "status"),
  );
  const search = el("input");
  search.placeholder = "Найти план";
  search.setAttribute("aria-label", "Поиск плана");
  app.append(search);
  const layout = el("div", undefined, "layout"),
    nav = el("nav", undefined, "plans"),
    detail = el("section");
  layout.append(nav, detail);
  app.append(layout);
  function select(p) {
    chosenPlan = p.name;
    detail.replaceChildren(
      el("h2", p.name),
      el("p", p.description || ""),
      el("pre", p.example || ""),
      el("p", "Параметры типов: " + p.types.join(", "), "status"),
      button("Открыть шаблон .pk", () => send("openPlan", { name: p.name })),
      el("pre", p.source),
    );
    const bound = specializations.filter((s) => s.name === p.name);
    if (bound.length) {
      const selectBox = el("select");
      selectBox.setAttribute("aria-label", "Подстановка типов");
      for (const [i, s] of bound.entries()) {
        const o = el("option", JSON.stringify(s.bindings));
        o.value = i;
        selectBox.append(o);
      }
      const formulas = el("section");
      function render() {
        formulas.replaceChildren();
        for (const row of bound[Number(selectBox.value)].rows) {
          if (row.kind === "EndBlock") continue;
          const f = el("div", undefined, "formula");
          f.append(table(row.cells));
          formulas.append(f);
        }
      }
      selectBox.onchange = render;
      detail.append(
        el("h2", "Подстановки текущей программы"),
        selectBox,
        formulas,
      );
      render();
    }
  }
  function filter() {
    nav.replaceChildren();
    const matches = plans.filter((p) =>
      (p.name + " " + (p.description || ""))
        .toLowerCase()
        .includes(search.value.toLowerCase()),
    );
    for (const p of matches) nav.append(button(p.name, () => select(p)));
    if (matches.length)
      select(matches.find((p) => p.name === chosenPlan) || matches[0]);
    else detail.replaceChildren(el("p", "Планы не найдены."));
  }
  search.oninput = filter;
  filter();
}
let controls,
  content,
  status,
  runSelect,
  delay,
  launchForm,
  launchFile,
  launchError,
  launchButton,
  launchConfig;
const launchFields = {},
  launchDrafts = new Map();
function setupLaunchForm() {
  launchFile = el("p", "Выберите .pk командой запуска в редакторе.", "status");
  launchForm = el("form", undefined, "toolbar launch-form");
  for (const [key, title, type] of [
    ["argumentsText", "Аргументы (JSON)", "text"],
    ["heapSize", "Куча, байт", "number"],
    ["delay", "Задержка нового запуска, мс", "number"],
    ["startPaused", "Пошагово", "checkbox"],
  ]) {
    const label = el("label", title),
      input = el("input");
    input.type = type;
    input.name = key;
    if (key === "argumentsText") input.placeholder = "[5,3] или [[1,2,3]]";
    if (key === "heapSize") {
      input.min = 8;
      input.max = 2147483640;
      input.step = 8;
    }
    if (key === "delay") {
      input.min = 0;
      input.max = 1000;
      input.step = 1;
    }
    if (type !== "checkbox") input.required = true;
    label.append(input);
    launchForm.append(label);
    launchFields[key] = input;
    input.oninput = () => {
      if (launchConfig) launchDrafts.set(launchConfig.path, launchValues());
      launchError.textContent = "";
    };
  }
  launchButton = button("Запустить", () => {});
  launchButton.type = "submit";
  launchButton.disabled = true;
  launchError = el("p", "", "error");
  launchError.setAttribute("role", "alert");
  launchForm.append(launchButton);
  launchForm.onsubmit = (e) => {
    e.preventDefault();
    if (!launchConfig || launchButton.disabled) return;
    const options = launchValues();
    try {
      if (!Array.isArray(JSON.parse(options.argumentsText)))
        throw Error("Нужен JSON-массив аргументов");
      if (
        !Number.isInteger(options.heapSize) ||
        options.heapSize <= 0 ||
        options.heapSize % 8 ||
        options.heapSize > 2147483640
      )
        throw Error(
          "Куча: положительное целое, кратное 8, не больше 2147483640",
        );
      if (
        !Number.isInteger(options.delay) ||
        options.delay < 0 ||
        options.delay > 1000
      )
        throw Error("Задержка: целое число от 0 до 1000 мс");
      launchButton.disabled = true;
      launchError.textContent = "";
      send("launch", { key: launchConfig.key, options });
    } catch (error) {
      launchError.textContent = error.message;
    }
  };
  app.append(launchFile, launchForm, launchError);
}
function launchValues() {
  return {
    argumentsText: launchFields.argumentsText.value,
    heapSize: Number(launchFields.heapSize.value),
    delay: Number(launchFields.delay.value),
    startPaused: launchFields.startPaused.checked,
  };
}
function updateLaunch(config) {
  if (!config || launchConfig?.key === config.key) return;
  launchConfig = config;
  const values = launchDrafts.get(config.path) || config;
  for (const [key, input] of Object.entries(launchFields)) {
    if (input.type === "checkbox") input.checked = values[key];
    else input.value = values[key];
  }
  launchFile.textContent =
    "Исходный файл: " +
    config.path +
    " · новый запуск использует текущий текст редактора";
  launchButton.disabled = false;
  launchError.textContent = "";
}
function setupMonitor() {
  app.replaceChildren(el("h1", "Машина Plankalkül"));
  setupLaunchForm();
  controls = el("div", undefined, "toolbar");
  runSelect = el("select");
  runSelect.setAttribute("aria-label", "Запуск");
  runSelect.onchange = () => send("selectRun", { id: runSelect.value });
  controls.append(runSelect);
  for (const [label, command] of [
    ["Пауза", "pause"],
    ["Продолжить", "resume"],
    ["Шаг", "step"],
    ["Остановить", "stop"],
    ["Исходник запуска", "snapshot"],
  ]) {
    const b = button(label, () => send(command, { id: run?.id }));
    b.dataset.command = command;
    controls.append(b);
  }
  delay = el("input");
  delay.type = "number";
  delay.min = 0;
  delay.max = 1000;
  delay.onchange = () =>
    send("delay", { id: run?.id, value: Number(delay.value) });
  const label = el("label", "Задержка текущего исполнения, мс");
  label.append(delay);
  controls.append(label);
  controls.append(button("Настройки запуска", () => send("settings")));
  app.append(controls);
  status = el("p", "", "status");
  app.append(status);
  const tabs = el("div", undefined, "toolbar tabs");
  for (const [key, label] of [
    ["output", "Вывод"],
    ["diagnostics", "Диагностика"],
    ["memory", "Память"],
    ["events", "События"],
    ["hex", "Куча · hex"],
  ]) {
    const b = button(label, () => {
      tab = key;
      renderRun();
    });
    b.dataset.tab = key;
    tabs.append(b);
  }
  app.append(tabs);
  content = el("section");
  app.append(content);
}
function listTable(headers, rows) {
  const t = el("table", undefined, "table"),
    head = el("tr");
  for (const h of headers) head.append(el("th", h));
  t.append(head);
  for (const row of rows) {
    const tr = el("tr");
    for (const cell of row) {
      const td = el("td");
      td.append(
        cell instanceof Node
          ? cell
          : document.createTextNode(String(cell ?? "")),
      );
      tr.append(td);
    }
    t.append(tr);
  }
  const wrap = el("div", undefined, "scroll");
  wrap.append(t);
  return wrap;
}
function inspect(handle) {
  send("inspect", { id: run.id, handle });
}
function stateLabel(state) {
  return (
    { running: "выполняется", paused: "пауза", waiting: "ожидание" }[state] ||
    state
  );
}
function renderRun() {
  if (!content) setupMonitor();
  for (const b of app.querySelectorAll("[data-tab]"))
    b.classList.toggle("active", b.dataset.tab === tab);
  if (!run) {
    for (const b of controls.querySelectorAll("[data-command]"))
      b.disabled = true;
    content.replaceChildren(
      el(
        "p",
        "Откройте .pk и выполните команду «Plankalkül: Запустить программу». Каждый запуск получает свой снимок исходника и свою кучу.",
        "empty",
      ),
    );
    return;
  }
  status.textContent =
    `${run.name} · ${stateLabel(run.state)} · ${(((run.finished || Date.now()) - run.started) / 1000) | 0} с · ${run.state === "running" ? "последняя позиция: строка" : "строка"} ${run.line || "—"} · код ${run.exitCode ?? "—"}` +
    (run.incomplete ? " · последний снимок неполный" : "");
  if (document.activeElement !== delay) delay.value = run.delay;
  delay.disabled = !!run.finished;
  for (const b of controls.querySelectorAll("[data-command]")) {
    const c = b.dataset.command;
    b.disabled =
      c === "pause"
        ? run.state !== "running"
        : c === "resume" || c === "step"
          ? run.state !== "paused"
          : c === "stop"
            ? !!run.finished
            : false;
  }
  const heapFocused = document.activeElement?.dataset.heapOffset === "true";
  const scrolls = [...content.querySelectorAll(".scroll,pre")].map((n) => [
    n.scrollTop,
    n.scrollLeft,
  ]);
  content.replaceChildren();
  if (tab === "output" || tab === "diagnostics" || tab === "events") {
    content.append(
      el(
        "pre",
        tab === "events"
          ? run.memory.join("\n")
          : run[tab] || "Пока нет вывода.",
      ),
    );
  }
  if (tab === "diagnostics")
    for (const d of run.buildDiagnostics || [])
      if (Number.isInteger(d.line) && d.line > 0)
        content.append(
          button(`Строка ${d.line}: ${d.message}`, () =>
            send("location", { id: run.id, line: d.line, column: d.column }),
          ),
        );
  if (tab === "memory") {
    if (run.process)
      content.append(
        el(
          "p",
          `Процесс Worker: ${run.process.workingSetBytes} Б · CPU ${Math.round(run.process.cpuMilliseconds)} мс`,
          "status",
        ),
      );
    const s = run.stats;
    if (!s) {
      content.append(
        el("p", "Снимок памяти появится после начала выполнения."),
      );
      return;
    }
    const stat = s.stats;
    content.append(
      el(
        "div",
        `Выделений: ${stat.allocations} · освобождений: ${stat.frees}\nЗанято: ${stat.usedBytes} Б · свободно: ${stat.freeBytes} Б · пик: ${stat.peakUsedBytes} Б\nКрупнейший свободный блок: ${stat.largestFreeBlock} Б · объектов: ${s.objects.length}\nСнимок №${run.sequence}. Собственная куча не является общим лимитом памяти процесса.`,
        "stats",
      ),
    );
    const map = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    map.setAttribute("class", "map");
    map.setAttribute("viewBox", "0 0 1000 32");
    for (const b of s.blocks) {
      const rect = document.createElementNS(map.namespaceURI, "rect");
      rect.setAttribute("x", String((1000 * b.offset) / run.heapSize));
      rect.setAttribute("width", String((1000 * b.size) / run.heapSize));
      rect.setAttribute("height", "32");
      rect.setAttribute("class", b.free ? "free" : "used");
      const title = document.createElementNS(map.namespaceURI, "title");
      title.textContent = `${b.offset}: ${b.size} Б · ${b.free ? "свободно" : "занято"}`;
      rect.append(title);
      rect.onclick = () => {
        tab = "hex";
        send("heap", { id: run.id, offset: b.offset });
        renderRun();
      };
      map.append(rect);
    }
    content.append(map);
    content.append(
      el("h2", "Объекты"),
      listTable(
        ["Ссылка", "Тип", "Смещение", "Размер", "Создан"],
        s.objects.map((o) => [
          button("#" + o.handle, () => inspect(o.handle)),
          o.typeName,
          o.offset,
          o.size,
          o.location,
        ]),
      ),
    );
    content.append(el("h2", "Поля объекта"));
    if (run.inspection) {
      const i = run.inspection;
      content.append(
        el(
          "p",
          `Объект #${i.handle} · снимок №${i.snapshotSequence}${i.snapshotSequence < run.sequence ? " · сохранённые данные" : ""}`,
          "status",
        ),
        listTable(
          ["Поле", "Тип", "Значение"],
          i.fields.map((f) => [
            f.path,
            f.kind,
            f.targetHandle && f.targetHandle !== "0"
              ? button(f.value, () => inspect(f.targetHandle))
              : f.value,
          ]),
        ),
      );
    } else
      content.append(
        el(
          "p",
          "Выберите объект на паузе. После завершения доступны только уже прочитанные поля.",
          "status",
        ),
      );
  }
  if (tab === "hex") {
    const page = run.heapPage;
    const nav = el("div", undefined, "toolbar");
    const offset = el("input");
    offset.setAttribute("aria-label", "Смещение в байтах");
    offset.type = "number";
    offset.min = 0;
    offset.dataset.heapOffset = "true";
    offset.value = heapDrafts.get(run.id) ?? page?.offset ?? 0;
    offset.oninput = () => heapDrafts.set(run.id, offset.value);
    nav.append(
      button("Назад", () =>
        send("heap", {
          id: run.id,
          offset: Math.max(0, (page?.offset || 0) - 256),
        }),
      ),
      offset,
      button("Перейти", () =>
        send("heap", { id: run.id, offset: Number(offset.value) }),
      ),
      button("Вперёд", () =>
        send("heap", { id: run.id, offset: (page?.offset || 0) + 256 }),
      ),
    );
    if (run.finished) for (const c of nav.children) c.disabled = true;
    content.append(nav);
    if (!page) {
      content.append(
        el("p", "Дамп обновляется на паузе или при ненулевой задержке."),
      );
      if (heapFocused) content.querySelector("[data-heap-offset]")?.focus();
      return;
    }
    content.append(
      el(
        "p",
        `Снимок №${page.snapshotSequence}${page.snapshotSequence < run.sequence ? " · сохранённые данные" : ""}. «--» — свободная память.`,
        "status",
      ),
    );
    const t = el("table", undefined, "hex");
    for (let i = 0; i < page.bytes.length; i += 16) {
      const row = el("tr");
      row.append(el("th", (page.offset + i).toString(16).padStart(8, "0")));
      for (let j = i; j < Math.min(i + 16, page.bytes.length); j++) {
        const address = page.offset + j,
          owner = page.objects?.find(
            (o) => address >= o.offset && address < o.offset + o.size,
          ),
          value = page.bytes[j];
        const cell = el(
          "td",
          value === null
            ? "--"
            : value.toString(16).padStart(2, "0").toUpperCase(),
        );
        if (owner) {
          cell.className =
            owner.handle === run.selectedObject
              ? "chosen"
              : "owner" + Number(BigInt(owner.handle) % 5n);
          cell.title = `#${owner.handle} ${owner.typeName}`;
        }
        row.append(cell);
      }
      t.append(row);
    }
    const wrap = el("div", undefined, "scroll");
    wrap.append(t);
    content.append(wrap);
    content.append(
      listTable(
        ["Объект", "Тип", "Смещение"],
        (page.objects || [])
          .filter(
            (o) =>
              o.offset < page.offset + page.bytes.length &&
              o.offset + o.size > page.offset,
          )
          .map((o) => [
            button("#" + o.handle, () => inspect(o.handle)),
            o.typeName,
            o.offset,
          ]),
      ),
    );
  }
  [...content.querySelectorAll(".scroll,pre")].forEach((n, i) => {
    if (scrolls[i]) {
      n.scrollTop = scrolls[i][0];
      n.scrollLeft = scrolls[i][1];
    }
  });
  if (heapFocused) content.querySelector("[data-heap-offset]")?.focus();
}
window.addEventListener("message", ({ data: m }) => {
  if (m.kind === "launchError" || m.kind === "launchReady") {
    if (launchButton) launchButton.disabled = !launchConfig;
    if (launchError)
      launchError.textContent = m.kind === "launchError" ? m.text : "";
  }
  if (m.kind === "execution") {
    executionPosition = m;
    highlightExecution();
  }
  if (m.kind === "loading") {
    app.querySelectorAll(".formula").forEach((n) => n.classList.add("stale"));
    let p = app.querySelector(".loading");
    if (!p) {
      p = el("p", "", "loading status");
      app.prepend(p);
    }
    p.textContent = m.text;
  }
  if (m.kind === "error") {
    app.replaceChildren(el("p", m.text, "error"));
    projection = undefined;
  }
  if (m.kind === "notation") notation(m);
  if (m.kind === "selection")
    for (const n of app.querySelectorAll(".formula"))
      n.classList.toggle(
        "selected",
        Number(n.dataset.line) <= m.line && Number(n.dataset.endLine) >= m.line,
      );
  if (m.kind === "library") library(m.plans, m.specializations, m.sourceLabel);
  if (m.kind === "help") help(m.topics);
  if (m.kind === "monitor") {
    if (!content) setupMonitor();
    updateLaunch(m.launch);
    run = m.run;
    const key = JSON.stringify(m.runs);
    if (key !== JSON.stringify(runList)) {
      runList = m.runs;
      runSelect.replaceChildren(
        ...m.runs.map((r) => {
          const o = el("option", r.name + " · " + stateLabel(r.state));
          o.value = r.id;
          return o;
        }),
      );
    }
    runSelect.value = m.selected || "";
    renderRun();
  }
});
if (view === "monitor") setupMonitor();
else app.append(el("p", "Загрузка…", "status"));
send("ready");

function help(topics) {
  app.replaceChildren(el("h1", "Справка по языку"));
  const input = el("input");
  input.placeholder = "Найти конструкцию";
  input.setAttribute("aria-label", "Поиск по справке");
  app.append(input);
  const layout = el("div", undefined, "layout"),
    nav = el("nav", undefined, "plans"),
    detail = el("section");
  layout.append(nav, detail);
  app.append(layout);
  function select(t) {
    detail.replaceChildren(el("h2", t.title));
    for (const p of t.paragraphs)
      detail.append(el(p.code ? "pre" : "p", p.text));
  }
  function filter() {
    nav.replaceChildren();
    const found = topics.filter((t) =>
      (t.title + " " + t.paragraphs.map((p) => p.text).join(" "))
        .toLowerCase()
        .includes(input.value.toLowerCase()),
    );
    for (const t of found) nav.append(button(t.title, () => select(t)));
    if (found.length) select(found[0]);
    else detail.replaceChildren(el("p", "Ничего не найдено."));
  }
  input.oninput = filter;
  filter();
}
