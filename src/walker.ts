/** File walker with gitignore-lite and binary filtering. */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

/** Parse a .gitignore file into a list of pattern matchers (directory-anchored, fnmatch-style). */
export function parseGitignore(text: string): (relPath: string) => boolean {
  const lines = text.split("\n").map((l) => l.trim()).filter((l) => l && !l.startsWith("#"));
  const matchers: { pattern: string; negated: boolean; dirOnly: boolean }[] = [];
  for (const line of lines) {
    let pattern = line;
    let negated = false;
    let dirOnly = false;
    if (pattern.startsWith("!")) {
      negated = true;
      pattern = pattern.slice(1);
    }
    if (pattern.endsWith("/")) {
      dirOnly = true;
      pattern = pattern.slice(0, -1);
    }
    pattern = pattern.replace(/^\//, ""); // root-anchored only form we support
    if (pattern) matchers.push({ pattern, negated, dirOnly });
  }
  const fnmatch = (str: string, pat: string): boolean => {
    const rx = pat
      .replace(/[.+^${}()|[\]\\]/g, "\\$&")
      .replace(/\*\*/g, "\0")
      .replace(/\*/g, "[^/]*")
      .replace(/\?/g, "[^/]")
      .replace(/\0/g, ".*");
    return new RegExp(`^${rx}$`).test(str);
  };
  const matches = (relPath: string, m: { pattern: string; dirOnly: boolean }): boolean => {
    if (m.dirOnly && !relPath.endsWith("/")) {
      // match any path segment as a directory
      return relPath.split(sep).some((seg) => fnmatch(seg, m.pattern));
    }
    return fnmatch(relPath, m.pattern) || relPath.split(sep).some((seg) => fnmatch(seg, m.pattern));
  };
  return (relPath: string): boolean => {
    let ignored = false;
    for (const m of matchers) {
      if (matches(relPath, m)) ignored = !m.negated;
    }
    return ignored;
  };
}

export const DEFAULT_SKIP_DIRS = new Set([
  ".git", "node_modules", ".glob", "dist", "build", "__pycache__",
  ".venv", "venv", ".mypy_cache", ".pytest_cache", ".ruff_cache",
]);

const TEXT_EXTS = new Set([
  ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json", ".md", ".txt",
  ".yml", ".yaml", ".toml", ".cfg", ".ini", ".css", ".html", ".sh", ".sql", ".rs", ".go",
]);

export interface WalkedFile {
  /** repo-relative path with forward slashes */
  relPath: string;
  text: string;
}

/** Walk the repo collecting readable text files, honoring .gitignore and skip-dirs. */
export function collectFiles(root: string, maxFileBytes = 1_000_000): WalkedFile[] {
  const out: WalkedFile[] = [];
  let gitignore = (rel: string) => false;
  try {
    gitignore = parseGitignore(readFileSync(join(root, ".gitignore"), "utf8"));
  } catch {
    /* no gitignore */
  }
  const walk = (dir: string): void => {
    let entries: string[];
    try {
      entries = readdirSync(dir);
    } catch {
      return;
    }
    for (const entry of entries) {
      const full = join(dir, entry);
      const rel = relative(root, full).split(sep).join("/");
      let st;
      try {
        st = statSync(full);
      } catch {
        continue;
      }
      if (st.isDirectory()) {
        if (DEFAULT_SKIP_DIRS.has(entry) || gitignore(rel + "/")) continue;
        walk(full);
      } else if (st.isFile()) {
        if (gitignore(rel)) continue;
        const ext = rel.slice(rel.lastIndexOf("."));
        if (!TEXT_EXTS.has(ext)) continue;
        if (st.size > maxFileBytes) continue;
        try {
          out.push({ relPath: rel, text: readFileSync(full, "utf8") });
        } catch {
          /* unreadable */
        }
      }
    }
  };
  walk(root);
  return out;
}
