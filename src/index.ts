#!/usr/bin/env bun
// Glob CLI — step 2.1/2.2: `glob index <path>`, incremental by mtime+size.
import { stat } from "node:fs/promises";
import { join } from "node:path";
import { initParser, extractSymbols, extractRefs } from "./symbols";
import { listFiles } from "./walk";
import { openIndex, knownFiles, replaceFile, removeFile, searchSymbols, findSymbols, traceSymbol } from "./store";

async function cmdIndex(root: string): Promise<void> {
  const t0 = performance.now();
  const parser = await initParser();
  const db = openIndex(root);
  const known = knownFiles(db);
  const files = await listFiles(root);

  let reindexed = 0;
  let unchanged = 0;
  const seen = new Set<string>();

  for (const rel of files) {
    seen.add(rel);
    const abs = join(root, rel);
    let st;
    try {
      st = await stat(abs);
    } catch {
      continue; // vanished between walk and stat
    }
    const mtime = Math.floor(st.mtimeMs);
    const prev = known.get(rel);
    if (prev && prev.mtime === mtime && prev.size === st.size) {
      unchanged++;
      continue;
    }
    let source: string;
    try {
      source = await Bun.file(abs).text();
    } catch {
      continue;
    }
    const symbols = extractSymbols(source);
    const refs = extractRefs(source);
    replaceFile(db, rel, mtime, st.size, symbols, source, refs);
    reindexed++;
  }

  // Drop files that no longer exist.
  for (const path of known.keys()) {
    if (!seen.has(path)) {
      removeFile(db, path);
      reindexed++; // counted as work done
    }
  }

  const ms = performance.now() - t0;
  console.log(
    `indexed ${files.length} files (${reindexed} reindexed, ${unchanged} unchanged) in ${ms.toFixed(0)} ms`,
  );
}

function cmdSearch(root: string, query: string): void {
  const db = openIndex(root);
  const hits = searchSymbols(db, query);
  if (hits.length === 0) {
    console.log(`no matches for '${query}'`); // refusal over silence
    return;
  }
  for (const h of hits) {
    const location = h.line > 0 ? `${h.file}:${h.line}` : h.file;
    console.log(`citation=${location}\tsource=${h.source}\tkind=${h.kind}\tname=${h.name}\tscore=${h.score}`);
  }
}

const [, , cmd, ...args] = process.argv;
if (cmd === "index") {
  const root = args[0] ?? ".";
  await cmdIndex(root);
} else if (cmd === "find-symbol") {
  const [root, ...rest] = args;
  if (!root || rest.length === 0) {
    console.error("usage: glob find-symbol <root> <name>");
    process.exit(1);
  }
  const db = openIndex(root);
  for (const h of findSymbols(db, rest.join(" "))) {
    console.log(`citation=${h.file}:${h.line}\tkind=${h.kind}\tname=${h.name}`);
  }
} else if (cmd === "trace") {
  const [root, ...rest] = args;
  if (!root || rest.length === 0) {
    console.error("usage: glob trace <root> <name>");
    process.exit(1);
  }
  const db = openIndex(root);
  const hits = traceSymbol(db, rest.join(" "));
  if (hits.length === 0) console.log(`no references for '${rest.join(" ")}'`);
  for (const h of hits) console.log(`citation=${h.file}:${h.line}\tkind=${h.kind}\tname=${h.name}`);
} else if (cmd === "search") {
  const [root, ...rest] = args;
  if (!root || rest.length === 0) {
    console.error("usage: glob search <root> <query>");
    process.exit(1);
  }
  cmdSearch(root, rest.join(" "));
} else {
  console.error("usage: glob <index|search|find-symbol|trace> ...");
  process.exit(1);
}
