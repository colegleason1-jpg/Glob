/**
 * Indexer: walk files, parse Python with tree-sitter, build a SQLite index.
 * Index lives at <repo>/.glob/index.db. Rebuild is cheap for MVP (no incremental yet).
 */
import { mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { Database } from "bun:sqlite";
import { collectFiles } from "./walker";
import { initParser, extractPythonSymbols, extractPythonCalls } from "./parse";

export const INDEX_DIR = ".glob";
export const INDEX_FILE = "index.db";

export interface IndexStats {
  files: number;
  symbols: number;
  calls: number;
  lines: number;
  durationMs: number;
  dbPath: string;
}

export function openIndex(repoRoot: string): Database {
  const dbPath = join(repoRoot, INDEX_DIR, INDEX_FILE);
  const db = new Database(dbPath);
  db.exec("PRAGMA journal_mode = WAL;");
  return db;
}

export function createSchema(db: Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS files (
      path TEXT PRIMARY KEY,
      lang TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS symbols (
      file TEXT NOT NULL,
      name TEXT NOT NULL,
      kind TEXT NOT NULL,
      line INTEGER NOT NULL,
      end_line INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS calls (
      file TEXT NOT NULL,
      callee TEXT NOT NULL,
      line INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_calls_callee ON calls(callee);
    CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
    CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file);
    CREATE VIRTUAL TABLE IF NOT EXISTS lines USING fts5(file UNINDEXED, lineno UNINDEXED, text);
  `);
}

/** Tokenize source into FTS-friendly per-line rows (skip blank/noise lines). */
function lineRows(path: string, text: string): { file: string; lineno: number; text: string }[] {
  const rows: { file: string; lineno: number; text: string }[] = [];
  const lines = text.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line === undefined) continue;
    const trimmed = line.trim();
    if (!trimmed) continue;
    rows.push({ file: path, lineno: i + 1, text: trimmed });
  }
  return rows;
}

function detectLang(path: string): string | null {
  if (path.endsWith(".py")) return "python";
  if (/\.tsx?$/.test(path) || /\.m?jsx?$/.test(path)) return "typescript";
  return null;
}

/** Build (rebuild) the index for a repo root. */
export async function indexRepo(repoRoot: string): Promise<IndexStats> {
  const start = performance.now();
  const dbPath = join(repoRoot, INDEX_DIR, INDEX_FILE);
  mkdirSync(join(repoRoot, INDEX_DIR), { recursive: true });

  const files = collectFiles(repoRoot);

  // Parse first so a grammar failure aborts before we clobber the old index.
  await initParser();
  const parsed = files.map((f) => {
    const lang = detectLang(f.relPath);
    const isPy = lang === "python";
    return {
      ...f,
      lang,
      symbols: isPy ? extractPythonSymbols(f.text) : [],
      calls: isPy ? extractPythonCalls(f.text) : [],
    };
  });

  rmSync(dbPath, { force: true });
  const db = openIndex(repoRoot);
  createSchema(db);

  const insertFile = db.prepare("INSERT INTO files (path, lang) VALUES (?, ?)");
  const insertSymbol = db.prepare("INSERT INTO symbols (file, name, kind, line, end_line) VALUES (?, ?, ?, ?, ?)");
  const insertCall = db.prepare("INSERT INTO calls (file, callee, line) VALUES (?, ?, ?)");
  const insertLine = db.prepare("INSERT INTO lines (file, lineno, text) VALUES (?, ?, ?)");

  let symbolCount = 0;
  let callCount = 0;
  let lineCount = 0;
  db.transaction(() => {
    for (const f of parsed) {
      insertFile.run(f.relPath, f.lang ?? "other");
      for (const s of f.symbols) {
        insertSymbol.run(f.relPath, s.name, s.kind, s.line, s.endLine);
        symbolCount++;
      }
      for (const c of f.calls) {
        insertCall.run(f.relPath, c.callee, c.line);
        callCount++;
      }
      for (const row of lineRows(f.relPath, f.text)) {
        insertLine.run(row.file, row.lineno, row.text);
        lineCount++;
      }
    }
  })();

  const durationMs = Math.round(performance.now() - start);
  db.close();
  return { files: parsed.length, symbols: symbolCount, calls: callCount, lines: lineCount, durationMs, dbPath };
}
