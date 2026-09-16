import { join } from "node:path";
import { listFiles } from "../src/walk";

const root = process.argv[2] ?? "corpus/supply-chain-resilience-engine";
const cases = [
  { name: "provenance", tool: "glob_search", args: { query: "provenance" }, expected: ["provenance"] },
  { name: "calibration", tool: "glob_search", args: { query: "calibrate_elasticity" }, expected: ["calibrate_elasticity"] },
  { name: "solve callers", tool: "glob_trace", args: { name: "solve" }, expected: ["app/engine_client.py:47", "app/adapters.py:725"] },
  { name: "capacity", tool: "glob_search", args: { query: "capacity" }, expected: ["network.py", "optimizer.py"] },
];

function startClient() {
  const proc = Bun.spawn(["bun", "run", "src/mcp.ts"], { stdin: "pipe", stdout: "pipe", stderr: "pipe" });
  const writer = proc.stdin as { write: (value: string) => void };
  const reader = proc.stdout.getReader();
  const decoder = new TextDecoder();
  let buffered = "";
  const read = async () => {
    while (!buffered.includes("\n")) {
      const { value, done } = await reader.read();
      if (done) throw new Error("MCP process ended early");
      buffered += decoder.decode(value, { stream: true });
    }
    const end = buffered.indexOf("\n");
    const line = buffered.slice(0, end);
    buffered = buffered.slice(end + 1);
    return JSON.parse(line);
  };
  let id = 0;
  const call = async (method: string, params?: unknown) => {
    const requestId = ++id;
    writer.write(`${JSON.stringify({ jsonrpc: "2.0", id: requestId, method, ...(params ? { params } : {}) })}\n`);
    return read();
  };
  return { proc, call };
}

const files = await listFiles(root);
const rows = [];
const client = startClient();
try {
  await client.call("initialize");
  for (const test of cases) {
    const terms = (test.args.query ?? test.args.name).toLowerCase().split(/\s+/);
    const baselineStart = performance.now();
    let baselineChars = 0;
    let baselineFiles = 0;
    for (const rel of files) {
      const text = await Bun.file(join(root, rel)).text();
      if (terms.every((term) => text.toLowerCase().includes(term))) {
        baselineChars += text.length;
        baselineFiles++;
      }
    }
    const baselineMs = performance.now() - baselineStart;

    const globStart = performance.now();
    const response = await client.call("tools/call", {
      name: test.tool,
      arguments: { root, ...test.args },
    });
    const globMs = performance.now() - globStart;
    const globText = response.result?.content?.[0]?.text ?? "";
    const citationsFound = test.expected.every((needle) => globText.includes(needle));
    rows.push({
      task: test.name,
      baselineFiles,
      baselineChars,
      baselineApproxTokens: Math.ceil(baselineChars / 4),
      baselineMs: Number(baselineMs.toFixed(2)),
      globChars: globText.length,
      globApproxTokens: Math.ceil(globText.length / 4),
      globMs: Number(globMs.toFixed(2)),
      retrievalReduction: `${Math.max(0, (1 - globText.length / Math.max(baselineChars, 1)) * 100).toFixed(1)}%`,
      citationsFound,
    });
  }
} finally {
  client.proc.kill();
}

console.log(JSON.stringify({
  status: rows.every((row) => row.citationsFound) ? "pass" : "citation-failure",
  type: "tool-level A/B; not model-token telemetry",
  root,
  rows,
}, null, 2));
