// Glob — symbol extraction via tree-sitter (WASM).
// M1 scope: Python first. Line numbers are 1-based.
import { Parser, Language } from "web-tree-sitter";

const PY_WASM = "node_modules/tree-sitter-python/tree-sitter-python.wasm";

export type Sym = {
  kind: "def" | "class";
  name: string;
  line: number;
};

let parser: Parser | null = null;
let pyLang: Language | null = null;

export async function initParser(): Promise<Parser> {
  if (parser) return parser;
  await Parser.init();
  pyLang = await Language.load(PY_WASM);
  parser = new Parser();
  parser.setLanguage(pyLang);
  return parser;
}

export function extractRefs(source: string): { name: string; line: number; kind: string }[] {
  if (!parser) throw new Error("initParser() not called");
  const tree = parser.parse(source);
  if (!tree) return [];
  const refs: { name: string; line: number; kind: string }[] = [];
  const keywords = new Set(["and", "as", "assert", "async", "await", "break", "case", "class", "continue", "def", "del", "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "match", "nonlocal", "not", "or", "pass", "raise", "return", "try", "while", "with", "yield"]);
  const visit = (node: any): void => {
    if (node.type === "identifier" && !keywords.has(node.text)) {
      let ancestor = node.parent;
      let isCall = false;
      for (let depth = 0; ancestor && depth < 3; depth++, ancestor = ancestor.parent) {
        if (ancestor.type !== "call") continue;
        const functionNode = ancestor.childForFieldName("function");
        const functionText = functionNode?.text ?? "";
        isCall = functionText === node.text || functionText.endsWith(`.${node.text}`);
        break;
      }
      refs.push({ name: node.text, line: node.startPosition.row + 1, kind: isCall ? "call" : "identifier" });
    }
    for (let i = 0; i < node.childCount; i++) visit(node.child(i));
  };
  visit(tree.rootNode);
  return refs;
}

export function extractSymbols(source: string): Sym[] {
  if (!parser) throw new Error("initParser() not called");
  const tree = parser.parse(source);
  if (!tree) return [];
  const out: Sym[] = [];
  const visit = (node: any): void => {
    if (node.type === "function_definition" || node.type === "class_definition") {
      const nameNode = node.childForFieldName("name");
      if (nameNode) {
        out.push({
          kind: node.type === "class_definition" ? "class" : "def",
          name: nameNode.text,
          line: node.startPosition.row + 1,
        });
      }
    }
    for (let i = 0; i < node.childCount; i++) visit(node.child(i));
  };
  visit(tree.rootNode);
  return out;
}
