#!/usr/bin/env bun
// Glob MCP transport — newline-delimited JSON-RPC over stdin/stdout.
// Deliberately dependency-free for the MVP: the protocol surface is tiny and stable.
import { listFiles } from "./walk";
import { openIndex, searchSymbols, findSymbols, traceSymbol } from "./store";

const toolDefinitions = [
  {
    name: "glob_overview",
    description: "Show the indexed repository structure and counts.",
    inputSchema: { type: "object", properties: { root: { type: "string" } }, required: ["root"] },
  },
  {
    name: "glob_search",
    description: "Search symbols and file contents with cited file:line results.",
    inputSchema: { type: "object", properties: { root: { type: "string" }, query: { type: "string" }, limit: { type: "number" } }, required: ["root", "query"] },
  },
  {
    name: "glob_find_symbol",
    description: "Find symbol definitions and return file:line citations.",
    inputSchema: { type: "object", properties: { root: { type: "string" }, name: { type: "string" } }, required: ["root", "name"] },
  },
  {
    name: "glob_trace",
    description: "Find indexed references to a symbol.",
    inputSchema: { type: "object", properties: { root: { type: "string" }, name: { type: "string" } }, required: ["root", "name"] },
  },
];

function result(text: string, isError = false) {
  return { content: [{ type: "text", text }], ...(isError ? { isError: true } : {}) };
}

async function callTool(name: string, args: Record<string, unknown>) {
  if (!args || typeof args !== "object" || Array.isArray(args)) throw new Error("arguments must be an object");
  const root = String(args.root ?? "");
  if (!root) throw new Error("root is required");
  if (name === "glob_overview") {
    const files = await listFiles(root);
    const db = openIndex(root);
    const counts = db.query("SELECT (SELECT COUNT(*) FROM symbols) AS symbols, (SELECT COUNT(*) FROM refs) AS refs").get() as { symbols: number; refs: number };
    db.close();
    return result(JSON.stringify({ root, pythonFiles: files.length, ...counts }, null, 2));
  }
  const db = openIndex(root);
  if (name === "glob_search") {
    const hits = searchSymbols(db, String(args.query ?? ""), Number(args.limit ?? 20));
    const response = result(hits.length ? JSON.stringify(hits.map((h) => ({
      citation: `${h.file}:${h.line}`,
      source: h.source,
      kind: h.kind,
      name: h.name,
      score: h.score,
    })), null, 2) : "not enough signal: no matches");
    db.close();
    return response;
  }
  if (name === "glob_find_symbol") {
    const hits = findSymbols(db, String(args.name ?? ""));
    const response = result(hits.length ? JSON.stringify(hits.map((h) => ({ citation: `${h.file}:${h.line}`, kind: h.kind, name: h.name })), null, 2) : "not enough signal: symbol not indexed");
    db.close();
    return response;
  }
  if (name === "glob_trace") {
    const hits = traceSymbol(db, String(args.name ?? ""));
    const response = result(hits.length ? JSON.stringify(hits.map((h) => ({ citation: `${h.file}:${h.line}`, kind: h.kind, name: h.name })), null, 2) : "not enough signal: no references indexed");
    db.close();
    return response;
  }
  throw new Error(`unknown tool: ${name}`);
}

function reply(id: unknown, response: unknown) {
  process.stdout.write(`${JSON.stringify({ jsonrpc: "2.0", id, result: response })}\n`);
}

function error(id: unknown, code: number, message: string) {
  process.stdout.write(`${JSON.stringify({ jsonrpc: "2.0", id, error: { code, message } })}\n`);
}

let buffer = "";
for await (const chunk of process.stdin) {
  buffer += chunk;
  const lines = buffer.split("\n");
  buffer = lines.pop() ?? "";
  for (const line of lines.filter(Boolean)) {
    try {
      const request = JSON.parse(line);
      if (!request || typeof request !== "object" || Array.isArray(request) || request.jsonrpc !== "2.0" || typeof request.method !== "string") {
        error(null, -32600, "invalid request");
        continue;
      }
      if (request.method === "initialize") {
        reply(request.id, { protocolVersion: "2024-11-05", capabilities: { tools: {} }, serverInfo: { name: "glob", version: "0.0.1" } });
      } else if (request.method === "notifications/initialized") {
        // Notification: no response.
      } else if (request.method === "tools/list") {
        reply(request.id, { tools: toolDefinitions });
      } else if (request.method === "tools/call") {
        try {
          reply(request.id, await callTool(request.params?.name, request.params?.arguments ?? {}));
        } catch (e) {
          reply(request.id, result(e instanceof Error ? e.message : String(e), true));
        }
      } else if (request.id !== undefined) {
        error(request.id, -32601, `method not found: ${request.method}`);
      }
    } catch (e) {
      error(null, -32700, e instanceof Error ? e.message : "invalid JSON");
    }
  }
}
