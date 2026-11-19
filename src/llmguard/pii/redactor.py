"""Replace PII with placeholders like <PAN_1>, and optionally put it back."""

from dataclasses import dataclass, field

from llmguard.pii.detectors import Entity, detect


@dataclass
class RedactionResult:
    text: str
    # placeholder -> original value. Keep in memory only; never log or persist it.
    mapping: dict[str, str] = field(default_factory=dict, repr=False)
    entities: list[Entity] = field(default_factory=list)


def redact(text: str) -> RedactionResult:
    """Redact all detected PII. The same value always gets the same placeholder."""
    entities = detect(text)
    mapping: dict[str, str] = {}
    value_to_placeholder: dict[tuple[str, str], str] = {}
    counters: dict[str, int] = {}

    out: list[str] = []
    pos = 0
    for ent in entities:
        key = (ent.type, ent.value)
        placeholder = value_to_placeholder.get(key)
        if placeholder is None:
            counters[ent.type] = counters.get(ent.type, 0) + 1
            placeholder = f"<{ent.type}_{counters[ent.type]}>"
            value_to_placeholder[key] = placeholder
            mapping[placeholder] = ent.value
        out.append(text[pos : ent.start])
        out.append(placeholder)
        pos = ent.end
    out.append(text[pos:])
    return RedactionResult("".join(out), mapping, entities)


def restore(text: str, mapping: dict[str, str], allowed_types: set[str] | None = None) -> str:
    """Put original values back. If `allowed_types` is given, restore only those types."""
    for placeholder, value in mapping.items():
        ptype = placeholder[1:].rsplit("_", 1)[0]
        if allowed_types is None or ptype in allowed_types:
            text = text.replace(placeholder, value)
    return text
