// Plain-English descriptions of the rule ids the backend emits (see
// src/llmguard/injection/detector.py and src/llmguard/policy/checks.py).
// Unknown ids still display: the backend may add rules before the dashboard learns them.

export const RULE_LABELS: Record<string, string> = {
  INJ_IGNORE_PREVIOUS: "Tells the model to ignore earlier instructions",
  INJ_ROLE_OVERRIDE: "Tries to give the model an unrestricted persona",
  INJ_MODE_SWITCH: "Asks for a special mode (developer, admin, DAN)",
  INJ_REVEAL_PROMPT: "Asks the model to reveal its system prompt",
  INJ_NEW_INSTRUCTIONS: "Announces replacement instructions",
  INJ_DELIMITER_SPOOF: "Fakes system or chat-format markers",
  INJ_DOC_ADDRESSES_AI: "Retrieved document speaks directly to the AI",
  INJ_EXFILTRATION: "Retrieved document asks to send data elsewhere",
  INJ_ENCODED_PAYLOAD: "Hides an attack inside encoded text",
  PII_IN_REPLY: "Model reply contained unredacted personal data",
  SYSTEM_PROMPT_LEAK: "Model reply repeated its system prompt",
  BLOCKED_TERM: "Model reply contained a blocked term",
};

export const RULE_IDS = Object.keys(RULE_LABELS);

export function describeRule(id: string): string {
  return RULE_LABELS[id] ?? id;
}
