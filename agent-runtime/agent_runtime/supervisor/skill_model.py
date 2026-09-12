"""Immutable value objects used by conversation workspace skills."""

from dataclasses import dataclass
import hashlib


@dataclass(frozen=True, slots=True)
class SkillDescriptor:
    """The immutable identity and storage location of one skill version."""

    skill_id: str
    version_id: str
    name: str
    description: str
    object_key: str

    @property
    def cache_key(self) -> str:
        """Return an opaque disk-safe key isolated by skill and version."""
        return hashlib.sha256(f"{self.skill_id}\0{self.version_id}".encode()).hexdigest()
