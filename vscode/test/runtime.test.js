const test = require("node:test"),
  assert = require("node:assert/strict");
const {
  bounded,
  WorkerClient,
  parseArguments,
} = require("../src/worker-client");
function waitEvent(client, predicate, timeout = 15000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      client.off("event", listen);
      reject(Error("event timeout"));
    }, timeout);
    function listen(e) {
      if (predicate(e)) {
        clearTimeout(timer);
        client.off("event", listen);
        resolve(e);
      }
    }
    client.on("event", listen);
  });
}
test("bounded output retains tail and marks truncation", () => {
  const text = bounded("a".repeat(1000), "конец", 100);
  assert.ok(Buffer.byteLength(text) <= 100);
  assert.ok(text.endsWith("конец"));
  assert.match(text, /усечён/);
});
test(
  "real worker supports independent runs, pause, inspection, stop and pipe loss",
  { skip: !process.env.PK_WORKER },
  async () => {
    const loop = new WorkerClient(process.env.PK_LOOP, process.env.PK_WORKER, {
      heapSize: 1048576,
      delayMs: 2,
      arguments: [],
    });
    const list = new WorkerClient(process.env.PK_LIST, process.env.PK_WORKER, {
      heapSize: 1048576,
      delayMs: 0,
      arguments: ["5", "3"],
    });
    const diagnostics = [];
    loop.on("diagnostic", (s) => diagnostics.push(s));
    list.on("diagnostic", (s) => diagnostics.push(s));
    let output = "",
      final;
    list.on("event", (e) => {
      if (e.event === "output" && e.stream === "stdout") output += e.text;
      if (e.event === "snapshot") final = e.snapshot;
    });
    try {
      const allocated = waitEvent(
        loop,
        (e) =>
          e.event === "snapshot" &&
          e.snapshot.objects.length > 0 &&
          e.line >= 5,
      );
      const finished = waitEvent(list, (e) => e.event === "completed");
      await loop.start();
      await list.start();
      await allocated;
      const paused = waitEvent(
        loop,
        (e) => e.event === "state" && e.state === "paused",
      );
      loop.send("pause");
      await paused;
      const inspected = waitEvent(loop, (e) => e.event === "inspection");
      loop.send("inspect", { handle: "1" });
      const fields = (await inspected).fields;
      assert.ok(fields.some((f) => f.value === "7"));
      const bytes = waitEvent(loop, (e) => e.event === "heapPage");
      loop.send("inspectHeap", { offset: 0 });
      assert.equal((await bytes).bytes[0], 7);
      assert.equal((await finished).exitCode, 0);
      assert.equal(output.trim(), "2");
      assert.equal(final.objects.length, 0);
      const resumed = waitEvent(
        loop,
        (e) => e.event === "state" && e.state === "running",
      );
      loop.send("resume");
      await resumed;
      const pausedAgain = waitEvent(
        loop,
        (e) => e.event === "state" && e.state === "paused",
      );
      loop.send("pause");
      await pausedAgain;
      const stopped = waitEvent(loop, (e) => e.event === "completed");
      loop.stop();
      assert.equal((await stopped).exitCode, 130);
      assert.deepEqual(diagnostics, []);
    } finally {
      loop.stop();
      list.stop();
    }
    const lost = new WorkerClient(process.env.PK_LOOP, process.env.PK_WORKER, {
      heapSize: 1048576,
      delayMs: 1000,
      arguments: [],
    });
    const running = waitEvent(
      lost,
      (e) => e.event === "state" && e.state === "running",
    );
    await lost.start();
    await running;
    const exit = new Promise((resolve) => lost.once("exit", resolve));
    lost.socket.destroy();
    await exit;
    assert.ok([1, 130].includes(lost.child.exitCode)); // Broken output pipe may be reported as transport error.
  },
);

test("structured Int64 arguments retain their exact spelling", () => {
  assert.deepEqual(parseArguments("[9223372036854775807, [1, 2], [7,9]]"), [
    "9223372036854775807",
    "[1, 2]",
    "[7,9]",
  ]);
});

test(
  "start paused and step advances exactly one checkpoint",
  { skip: !process.env.PK_WORKER },
  async () => {
    const client = new WorkerClient(
      process.env.PK_LOOP,
      process.env.PK_WORKER,
      { heapSize: 1048576, delayMs: 0, startPaused: true, arguments: [] },
    );
    let snapshots = [];
    client.on("event", (e) => {
      if (e.event === "snapshot" && e.exact) snapshots.push(e);
    });
    try {
      const first = waitEvent(client, (e) => e.event === "snapshot" && e.exact);
      await client.start();
      assert.equal((await first).snapshot.objects.length, 0);
      // The function entry itself is a checkpoint, followed by the allocation.
      for (let i = 0; i < 2; i++) {
        const next = waitEvent(
          client,
          (e) => e.event === "snapshot" && e.exact,
        );
        client.send("step");
        await next;
      }
      assert.equal(snapshots.at(-1).snapshot.objects.length, 1);
      const count = snapshots.length;
      await new Promise((resolve) => setTimeout(resolve, 100));
      assert.equal(snapshots.length, count);
      const inspection = waitEvent(client, (e) => e.event === "inspection");
      client.send("inspect", { handle: "1" });
      assert.ok((await inspection).fields.some((f) => f.value === "0"));
      const next = waitEvent(client, (e) => e.event === "snapshot" && e.exact);
      client.send("step");
      await next;
      const changed = waitEvent(client, (e) => e.event === "inspection");
      client.send("inspect", { handle: "1" });
      assert.ok((await changed).fields.some((f) => f.value === "7"));
      const stopped = waitEvent(client, (e) => e.event === "completed");
      client.stop();
      assert.equal((await stopped).exitCode, 130);
    } finally {
      client.stop();
    }
  },
);

test(
  "one and thousand-node lists finish without live objects",
  { skip: !process.env.PK_WORKER },
  async () => {
    for (const [count, value, expected] of [
      [1, 1, "0"],
      [1000, 500, "499"],
    ]) {
      const client = new WorkerClient(
        process.env.PK_LIST,
        process.env.PK_WORKER,
        {
          heapSize: 1048576,
          delayMs: 0,
          arguments: [String(count), String(value)],
        },
      );
      let output = "",
        snapshot;
      client.on("event", (e) => {
        if (e.event === "output" && e.stream === "stdout") output += e.text;
        if (e.event === "snapshot") snapshot = e.snapshot;
      });
      const finished = waitEvent(client, (e) => e.event === "completed");
      await client.start();
      assert.equal((await finished).exitCode, 0);
      assert.equal(output.trim(), expected);
      assert.equal(snapshot.objects.length, 0);
    }
  },
);
