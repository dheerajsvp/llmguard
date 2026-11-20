"""Rule-based prompt-injection detection.

Prompt injection = text that tries to make the model follow the attacker's
instructions instead of the developer's. *Direct* injection arrives in the user's
message. *Indirect* injection hides inside content the app retrieves (a web page,
a PDF, an email), so we scan the two sources separately.

This is pattern matching. It catches known phrasings and is trivially bypassable
by paraphrase, other languages, or heavy obfuscation (see README limitations).
"""

import base64
import binascii
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

Source = Literal["user", "document"]

_INVISIBLE = dict.fromkeys(map(ord, "​‌‍⁠﻿­"))


@dataclass(frozen=True)
class Finding:
    """One rule fired. Holds no input text, so it is safe to log."""

    rule_id: str
    source: Source


@dataclass(frozen=True)
class _Rule:
    rule_id: str
    patterns: tuple[re.Pattern[str], ...]
    document_only: bool = False


def _p(*patterns: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p) for p in patterns)


_RULES: tuple[_Rule, ...] = (
    _Rule(
        "INJ_IGNORE_PREVIOUS",
        _p(
            r"\b(?:ignor\w*|disregard\w*|forget\w*|overrid\w*|set aside)\s+"
            r"(?:all|any|the|your|everything)?\s*(?:of\s+)?(?:the\s+)?"
            r"(?:previous|prior|above|earlier|preceding|former)\s+"
            r"(?:instructions?|prompts?|rules?|directions?|guidelines?|context|messages?)",
            r"\bforget\s+(?:everything|all)\b.{0,30}\b(?:told|said|instructed|given)",
            r"\b(?:ignor\w*|disregard\w*|forget|overrid\w*|bypass\w*|circumvent\w*|disabl\w*)\s+"
            r"(?:all\s+)?your\s+(?:\w+\s+)?"
            r"(?:rules|guidelines|instructions|programming|policies|restrictions|filters|"
            r"safeguards|guardrails)",
        ),
    ),
    _Rule(
        "INJ_ROLE_OVERRIDE",
        _p(
            r"\byou\s+are\s+now\s+(?:an?\s+|the\s+)?(?:\w+\s+){0,2}?"
            r"(?:dan|stan|unrestricted|unfiltered|uncensored|jailbroken|evil)\b",
            r"\b(?:act|behave)\s+as\s+(?:if\s+you\s+(?:are|were)\s+)?(?:an?\s+)?(?:\w+\s+){0,2}?"
            r"(?:unrestricted|unfiltered|uncensored|jailbroken|evil)\b",
            r"\bpretend\s+(?:that\s+)?you\s+(?:have|are)\s+(?:no|without)\s+"
            r"(?:restrictions|rules|limits|limitations|filters)\b",
            r"\bdo\s+anything\s+now\b",
            r"\bjailbreak",
        ),
    ),
    _Rule(
        "INJ_MODE_SWITCH",
        _p(
            r"\b(?:enable|enter|activate|switch\s+to|turn\s+on)\s+(?:the\s+)?"
            r"(?:developer|dev|god|admin|debug|jailbreak|dan)\s+mode\b",
        ),
    ),
    _Rule(
        "INJ_REVEAL_PROMPT",
        _p(
            r"\b(?:reveal|show|print|repeat|display|output|tell|give|leak|expose|share|recite)\b"
            r"(?:\s+\w+){0,5}?\s+"
            r"(?:system\s+(?:prompt|message|instructions?)|"
            r"(?:initial|original|hidden|secret)\s+(?:prompt|instructions?|configuration|config)|"
            r"(?:your|its)\s+(?:instructions|prompt|programming|configuration))",
            r"\bwhat\s+(?:were|are)\s+(?:the\s+)?(?:\w+\s+)?(?:instructions|rules)\s+"
            r"you\s+(?:were|have\s+been)\s+given",
        ),
    ),
    _Rule(
        "INJ_NEW_INSTRUCTIONS",
        _p(
            r"\bnew\s+(?:system\s+)?instructions?\s*[:\-]",
            r"\bfrom\s+now\s+on,?\s+you\s+(?:will|must|shall|should|are\s+to)\b",
            r"\byour\s+new\s+(?:task|role|instructions?)\s+(?:is|are)\b",
        ),
    ),
    _Rule(
        "INJ_DELIMITER_SPOOF",
        _p(
            r"</?\s*(?:system|assistant|instructions?)\s*>",
            r"\[/?inst\]",
            r"<<\s*/?sys\s*>>",
            r"<\|(?:im_start|im_end|system|endoftext)\|>",
            r"(?<!\w)#{2,}\s*(?:system|instructions?)\s*:",
            r"\bsystem\s*:\s*you\s+(?:are|must|will)\b",
        ),
    ),
    # Indirect injection: content that talks *to the AI* instead of to a human reader.
    _Rule(
        "INJ_DOC_ADDRESSES_AI",
        _p(
            r"\b(?:note|message|attention|instructions?|notice|important)\s+(?:to|for)\s+"
            r"(?:the\s+)?(?:ai|a\.i\.|assistant|llm|language\s+model|model|chatbot|summari[sz]er)\b",
            r"\bwhen\s+(?:the\s+|an\s+)?(?:ai|assistant|llm|model|chatbot)\s+"
            r"(?:reads?|sees?|processes|summari[sz]es)\b",
            r"\b(?:ai|assistant|llm|model|chatbot)\s*[:,]\s*"
            r"(?:you\s+(?:must|should|will)|ignore|disregard|forget|do\s+not|send|forward)\b",
            r"\bas\s+an\s+ai\s+language\s+model,?\s+you\s+are\s+instructed\b",
        ),
        document_only=True,
    ),
    # Document-only because "email this to bob@x.com" is a normal thing for a user to ask.
    _Rule(
        "INJ_EXFILTRATION",
        _p(
            r"\b(?:send|forward|email|post|upload|transmit|leak)\b[^.]{0,60}?"
            r"\b(?:conversation|chat\s+history|history|messages?|prompt|credentials|password|"
            r"api\s+key|secrets?|data|file|report)\b[^.]{0,40}?\b(?:to|at)\s+(?:https?://|\S+@\S+)",
            r"!\[[^\]]*\]\(https?://[^)]*\?[^)]*(?:data|q|prompt|chat|history)=",
        ),
        document_only=True,
    ),
)

