"use strict";
const fs = require("node:fs/promises"),
  path = require("node:path"),
  { randomUUID } = require("node:crypto");
async function prepareSession(root) {
  await fs.mkdir(root, { recursive: true });
  root = path.resolve(root);
  for (const name of await fs.readdir(root)) {
    if (!/^session-[0-9a-f-]{36}$/.test(name)) continue;
    const directory = path.resolve(root, name);
    if (
      path.dirname(directory) !== root ||
      (await fs.lstat(directory)).isSymbolicLink()
    )
      continue;
    try {
      const owner = JSON.parse(
        await fs.readFile(path.join(directory, "owner.json"), "utf8"),
      );
      if (
        owner.application !== "plankalkul-vscode" ||
        !Number.isInteger(owner.pid) ||
        owner.pid <= 0
      )
        continue;
      try {
        process.kill(owner.pid, 0);
      } catch (error) {
        if (error.code === "ESRCH")
          await fs.rm(directory, { recursive: true, force: true });
      }
    } catch {} // Unknown directories never belong to this cleanup routine.
  }
  const directory = path.join(root, "session-" + randomUUID());
  await fs.mkdir(directory);
  await fs.writeFile(
    path.join(directory, "owner.json"),
    JSON.stringify({ application: "plankalkul-vscode", pid: process.pid }),
  );
  return directory;
}
module.exports = { prepareSession };
