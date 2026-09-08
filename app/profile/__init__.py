"""Candidate profile data model and validation API."""

from .model import CandidateProfile, ProfileValidationError, validate_candidate_profile

__all__ = ["CandidateProfile", "ProfileValidationError", "validate_candidate_profile"]
