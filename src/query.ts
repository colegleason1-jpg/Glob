/**
 * Query layer: search, findSymbol, trace, overview.
 * Every result is citation-first: file:line with provenance kind (symbol vs keyword).
 * Refusal over hallucination: thin evidence returns "not enough signal".
 */
import { Database } from "bun:sqlite";
import type { Citation, OverviewResult, Symbol, TraceResult } from "./types";

interface SymbolRow {
  file: string;
  name: string;
  kind: string;
  line: number;
  end_line: number;
}

const MIN_SCORE = 0.25;

function rowToSymbol(r: SymbolRow): Symbol {
  return { file: r.file, name: r.name, kind: r.kind as Symbol["kind"], line: r.line, endLine: r.end_line };
}

/** Escape a user string for FTS5 MATCH (treat as quoted phrase, allow inner quotes doubled). */
function ftsQuote(q: string): string {
  return `"${q.replace(/"/g, '""')}"`;
}

export function search(db: Database, query: string, limit = 10): { citations: Citation[]; refused?: string } {
  const trimmed = query.trim();
  if (!trimmed) return { citations: [], refused: "empty query" };

  const citations: Citation[] = [];

  // Layer 1: symbol names (strongest evidence).
  const symExact = db
    .query("SELECT * FROM symbols WHERE name = ? ORDER BY file LIMIT ?")
    .all(trimmed, limit) as unknown as SymbolRow[];
  for (const r of symExact) {
    citations.push({
      file: r.file,
      line: r.line,
      kind: "symbol",
      label: r.kind === "class" ? "class def" : "function def",
      text: `${r.kind} ${r.name} (lines ${r.line}–${r.end_line})`,
    });
  }

  const symLike = db
    .query("SELECT * FROM symbols WHERE name LIKE ? AND name != ? ORDER BY file LIMIT ?")
    .all(`%${trimmed}%`, trimmed, limit) as unknown as SymbolRow[];
  for (const r of symLike) {
    citations.push({
      file: r.file,
      line: r.line,
      kind: "symbol",
      label: `${r.kind} (partial)`,
      text: `${r.kind} ${r.name} (lines ${r.line}–${r.end_line})`,
    });
  }

  // Layer 2: FTS over lines.
  let ftsRows: { file: string; lineno: number; text: string; rank?: number }[] = [];
  try {
    ftsRows = db
      .query(
        `SELECT file, lineno, text FROM lines WHERE lines MATCH ? ORDER BY rank LIMIT ?`,
      )
      .all(ftsQuote(trimmed), limit) as unknown as { file: string; lineno: number; text: string; rank?: number }[];
  } catch {
    ftsRows = [];
  }
  for (const r of ftsRows) {
    citations.push({ file: r.file, line: r.lineno, kind: "keyword", text: r.text });
  }

  // Dedupe by file+line, keep first (symbol evidence wins by insertion order).
  const seen = new Set<string>();
  const deduped = citations.filter((c) => {
    const key = `${c.file}:${c.line}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  if (deduped.length === 0) {
    return { citations: [], refused: `no evidence for "${trimmed}" in this index — not guessing` };
  }
  return { citations: deduped.slice(0, limit) };
}

export function findSymbol(db: Database, name: string): Symbol[] {
  const rows = db
    .query("SELECT * FROM symbols WHERE name = ? OR name LIKE ? ORDER BY file, line LIMIT 100")
    .all(name, `%${name}%`) as unknown as SymbolRow[];
  return rows.map(rowToSymbol);
}

export function trace(db: Database, symbol: string): TraceResult {
  // Callers: functions whose line span contains a call to `symbol`.
  const callers = db
    .query(
      `SELECT DISTINCT s.* FROM symbols s JOIN calls c ON s.file = c.file
       WHERE s.kind = 'function' AND c.callee = ? AND s.line <= c.line AND c.line <= s.end_line
       ORDER BY s.file, s.line LIMIT 50`,
    )
    .all(symbol) as unknown as SymbolRow[];

  // Callees: symbols invoked from within any symbol named `symbol`.
  const calleeSyms: Symbol[] = [];
  const callsFromSpan = db
    .query(
      `SELECT c.callee, c.line, c.file FROM calls c JOIN symbols s
       ON s.file = c.file AND s.line <= c.line AND c.line <= s.end_line
       WHERE s.name = ? ORDER BY c.line LIMIT 100`,
    )
    .all(symbol) as unknown as { callee: string; line: number; file: string }[];
  for (const c of callsFromSpan) {
    const def = db
      .query("SELECT * FROM symbols WHERE name = ? ORDER BY file, line LIMIT 1")
      .get(c.callee) as unknown as SymbolRow | null;
    if (def) {
      const s = rowToSymbol(def);
      if (!calleeSyms.some((x) => x.file === s.file && x.line === s.line)) calleeSyms.push(s);
    }
  }

  // Importers: files whose text matches `import <symbol>` (FTS phrase-ish match).
  const importers = (
    db.query(
      `SELECT DISTINCT file FROM lines WHERE lines MATCH ? AND file NOT IN
       (SELECT file FROM symbols WHERE name = ?) LIMIT 50`,
    ).all(ftsQuote(`import ${symbol}`), symbol) as unknown as { file: string }[]
  ).map((r) => r.file);

  return { symbol, callers: callers.map(rowToSymbol), callees: calleeSyms, importers };
}

export function overview(db: Database): OverviewResult {
  const files = (db.query("SELECT COUNT(*) AS n FROM files").get() as unknown as { n: number }).n;
  const symbols = (db.query("SELECT COUNT(*) AS n FROM symbols").get() as unknown as { n: number }).n;
  const langs: Record<string, number> = {};
  for (const r of db.query("SELECT lang, COUNT(*) AS n FROM files GROUP BY lang").all() as unknown as {
    lang: string;
    n: number;
  }[]) {
    langs[r.lang] = r.n;
  }
  const topLevelDirs: { dir: string; files: number }[] = [];
  for (const r of db
    .query("SELECT SUBSTR(path, 1, INSTR(path, '/')) AS dir, COUNT(*) AS n FROM files WHERE path LIKE '%/%' GROUP BY dir ORDER BY n DESC LIMIT 12")
    .all() as unknown as { dir: string; n: number }[]) {
    topLevelDirs.push({ dir: r.dir, files: r.n });
  }
  const entryPoints = (
    db.query(
      `SELECT DISTINCT file FROM symbols WHERE name IN ('main','app','cli','serve','run') ORDER BY file LIMIT 10`,
    ).all() as unknown as { file: string }[]
  ).map((r) => r.file);
  return { files, languages: langs, symbols, topLevelDirs, entryPoints };
}

export { MIN_SCORE };
