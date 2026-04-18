/**
 * Agent card for `/.well-known/agent*.json` — mirrors Python `build_agent_card`.
 */
export interface AgentSkill {
  id: string;
  name: string;
  description: string;
}

export interface AgentCard {
  name: string;
  version: string;
  description: string;
  skills: AgentSkill[];
}

export function buildAgentCard(toolDefinitions: Array<Record<string, unknown>>): AgentCard {
  const skills: AgentSkill[] = [];
  for (const tool of toolDefinitions) {
    skills.push({
      id: String(tool["name"] ?? ""),
      name: String(tool["name"] ?? ""),
      description: String(tool["description"] ?? ""),
    });
  }
  return {
    name: "vermyth",
    version: "0.1.0",
    description: "Semantic IR runtime with MCP tool surface.",
    skills,
  };
}
