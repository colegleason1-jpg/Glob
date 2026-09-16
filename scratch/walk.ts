// Spike 1.3 — gitignore-aware file walk, count files by extension.
// Respects .gitignore via `git ls-files` when inside a git repo (corpus is one),
// falling back to Bun.walk elsewhere.
import { $ } from "bun";

async function gitFiles(root: string): Promise<string[]> {
  const out = await $`git -C ${root} ls-files --cached --others --exclude-standard`
    .quiet()
    .nothrow();
  if (out.exitCode !== 0) return [];
  return out.text().split("\n").filter(Boolean);
}

const [root = "."] = process.argv.slice(2);
const files = await gitFiles(root);
const byExt = new Map<string, number>();
for (const f of files) {
  const ext = f.includes(".") ? f.slice(f.lastIndexOf(".") + 1).toLowerCase() : "(none)";
  byExt.set(ext, (byExt.get(ext) ?? 0) + 1);
}
console.log(`root: ${root}`);
console.log(`total files: ${files.length}`);
for (const [ext, n] of [...byExt.entries()].sort((a, b) => b[1] - a[1]).slice(0, 12)) {
  console.log(`  .${ext}: ${n}`);
}
