import { expect, test } from "bun:test";

function message(id: number, method: string, params?: unknown) {
  return `${JSON.stringify({ jsonrpc: "2.0", id, method, ...(params ? { params } : {}) })}\n`;
}

function startServer() {
  const proc = Bun.spawn(["bun", "run", "src/mcp.ts"], {
    stdin: "pipe",
    stdout: "pipe",
    stderr: "pipe",
  });
  const reader = proc.stdout.getReader();
  const decoder = new TextDecoder();
  let buffered = "";
  const readLine = async () => {
    while (!buffered.includes("\n")) {
      const { value, done } = await reader.read();
      if (done) throw new Error("MCP server closed stdout before replying");
      buffered += decoder.decode(value, { stream: true });
    }
    const newline = buffered.indexOf("\n");
    const line = buffered.slice(0, newline);
    buffered = buffered.slice(newline + 1);
    return JSON.parse(line);
  };
  return { proc, writer: proc.stdin as { write: (value: string) => void }, readLine };
}

test("MCP server supports initialize, tools/list, and tools/call", async () => {
  const { proc, writer, readLine } = startServer();
  try {
    writer.write(message(1, "initialize"));
    const initialized = await readLine();
    expect(initialized.result.serverInfo.name).toBe("glob");

    writer.write(message(2, "tools/list"));
    const listed = await readLine();
    expect(listed.result.tools.map((tool: { name: string }) => tool.name)).toEqual([
      "glob_overview",
      "glob_search",
      "glob_find_symbol",
      "glob_trace",
    ]);

    writer.write(message(3, "tools/call", { name: "glob_search", arguments: { root: "corpus/supply-chain-resilience-engine", query: "calibrate_elasticity" } }));
    const called = await readLine();
    expect(called.result.content[0].text).toContain('"citation": "engine/src/scrcae/calibration/elasticity.py:404"');
    expect(called.result.content[0].text).toContain('"source": "symbol"');
  } finally {
    proc.kill();
  }
});

test("MCP preserves message boundaries and returns protocol errors", async () => {
  const { proc, writer, readLine } = startServer();
  try {
    const initialize = message(1, "initialize");
    writer.write(initialize.slice(0, 7));
    writer.write(initialize.slice(7));
    expect((await readLine()).result.serverInfo.name).toBe("glob");

    writer.write("not-json\n");
    const parseError = await readLine();
    expect(parseError.error.code).toBe(-32700);

    writer.write(`${JSON.stringify({ jsonrpc: "2.0", id: 2, method: "missing/method" })}\n`);
    const methodError = await readLine();
    expect(methodError.error.code).toBe(-32601);

    writer.write(`${JSON.stringify({ jsonrpc: "1.0", id: 3, method: "tools/list" })}\n`);
    const requestError = await readLine();
    expect(requestError.error.code).toBe(-32600);

    writer.write(message(4, "tools/call", { name: "glob_search", arguments: { root: "corpus/supply-chain-resilience-engine", query: "!!!" } }));
    const refusal = await readLine();
    expect(refusal.result.content[0].text).toContain("not enough signal");
  } finally {
    proc.kill();
  }
});
