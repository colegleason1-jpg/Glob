const root = process.argv[2] ?? "corpus/supply-chain-resilience-engine";
const proc = Bun.spawn(["bun", "run", "src/mcp.ts"], {
  stdin: "pipe",
  stdout: "pipe",
  stderr: "pipe",
});
const writer = proc.stdin as { write: (value: string) => void };
const reader = proc.stdout.getReader();
const decoder = new TextDecoder();
let buffered = "";

async function readMessage(): Promise<any> {
  while (!buffered.includes("\n")) {
    const { value, done } = await reader.read();
    if (done) throw new Error("server closed before responding");
    buffered += decoder.decode(value, { stream: true });
  }
  const end = buffered.indexOf("\n");
  const line = buffered.slice(0, end);
  buffered = buffered.slice(end + 1);
  return JSON.parse(line);
}

function send(id: number, method: string, params?: unknown): void {
  writer.write(`${JSON.stringify({ jsonrpc: "2.0", id, method, ...(params ? { params } : {}) })}\n`);
}

try {
  send(1, "initialize");
  const initialized = await readMessage();
  if (initialized.result?.serverInfo?.name !== "glob") throw new Error("initialize did not identify Glob");

  send(2, "tools/list");
  const listed = await readMessage();
  const names = listed.result?.tools?.map((tool: { name: string }) => tool.name) ?? [];
  const expected = ["glob_overview", "glob_search", "glob_find_symbol", "glob_trace"];
  if (JSON.stringify(names) !== JSON.stringify(expected)) throw new Error(`unexpected tools: ${names.join(", ")}`);

  send(3, "tools/call", { name: "glob_overview", arguments: { root } });
  const overview = await readMessage();
  const overviewText = overview.result?.content?.[0]?.text ?? "";
  if (!overviewText.includes('"pythonFiles": 80')) throw new Error(`unexpected overview: ${overviewText}`);

  send(4, "tools/call", { name: "glob_search", arguments: { root, query: "calibrate_elasticity" } });
  const search = await readMessage();
  const searchText = search.result?.content?.[0]?.text ?? "";
  if (!searchText.includes("engine/src/scrcae/calibration/elasticity.py:404")) throw new Error("search citation missing");
  if (!searchText.includes('"source": "symbol"')) throw new Error("search evidence source missing");

  send(5, "tools/call", { name: "glob_trace", arguments: { root, name: "solve" } });
  const trace = await readMessage();
  const traceText = trace.result?.content?.[0]?.text ?? "";
  if (!traceText.includes("app/engine_client.py:47")) throw new Error("trace citation missing");

  console.log(JSON.stringify({
    status: "pass",
    server: initialized.result.serverInfo,
    tools: names,
    overview: JSON.parse(overviewText),
    searchCitation: "engine/src/scrcae/calibration/elasticity.py:404",
    traceCitation: "app/engine_client.py:47",
  }, null, 2));
} finally {
  proc.kill();
}
