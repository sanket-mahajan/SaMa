"""Dependency-free candidate profile model and boundary validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from email.utils import parseaddr
import re
from typing import Any, Mapping
from urllib.parse import urlparse
from uuid import UUID


SCHEMA_VERSION = "candidate_profile.v1"
_E164_PHONE = re.compile(r"^\+[1-9]\d{7,14}$")


class ProfileValidationError(ValueError):
    """Raised when incoming candidate-profile data cannot be safely used."""

    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__("Invalid candidate profile: " + "; ".join(issues))


@dataclass(frozen=True)
class Link:
    label: str
    url: str


@dataclass(frozen=True)
class Skill:
    name: str
    years_experience: float | None = None


@dataclass(frozen=True)
class Experience:
    company: str
    title: str
    start_date: date
    end_date: date | None
    is_current: bool
    highlights: tuple[str, ...]


@dataclass(frozen=True)
class Education:
    institution: str
    qualification: str
    graduation_year: int | None = None


@dataclass(frozen=True)
class CandidateProfile:
    """A normalized, validated candidate profile used by downstream features."""

    candidate_id: UUID
    full_name: str
    email: str
    phone: str | None
    location: str | None
    summary: str | None
    links: tuple[Link, ...]
    skills: tuple[Skill, ...]
    experience: tuple[Experience, ...]
    education: tuple[Education, ...]
    schema_version: str = SCHEMA_VERSION


def validate_candidate_profile(payload: Mapping[str, Any]) -> CandidateProfile:
    """Validate an untrusted payload and return an immutable profile.

    The function collects independent problems so callers can show useful form
    feedback instead of failing one field at a time.
    """
    if not isinstance(payload, Mapping):
        raise ProfileValidationError(["profile must be an object"])

    issues: list[str] = []
    version = _required_string(payload, "schema_version", issues)
    if version and version != SCHEMA_VERSION:
        issues.append(f"schema_version must be {SCHEMA_VERSION!r}")

    candidate_id = _uuid(payload.get("candidate_id"), "candidate_id", issues)
    full_name = _required_string(payload, "full_name", issues)
    email = _email(payload.get("email"), issues)
    phone = _optional_string(payload, "phone", issues)
    if phone is not None and not _E164_PHONE.fullmatch(phone):
        issues.append("phone must use E.164 format, for example '+14155550123'")
    location = _optional_string(payload, "location", issues)
    summary = _optional_string(payload, "summary", issues)

    links = _links(payload.get("links", []), issues)
    skills = _skills(payload.get("skills"), issues)
    experience = _experience(payload.get("experience"), issues)
    education = _education(payload.get("education", []), issues)

    if issues:
        raise ProfileValidationError(issues)
    return CandidateProfile(
        candidate_id=candidate_id,
        full_name=full_name,
        email=email,
        phone=phone,
        location=location,
        summary=summary,
        links=tuple(links),
        skills=tuple(skills),
        experience=tuple(experience),
        education=tuple(education),
    )


def _required_string(value_source: Mapping[str, Any], key: str, issues: list[str]) -> str | None:
    value = value_source.get(key)
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{key} is required and must be a non-empty string")
        return None
    return value.strip()


def _optional_string(value_source: Mapping[str, Any], key: str, issues: list[str]) -> str | None:
    value = value_source.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{key} must be a non-empty string when provided")
        return None
    return value.strip()


def _uuid(value: Any, field: str, issues: list[str]) -> UUID | None:
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        issues.append(f"{field} must be a UUID")
        return None


def _email(value: Any, issues: list[str]) -> str | None:
    if not isinstance(value, str):
        issues.append("email is required and must be a valid email address")
        return None
    _, address = parseaddr(value.strip())
    if not address or address != value.strip() or address.count("@") != 1:
        issues.append("email is required and must be a valid email address")
        return None
    local, domain = address.rsplit("@", 1)
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        issues.append("email is required and must be a valid email address")
        return None
    return address


def _object_list(value: Any, field: str, issues: list[str], required: bool = False) -> list[Mapping[str, Any]]:
    if value is None and required:
        issues.append(f"{field} is required and must be a list")
        return []
    if not isinstance(value, list):
        issues.append(f"{field} must be a list")
        return []
    items: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            issues.append(f"{field}[{index}] must be an object")
        else:
            items.append(item)
    return items


def _links(value: Any, issues: list[str]) -> list[Link]:
    results = []
    for index, item in enumerate(_object_list(value, "links", issues)):
        label = _required_string(item, "label", issues)
        url = _required_string(item, "url", issues)
        if url and (urlparse(url).scheme not in {"http", "https"} or not urlparse(url).netloc):
            issues.append(f"links[{index}].url must be an absolute HTTP(S) URL")
        if label and url:
            results.append(Link(label, url))
    return results


def _skills(value: Any, issues: list[str]) -> list[Skill]:
    items = _object_list(value, "skills", issues, required=True)
    if not items:
        issues.append("skills must contain at least one item")
    results = []
    seen = set()
    for index, item in enumerate(items):
        name = _required_string(item, "name", issues)
        years = item.get("years_experience")
        if years is not None and (isinstance(years, bool) or not isinstance(years, (int, float)) or years < 0):
            issues.append(f"skills[{index}].years_experience must be a non-negative number")
            years = None
        if name:
            normalized = name.casefold()
            if normalized in seen:
                issues.append(f"skills[{index}].name duplicates another skill")
            seen.add(normalized)
            results.append(Skill(name, float(years) if years is not None else None))
    return results


def _parse_date(value: Any, field: str, issues: list[str]) -> date | None:
    if not isinstance(value, str):
        issues.append(f"{field} must be an ISO-8601 date (YYYY-MM-DD)")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        issues.append(f"{field} must be an ISO-8601 date (YYYY-MM-DD)")
        return None


def _experience(value: Any, issues: list[str]) -> list[Experience]:
    items = _object_list(value, "experience", issues, required=True)
    results = []
    for index, item in enumerate(items):
        company = _required_string(item, "company", issues)
        title = _required_string(item, "title", issues)
        start = _parse_date(item.get("start_date"), f"experience[{index}].start_date", issues)
        is_current = item.get("is_current")
        if not isinstance(is_current, bool):
            issues.append(f"experience[{index}].is_current must be a boolean")
        end_value = item.get("end_date")
        end = None if end_value is None else _parse_date(end_value, f"experience[{index}].end_date", issues)
        if is_current is True and end_value is not None:
            issues.append(f"experience[{index}].end_date must be omitted for a current role")
        if is_current is False and end_value is None:
            issues.append(f"experience[{index}].end_date is required for a past role")
        if start and end and end < start:
            issues.append(f"experience[{index}].end_date cannot be before start_date")
        highlights_value = item.get("highlights", [])
        if not isinstance(highlights_value, list) or not all(isinstance(h, str) and h.strip() for h in highlights_value):
            issues.append(f"experience[{index}].highlights must be a list of non-empty strings")
            highlights = []
        else:
            highlights = [h.strip() for h in highlights_value]
        if company and title and start and isinstance(is_current, bool) and (is_current or end):
            results.append(Experience(company, title, start, end, is_current, tuple(highlights)))
    return results


def _education(value: Any, issues: list[str]) -> list[Education]:
    results = []
    for index, item in enumerate(_object_list(value, "education", issues)):
        institution = _required_string(item, "institution", issues)
        qualification = _required_string(item, "qualification", issues)
        year = item.get("graduation_year")
        if year is not None and (isinstance(year, bool) or not isinstance(year, int) or not 1900 <= year <= 2100):
            issues.append(f"education[{index}].graduation_year must be an integer from 1900 to 2100")
            year = None
        if institution and qualification:
            results.append(Education(institution, qualification, year))
    return results
