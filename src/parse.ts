/**
 * Tree-sitter (wasm) loader for Python.
 * Uses web-tree-sitter with the prebuilt tree-sitter-python.wasm — no native builds.
 */
import { existsSync } from "node:fs";
import { join } from "node:path";

// Minimal structural types for web-tree-sitter to avoid type friction.
export interface TSNode {
  type: string;
  text: string;
  startPosition: { row: number; column: number };
  endPosition: { row: number; column: number };
  children: TSNode[];
  childByFieldName(name: string): TSNode | null;
}
export interface TSTree {
  rootNode: TSNode;
}
interface TSParser {
  setLanguage(lang: unknown): void;
  parse(input: string): TSTree;
}

let parser: TSParser | null = null;

/** Locate the prebuilt grammar wasm across common layouts. */
function findPythonWasm(): string {
  const candidates = [
    join(import.meta.dir, "../../tree-sitter-python/tree-sitter-python.wasm"), // package installed as dependency
    join(import.meta.dir, "../node_modules/tree-sitter-python/tree-sitter-python.wasm"), // repo root
    join(process.cwd(), "node_modules/tree-sitter-python/tree-sitter-python.wasm"),
  ];
  for (const c of candidates) if (existsSync(c)) return c;
  throw new Error("tree-sitter-python.wasm not found; is the tree-sitter-python dependency installed?");
}

/** Load the wasm runtime + Python grammar once per process. */
export async function initParser(): Promise<void> {
  if (parser) return;
  const mod = await import("web-tree-sitter");
  const Parser = (mod.default ?? mod) as unknown as {
    init: () => Promise<void>;
    Language: { load: (p: string) => Promise<unknown> };
    new (): TSParser;
  };
  await Parser.init();
  const pyLang = await Parser.Language.load(findPythonWasm());
  const p = new Parser();
  p.setLanguage(pyLang);
  parser = p;
}

/** Parse source and return the root node. Throws if initParser() has not run. */
export function parsePython(source: string): TSNode {
  if (!parser) throw new Error("parser not initialized; call initParser() first");
  return parser.parse(source).rootNode;
}

function functionName(node: TSNode): string | null {
  const n = node.childByFieldName("name");
  return n ? n.text : null;
}

/**
 * Extract function/class definitions and call expressions.
 * Line numbers are 1-based inclusive spans.
 */
export function extractPythonSymbols(source: string): {
  name: string;
  kind: "function" | "class";
  line: number;
  endLine: number;
}[] {
  const root = parsePython(source);
  const out: { name: string; kind: "function" | "class"; line: number; endLine: number }[] = [];
  const walk = (node: TSNode): void => {
    if (node.type === "function_definition" || node.type === "class_definition") {
      const name = functionName(node);
      if (name) {
        out.push({
          name,
          kind: node.type === "function_definition" ? "function" : "class",
          line: node.startPosition.row + 1,
          endLine: node.endPosition.row + 1,
        });
      }
    }
    for (const child of node.children) walk(child);
  };
  walk(root);
  return out;
}

export interface CallSite {
  callee: string;
  line: number;
}

/** Extract simple name calls and attribute calls (method.resolved part only). */
export function extractPythonCalls(source: string): CallSite[] {
  const root = parsePython(source);
  const out: CallSite[] = [];
  const walk = (node: TSNode): void => {
    if (node.type === "call") {
      const fn = node.childByFieldName("function");
      if (fn) {
        // plain name call: foo(...) — function field is an identifier
        if (fn.type === "identifier") {
          out.push({ callee: fn.text, line: node.startPosition.row + 1 });
        } else if (fn.type === "attribute") {
          // foo.bar(...) — attribute node has field "attribute" for the method name
          const attr = fn.childByFieldName("attribute");
          if (attr) out.push({ callee: attr.text, line: node.startPosition.row + 1 });
        }
      }
    }
    for (const child of node.children) walk(child);
  };
  walk(root);
  return out;
}
