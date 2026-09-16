// Glob — index storage. SQLite at <repo>/.glob/index.db.
// Step 2.2 scope: files / symbols / refs tables, incremental by mtime+size.
import { Database } from "bun:sqlite";
import { mkdirSync } from "node:fs";

export type FileRow = { path: string; mtime: number; size: number };
export type RefRow = { file: string; name: string; line: number; kind: string };

export function openIndex(root: string): Database {
  mkdirSync(`${root}/.glob`, { recursive: true });
  const db = new Database(`${root}/.glob/index.db`, { create: true });
  db.exec("PRAGMA journal_mode = WAL;");
  db.exec(`
    CREATE TABLE IF NOT EXISTS files (
      path TEXT PRIMARY KEY,
      mtime INTEGER NOT NULL,
      size INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS symbols (
      file TEXT NOT NULL,
      kind TEXT NOT NULL,
      name TEXT NOT NULL,
      line INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
    CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file);
    CREATE TABLE IF NOT EXISTS refs (
      file TEXT NOT NULL,
      name TEXT NOT NULL,
      line INTEGER NOT NULL,
      kind TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_refs_name ON refs(name);
    CREATE VIRTUAL TABLE IF NOT EXISTS content USING fts5(file UNINDEXED, body);
  `);
  // Migrate indexes created before the FTS table existed.
  const fileCount = (db.query("SELECT COUNT(*) AS n FROM files").get() as { n: number }).n;
  const contentCount = (db.query("SELECT COUNT(*) AS n FROM content").get() as { n: number }).n;
  const refCount = (db.query("SELECT COUNT(*) AS n FROM refs").get() as { n: number }).n;
  if (fileCount > 0 && (contentCount === 0 || refCount === 0)) {
    db.exec("DELETE FROM refs; DELETE FROM symbols; DELETE FROM files;");
  }
  return db;
}

export function knownFiles(db: Database): Map<string, FileRow> {
  const rows = db.query("SELECT path, mtime, size FROM files").all() as FileRow[];
  return new Map(rows.map((r) => [r.path, r]));
}

export function replaceFile(
  db: Database,
  path: string,
  mtime: number,
  size: number,
  symbols: { kind: string; name: string; line: number }[],
  body: string,
  refs: { name: string; line: number; kind: string }[],
): void {
  db.query("DELETE FROM refs WHERE file = ?").run(path);
  db.query("DELETE FROM symbols WHERE file = ?").run(path);
  db.query("DELETE FROM content WHERE file = ?").run(path);
  db.query("DELETE FROM files WHERE path = ?").run(path);
  db.query("INSERT INTO files (path, mtime, size) VALUES (?, ?, ?)").run(path, mtime, size);
  db.query("INSERT INTO content (file, body) VALUES (?, ?)").run(path, body);
  const ins = db.query("INSERT INTO symbols (file, kind, name, line) VALUES (?, ?, ?, ?)");
  for (const s of symbols) ins.run(path, s.kind, s.name, s.line);
  const refIns = db.query("INSERT INTO refs (file, name, line, kind) VALUES (?, ?, ?, ?)");
  for (const r of refs) refIns.run(path, r.name, r.line, r.kind);
}

export function removeFile(db: Database, path: string): void {
  db.query("DELETE FROM refs WHERE file = ?").run(path);
  db.query("DELETE FROM symbols WHERE file = ?").run(path);
  db.query("DELETE FROM content WHERE file = ?").run(path);
  db.query("DELETE FROM files WHERE path = ?").run(path);
}

export type SearchHit = {
  file: string;
  kind: string;
  name: string;
  line: number;
  score: number; // 3 exact symbol, 2 prefix, 1 substring, 0 keyword
  source: "symbol" | "keyword";
};

// Step 2.3 — search the symbols table. Exact > prefix > substring.
export function findSymbols(db: Database, query: string, limit = 50): SearchHit[] {
  const q = query.trim();
  if (!q) return [];
  const safeLimit = Math.max(0, Math.min(100, Math.floor(Number.isFinite(limit) ? limit : 50)));
  return (db.query(
    `SELECT file, kind, name, line FROM symbols
     WHERE lower(name) = lower(?) OR lower(name) LIKE lower(?)
     ORDER BY CASE WHEN lower(name) = lower(?) THEN 0 ELSE 1 END, file, line LIMIT ?`,
  ).all(q, `%${q}%`, q, safeLimit) as Omit<SearchHit, "score" | "source">[]).map((r) => ({
    ...r,
    score: r.name.toLowerCase() === q.toLowerCase() ? 3 : 1,
    source: "symbol" as const,
  }));
}

export function traceSymbol(db: Database, query: string, limit = 50): RefRow[] {
  const q = query.trim();
  if (!q) return [];
  const safeLimit = Math.max(0, Math.min(100, Math.floor(Number.isFinite(limit) ? limit : 50)));
  return db.query(
    `SELECT file, name, line, kind FROM refs WHERE lower(name) = lower(?)
     ORDER BY file, line LIMIT ?`,
  ).all(q, safeLimit) as RefRow[];
}

export function searchSymbols(db: Database, query: string, limit = 20): SearchHit[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const safeLimit = Math.max(0, Math.min(100, Math.floor(Number.isFinite(limit) ? limit : 20)));
  const rows = db
    .query(
      `SELECT file, kind, name, line FROM symbols
       WHERE instr(lower(name), ?) > 0
       ORDER BY file, line
       LIMIT ?`,
    )
    .all(q, safeLimit * 4) as Omit<SearchHit, "score">[];
  const scored = rows.map((r) => ({
    ...r,
    score: r.name.toLowerCase() === q ? 3 : r.name.toLowerCase().startsWith(q) ? 2 : 1,
    source: "symbol" as const,
  }));
  scored.sort((a, b) => b.score - a.score || a.file.localeCompare(b.file) || a.line - b.line);
  const ftsTerms = q.match(/[A-Za-z0-9_]+/g) ?? [];
  const keywordRows = ftsTerms.length === 0 ? [] : db
    .query(
      `SELECT file, body, snippet(content, 1, '[', ']', '…', 12) AS snippet
       FROM content WHERE content MATCH ? LIMIT ?`,
    )
    .all(ftsTerms.map((term) => `"${term}"`).join(" AND "), safeLimit) as { file: string; body: string; snippet: string }[];
  const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
  const keywordHits: SearchHit[] = keywordRows.map((r) => {
    const lines = r.body.split("\n");
    const line = Math.max(
      0,
      lines.findIndex((text) => terms.every((term) => text.toLowerCase().includes(term))),
      lines.findIndex((text) => terms.some((term) => text.toLowerCase().includes(term))),
    ) + 1;
    return {
    file: r.file,
    kind: "text",
    name: r.snippet,
    line,
    score: 0,
    source: "keyword",
    };
  });
  return [...scored, ...keywordHits]
    .sort((a, b) => b.score - a.score || a.file.localeCompare(b.file) || a.line - b.line)
    .slice(0, safeLimit);
}
