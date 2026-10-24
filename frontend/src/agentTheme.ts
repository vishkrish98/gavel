export type AgentKey = "chair" | "policy_compiler" | "request_reader" | "skeptic" | "engine" | "optimizer" | "drafter";

export interface AgentInfo {
  key: AgentKey;
  name: string;
  role: string;
  monogram: string;
  color: string;
  /** Which usage-table agent family name(s) this nameplate tracks (empty for code-only roles). */
  usageFamilies: string[];
}

export const AGENTS: AgentInfo[] = [
  { key: "chair", name: "Chair", role: "Orchestrator", monogram: "Ch", color: "#cf9d3f", usageFamilies: [] },
  { key: "policy_compiler", name: "Policy Compiler", role: "Reads the policy", monogram: "PC", color: "#5b9bd5", usageFamilies: ["policy_compiler"] },
  { key: "request_reader", name: "Request Reader", role: "Classifies lines", monogram: "RR", color: "#5b9bd5", usageFamilies: ["request_reader"] },
  { key: "skeptic", name: "Skeptic", role: "Second-guesses allowed lines", monogram: "Sk", color: "#d99a3d", usageFamilies: ["skeptic"] },
  { key: "engine", name: "Engine", role: "Applies rules (code only)", monogram: "En", color: "#9a978c", usageFamilies: [] },
  { key: "optimizer", name: "Optimizer", role: "Funding scenarios (code only)", monogram: "Op", color: "#9a978c", usageFamilies: [] },
  { key: "drafter", name: "Drafter", role: "Drafts questions & memo", monogram: "Dr", color: "#4caf6b", usageFamilies: ["drafter_questions", "drafter_memo"] },
];
