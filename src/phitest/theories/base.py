from dataclasses import dataclass, field


@dataclass
class TheoryDefinition:
    key: str
    name: str
    summary: str
    predictions: list[str]
    relevant_protocols: list[str]
    limitations: str
    citation_notes: str


_REGISTRY: dict[str, TheoryDefinition] = {}


def register(t: TheoryDefinition) -> TheoryDefinition:
    _REGISTRY[t.key] = t
    return t


def get_theory(key: str) -> TheoryDefinition | None:
    return _REGISTRY.get(key)


def list_theories() -> list[TheoryDefinition]:
    return list(_REGISTRY.values())
