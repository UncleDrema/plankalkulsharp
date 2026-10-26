"use strict";
const { spawn } = require("node:child_process");
const net = require("node:net");
const { randomUUID } = require("node:crypto");
const { EventEmitter } = require("node:events");

function killTree(child) {
  if (!child || child.exitCode !== null) return;
  if (process.platform === "win32")
    spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"], {
      windowsHide: true,
      stdio: "ignore",
    });
  else child.kill("SIGKILL");
}
function bounded(text, addition, limit = 1048576) {
  let result = text + addition;
  if (Buffer.byteLength(result, "utf8") > limit) {
    const marker = "[… предыдущий вывод усечён …]\n";
    let tail = Buffer.from(result, "utf8").subarray(
      -(limit - Buffer.byteLength(marker)),
    );
    while (tail.length && (tail[0] & 0xc0) === 0x80) tail = tail.subarray(1);
    result = marker + tail.toString("utf8");
  }
  return result;
}
// Validate JSON but retain each argument's spelling: JSON.parse/stringify would
// silently round an Int64 beyond JavaScript's safe integer range.
function parseArguments(text) {
  if (!Array.isArray(JSON.parse(text)))
    throw Error("Нужен JSON-массив аргументов");
  const input = text.trim().slice(1, -1);
  if (!input.trim()) return [];
  const values = [];
  let start = 0,
    depth = 0,
    string = false,
    escape = false;
  for (let i = 0; i < input.length; i++) {
    const c = input[i];
    if (string) {
      if (escape) escape = false;
      else if (c === "\\") escape = true;
      else if (c === '"') string = false;
      continue;
    }
    if (c === '"') string = true;
    else if (c === "[" || c === "{") depth++;
    else if (c === "]" || c === "}") depth--;
    else if (c === "," && depth === 0) {
      values.push(input.slice(start, i).trim());
      start = i + 1;
    }
  }
  values.push(input.slice(start).trim());
  return values;
}
// Transport has no dependency on VS Code: the same controller is tested headlessly.
class WorkerClient extends EventEmitter {
  constructor(module, worker, settings) {
    super();
    this.module = module;
    this.worker = worker;
    this.settings = settings;
    this.done = false;
  }
  async start() {
    const name = "plankalkul-vscode-" + randomUUID();
    const address =
      process.platform === "win32" ? "\\\\.\\pipe\\" + name : "/tmp/" + name;
    this.server = net.createServer((socket) => {
      if (this.socket) {
        socket.destroy();
        return;
      }
      this.socket = socket;
      clearTimeout(this.connectTimer);
      this.server.close();
      socket.setEncoding("utf8");
      let pending = "";
      socket.on("error", (error) => this.emit("diagnostic", error.message));
      socket.on("data", (data) => {
        pending += data;
        if (pending.length > 16 * 1024 * 1024) {
          this.emit("diagnostic", "Слишком большое сообщение Worker");
          this.stop();
          return;
        }
        let end;
        while ((end = pending.indexOf("\n")) >= 0) {
          const line = pending.slice(0, end);
          pending = pending.slice(end + 1);
          try {
            const event = JSON.parse(line);
            if (event.version !== 1)
              throw Error("Несовместимый протокол Worker");
            if (event.event === "completed") {
              this.done = true;
              clearTimeout(this.stopTimer);
            }
            this.emit("event", event);
          } catch (error) {
            this.emit("diagnostic", error.message);
          }
        }
      });
      socket.on("close", () => {
        if (!this.done) this.stop();
      });
      this.send("start", this.settings);
      if (this.stopping) this.send("stop");
    });
    await new Promise((resolve, reject) => {
      this.server.once("error", reject);
      this.server.listen(address, resolve);
    });
    this.child = spawn(
      "dotnet",
      [this.worker, "--module", this.module, "--pipe", name],
      { windowsHide: true, stdio: ["ignore", "pipe", "pipe"] },
    );
    this.child.stderr.setEncoding("utf8");
    this.child.stderr.on("data", (text) => this.emit("diagnostic", text));
    this.child.stdout.resume();
    this.child.on("error", (error) => {
      this.emit("diagnostic", error.message);
      this.finish(1);
    });
    // Let the pipe deliver the final snapshot/completed frame before disposal.
    this.child.on("exit", (code) =>
      setTimeout(() => this.finish(code ?? 1), 100),
    );
    this.connectTimer = setTimeout(() => {
      this.emit("diagnostic", "Worker не подключился за 10 секунд");
      this.stop();
    }, 10000);
  }
  send(command, params = {}) {
    if (this.socket && !this.socket.destroyed)
      this.socket.write(
        JSON.stringify({ version: 1, command, ...params }) + "\n",
      );
  }
  stop() {
    if (this.done || this.stopping) return;
    this.stopping = true;
    this.send("stop");
    this.stopTimer = setTimeout(() => {
      this.forced = true;
      killTree(this.child);
    }, 2000);
  }
  finish(code) {
    if (this.finished) return;
    this.finished = true;
    clearTimeout(this.connectTimer);
    clearTimeout(this.stopTimer);
    this.socket?.destroy();
    this.server?.close();
    if (!this.done)
      this.emit("event", {
        version: 1,
        event: "completed",
        exitCode: this.stopping ? 130 : code,
        forced: !!this.forced,
        incomplete: true,
      });
    this.done = true;
    this.emit("exit", code);
  }
  dispose() {
    this.stop();
  }
}
module.exports = { WorkerClient, killTree, bounded, parseArguments };
