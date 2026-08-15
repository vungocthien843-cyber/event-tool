import re
from dataclasses import dataclass, field

import yaml

_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")

ALLOWED_SERVICE_TYPES = {
    "service",
    "gateway",
    "worker",
    "batch",
    "job",
    "library",
    "website",
    "mobile-app",
    "data-pipeline",
    "function",
    "plugin",
    "tool",
    "documentation",
    "other",
}

ALLOWED_REF_KINDS = {
    "system",
    "resource",
    "component",
    "providesApis",
    "consumesApis",
    "publishesTo",
    "consumesFrom",
}

ALLOWED_MEMBER_ROLES = {"techlead", "maintainer", "member"}


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


def _require(d: dict, path: str):
    """Look up a dotted path in nested dicts, raising CatalogParseError if missing."""
    node = d
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node or node[key] in (None, ""):
            raise CatalogParseError(f"Missing required field: {path}")
        node = node[key]
    return node


def _require_slug(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _SLUG_RE.match(value):
        raise CatalogParseError(
            f"Field {field_name!r} must match ^[a-z][a-z0-9-]*$, got: {value!r}"
        )
    return value


def _parse_ref_kind(ref: str) -> str:
    if not isinstance(ref, str) or ":" not in ref:
        raise CatalogParseError(f"Invalid topology ref (missing ':'): {ref!r}")
    kind, _, _ = ref.partition(":")
    if kind not in ALLOWED_REF_KINDS:
        raise CatalogParseError(f"Unrecognized topology ref kind {kind!r} in ref: {ref!r}")
    return kind


def parse_catalog_yaml(raw_text: str) -> ParsedCatalog:
    try:
        doc = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise CatalogParseError(f"Invalid YAML: {exc}") from exc

    if not isinstance(doc, dict):
        raise CatalogParseError("Top-level YAML content must be a mapping")

    domain = _require(doc, "metadata.domain")
    system = _require_slug(_require(doc, "metadata.system"), "metadata.system")
    namespace = _require_slug(_require(doc, "metadata.namespace"), "metadata.namespace")

    service_type = _require(doc, "spec.type")
    if service_type not in ALLOWED_SERVICE_TYPES:
        raise CatalogParseError(f"Unrecognized spec.type: {service_type!r}")

    service_id = _require_slug(_require(doc, "spec.id"), "spec.id")
    name = _require(doc, "spec.name")
    description = doc.get("spec", {}).get("description")
    review_branch = _require(doc, "spec.review.branch")

    raw_members = _require(doc, "spec.owners.members")
    if not isinstance(raw_members, list) or len(raw_members) == 0:
        raise CatalogParseError("spec.owners.members must be a non-empty list")

    members: list[ParsedMember] = []
    for m in raw_members:
        user_email = _require(m, "user")
        role = _require(m, "role")
        if role not in ALLOWED_MEMBER_ROLES:
            raise CatalogParseError(f"Unrecognized member role: {role!r}")
        members.append(ParsedMember(user_email=user_email, role=role))

    raw_topology = doc.get("spec", {}).get("topology") or []
    if not isinstance(raw_topology, list):
        raise CatalogParseError("spec.topology must be a list")

    dependencies: list[ParsedDependency] = []
    for t in raw_topology:
        target_ref = _require(t, "ref")
        ref_kind = _parse_ref_kind(target_ref)
        dependencies.append(
            ParsedDependency(
                target_ref=target_ref,
                ref_kind=ref_kind,
                protocol=t.get("protocol"),
                reason=t.get("reason"),
            )
        )

    return ParsedCatalog(
        domain=domain,
        system=system,
        namespace=namespace,
        service_id=service_id,
        service_type=service_type,
        name=name,
        description=description,
        review_branch=review_branch,
        members=members,
        dependencies=dependencies,
    )
