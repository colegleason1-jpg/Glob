/** Shared types for Glob. */

export interface Symbol {
  file: string;
  name: string;
  kind: "function" | "class";
  line: number; // 1-based
  endLine: number; // 1-based inclusive
}

export type EvidenceKind = "symbol" | "keyword";

export interface Citation {
  file: string;
  line: number;
  kind: EvidenceKind;
  label?: string; // e.g. "function def", "class def"
  text: string;
}

export interface SearchHit {
  citations: Citation[];
}

export interface TraceResult {
  symbol: string;
  callers: Symbol[];
  callees: Symbol[];
  importers: string[];
}

export interface OverviewResult {
  files: number;
  languages: Record<string, number>;
  symbols: number;
  topLevelDirs: { dir: string; files: number }[];
  entryPoints: string[];
}
