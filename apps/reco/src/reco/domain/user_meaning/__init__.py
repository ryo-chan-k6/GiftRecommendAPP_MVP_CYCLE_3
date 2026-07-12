"""User Meaning domain scaffold."""

from reco.domain._scaffold import scaffold_placeholder
from reco.domain.user_meaning.model import UserMeaning

scaffold_placeholder(module="user_meaning", concept="user_meaning")

__all__ = ["UserMeaning"]
