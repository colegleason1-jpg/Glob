import { describe, expect, test } from "bun:test";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { initParser, extractRefs, extractSymbols } from "../src/symbols";
import { openIndex, replaceFile, removeFile, searchSymbols, findSymbols, traceSymbol } from "../src/store";

const source = `from audit import hash_input\n\nclass Ledger:\n    def solve(self, budget):\n        return hash_input(budget)\n`;

async function fixture() {
  const root = await mkdtemp(join(tmpdir(), "glob-test-"));
  const db = openIndex(root);
  await initParser();
  const symbols = extractSymbols(source);
  const refs = extractRefs(source);
  replaceFile(db, "app/ledger.py", 1, source.length, symbols, source, refs);
  return { root, db };
}

describe("Glob M1 engine", () => {
  test("extracts Python classes and functions with lines", async () => {
    await initParser();
    const symbols = extractSymbols(source);
    expect(symbols).toEqual([
      { kind: "class", name: "Ledger", line: 3 },
      { kind: "def", name: "solve", line: 4 },
    ]);
  });

  test("extracts call and identifier references", async () => {
    const refs = extractRefs(source);
    expect(refs.some((r) => r.name === "hash_input" && r.kind === "call" && r.line === 5)).toBe(true);
  });

  test("does not trace words inside comments or strings", async () => {
    const refs = extractRefs("# solve(hash_input)\nmessage = \"solve(hash_input)\"\nresult = solve(value)\n");
    expect(refs.filter((r) => r.name === "solve")).toEqual([{ name: "solve", line: 3, kind: "call" }]);
    expect(refs.some((r) => r.name === "hash_input")).toBe(false);
  });

  test("stores symbols and returns exact matches first", async () => {
    const { root, db } = await fixture();
    expect(searchSymbols(db, "solve")[0]).toMatchObject({ file: "app/ledger.py", name: "solve", score: 3 });
    db.close();
    await rm(root, { recursive: true, force: true });
  });

  test("returns full-text matches with a cited line", async () => {
    const { root, db } = await fixture();
    const hits = searchSymbols(db, "hash_input");
    expect(hits.some((h) => h.source === "keyword" && h.file === "app/ledger.py" && h.line === 1)).toBe(true);
    db.close();
    await rm(root, { recursive: true, force: true });
  });

  test("traces references by name", async () => {
    const { root, db } = await fixture();
    expect(traceSymbol(db, "hash_input")).toEqual([
      { file: "app/ledger.py", name: "hash_input", line: 1, kind: "identifier" },
      { file: "app/ledger.py", name: "hash_input", line: 5, kind: "call" },
    ]);
    db.close();
    await rm(root, { recursive: true, force: true });
  });

  test("refuses blank and punctuation-only queries", async () => {
    const { root, db } = await fixture();
    expect(searchSymbols(db, "   ")).toEqual([]);
    expect(searchSymbols(db, "!!!")).toEqual([]);
    expect(findSymbols(db, "")).toEqual([]);
    expect(traceSymbol(db, "")).toEqual([]);
    db.close();
    await rm(root, { recursive: true, force: true });
  });

  test("bounds result limits and removes deleted files", async () => {
    const { root, db } = await fixture();
    expect(searchSymbols(db, "solve", 0)).toEqual([]);
    removeFile(db, "app/ledger.py");
    expect(searchSymbols(db, "solve")).toEqual([]);
    expect(traceSymbol(db, "hash_input")).toEqual([]);
    db.close();
    await rm(root, { recursive: true, force: true });
  });

  test("refuses unknown queries", async () => {
    const { root, db } = await fixture();
    expect(searchSymbols(db, "not_present")).toEqual([]);
    db.close();
    await rm(root, { recursive: true, force: true });
  });
});
