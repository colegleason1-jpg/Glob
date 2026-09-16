// Spike 1.4 — walk + parse every .py file in a repo, report timing.
import { Parser, Language } from "web-tree-sitter";
import { $ } from "bun";

const PY_WASM = "node_modules/tree-sitter-python/tree-sitter-python.wasm";
await Parser.init();
const Py = await Language.load(PY_WASM);
const parser = new Parser();
parser.setLanguage(Py);

const [root = "."] = process.argv.slice(2);
const t0 = performance.now();
const ls = await $`git -C ${root} ls-files --cached --others --exclude-standard`
  .quiet()
  .nothrow();
const files = ls.text().split("\n").filter((f) => f.endsWith(".py"));
let parsed = 0;
let bytes = 0;
let failures = 0;
for (const f of files) {
  const src = await Bun.file(`${root}/${f}`).text();
  bytes += src.length;
  const tree = parser.parse(src);
  if (tree.rootNode.hasError) failures++;
  else parsed++;
}
const ms = performance.now() - t0;
console.log(`files: ${files.length} (parsed ${parsed}, withErrors ${failures})`);
console.log(`bytes: ${bytes}`);
console.log(`total: ${ms.toFixed(0)} ms  (${(ms / Math.max(parsed, 1)).toFixed(2)} ms/file)`);
