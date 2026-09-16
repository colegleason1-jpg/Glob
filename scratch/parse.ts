// Spike 1.2 — parse one Python file, print all function/class defs with line numbers.
// Uses web-tree-sitter (WASM) for portability.
import { Parser, Language } from "web-tree-sitter";

const PY_WASM = "node_modules/tree-sitter-python/tree-sitter-python.wasm";

async function loadPython() {
  await Parser.init();
  return await Language.load(PY_WASM);
}

function walk(node: any, out: any[] = []): any[] {
  if (
    node.type === "function_definition" ||
    node.type === "class_definition"
  ) {
    const nameNode = node.childForFieldName("name");
    if (nameNode) {
      out.push({ kind: node.type, name: nameNode.text, line: node.startPosition.row + 1 });
    }
  }
  for (let i = 0; i < node.childCount; i++) walk(node.child(i), out);
  return out;
}

const [file] = process.argv.slice(2);
if (!file) {
  console.error("usage: bun scratch/parse.ts <file.py>");
  process.exit(1);
}

await Parser.init();
const parser = new Parser();
parser.setLanguage(await loadPython());
const source = await Bun.file(file).text();
const tree = parser.parse(source);
for (const d of walk(tree.rootNode)) {
  console.log(`${d.line}\t${d.kind === "class_definition" ? "class" : "def"}\t${d.name}`);
}
