import { join } from "node:path";
import { openIndex, searchSymbols, traceSymbol } from "../src/store";
import { listFiles } from "../src/walk";

const root = process.argv[2] ?? "corpus/supply-chain-resilience-engine";
const cases = [
  { question: "provenance / audit", query: "provenance", mode: "search", expected: ["provenance"] },
  { question: "elasticity fit and refusal", query: "calibrate_elasticity", mode: "search", expected: ["calibrate_elasticity"] },
  { question: "solve callers", query: "solve", mode: "trace", expected: ["engine_client.py", "adapters.py"] },
  { question: "resource capacity", query: "capacity", mode: "search", expected: ["network.py", "optimizer.py"] },
];

const db = openIndex(root);
const files = await listFiles(root);
const rows: {
  question: string;
  files: number;
  globChars: number;
  baselineChars: number;
  globApproxTokens: number;
  baselineApproxTokens: number;
  reduction: string;
  expectedCitationFound: boolean;
}[] = [];

for (const test of cases) {
  const hits = test.mode === "trace" ? traceSymbol(db, test.query, 50) : searchSymbols(db, test.query, 20);
  const globText = hits.map((h) => `${h.file}:${h.line} ${"source" in h ? h.source : h.kind} ${h.kind} ${h.name}`).join("\n");
  const terms = test.query.toLowerCase().split(/\s+/);
  const matchingFiles: string[] = [];
  let baselineChars = 0;
  for (const rel of files) {
    const text = await Bun.file(join(root, rel)).text();
    if (terms.every((term) => text.toLowerCase().includes(term))) {
      matchingFiles.push(rel);
      baselineChars += text.length;
    }
  }
  const globTokens = Math.ceil(globText.length / 4);
  const baselineTokens = Math.ceil(baselineChars / 4);
  const reduction = baselineChars === 0 ? "n/a" : `${Math.max(0, (1 - globText.length / baselineChars) * 100).toFixed(1)}%`;
  const expectedCitationFound = test.expected.every((needle) => hits.some((h) => h.file.includes(needle) || h.name.includes(needle)));
  rows.push({
    question: test.question,
    files: matchingFiles.length,
    globChars: globText.length,
    baselineChars,
    globApproxTokens: globTokens,
    baselineApproxTokens: baselineTokens,
    reduction,
    expectedCitationFound,
  });
}

console.log(JSON.stringify({
  root,
  note: "Approximate retrieval context only: characters divided by four, not model-token telemetry or answer-quality measurement.",
  cases: rows,
}, null, 2));
db.close();
