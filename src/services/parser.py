import re
import yaml
from dataclasses import dataclass, field

class CatalogParseError(Exception):
    pass

@dataclass
class ParsedMember:
    user_email: str
    role: str

@dataclass
class ParsedDependency:
    target_ref: str
    ref_kind: str
    protocol: str | None = None
    reason: str | None = None

@dataclass
class ParsedCatalog:
    domain: str
    system: str
    namespace: str
    service_id: str
    service_type: str
    name: str
    description: str | None
    review_branch: str
    members: list[ParsedMember] = field(default_factory=list)
    dependencies: list[ParsedDependency] = field(default_factory=list)

    @property
    def service_key(self) -> str:
        return f"{self.system}.{self.service_id}"

def parse_catalog_yaml(raw_text: str) -> ParsedCatalog:
    try:
        doc = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise CatalogParseError(f"Invalid YAML: {exc}")
    
    if not isinstance(doc, dict):
        raise CatalogParseError("Top-level YAML content must be a mapping")

    metadata = doc.get("metadata", {})
    spec = doc.get("spec", {})
    
    parsed = ParsedCatalog(
        domain=metadata.get("domain", ""),
        system=metadata.get("system", ""),
        namespace=metadata.get("namespace", ""),
        service_id=spec.get("id", ""),
        service_type=spec.get("type", ""),
        name=spec.get("name", ""),
        description=spec.get("description"),
        review_branch=spec.get("review", {}).get("branch", "main"),
    )

    for m in spec.get("owners", {}).get("members", []):
        parsed.members.append(ParsedMember(user_email=m.get("user"), role=m.get("role")))
        
    for t in spec.get("topology", []):
        ref = t.get("ref", "")
        kind = ref.split(":")[0] if ":" in ref else ""
        parsed.dependencies.append(ParsedDependency(
            target_ref=ref,
            ref_kind=kind,
            protocol=t.get("protocol"),
            reason=t.get("reason")
        ))
        
    return parsed