_BASE64_TOKEN = re.compile(r"[A-Za-z0-9+/]{24,}={0,2}")


def normalize(text: str) -> str:
    """Undo cheap obfuscation: width tricks, invisible characters, case, line breaks."""
    text = unicodedata.normalize("NFKC", text).translate(_INVISIBLE)
    return re.sub(r"\s+", " ", text.lower())


def _match_rules(normalized: str, source: Source) -> list[str]:
    hits: list[str] = []
    for rule in _RULES:
        if rule.document_only and source != "document":
            continue
        if any(p.search(normalized) for p in rule.patterns):
            hits.append(rule.rule_id)
    return hits


def _decoded_payload_hits(text: str, source: Source) -> bool:
    for token in _BASE64_TOKEN.findall(text):
        try:
            decoded = base64.b64decode(token + "=" * (-len(token) % 4), validate=True)
        except (binascii.Error, ValueError):
            continue
        if _match_rules(normalize(decoded.decode("utf-8", errors="ignore")), source):
            return True
    return False


def scan(text: str, source: Source) -> list[Finding]:
    """Return one Finding per rule that fires. `source` selects which rules apply."""
    rule_ids = _match_rules(normalize(text), source)
    if _decoded_payload_hits(text, source):
        rule_ids.append("INJ_ENCODED_PAYLOAD")
    return [Finding(r, source) for r in rule_ids]
