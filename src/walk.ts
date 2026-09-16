// Glob — gitignore-aware file walk via `git ls-files`.
// Falls back to empty when the target is not a git repo (M1: corpus is one).
import { $ } from "bun";

export async function listFiles(root: string): Promise<string[]> {
  const out = await $`git -C ${root} ls-files --cached --others --exclude-standard`
    .quiet()
    .nothrow();
  if (out.exitCode !== 0) return [];
  return out.text().split("\n").filter((f) => f.endsWith(".py"));
}
