"""Item Meaning domain scaffold."""

from reco.domain._scaffold import scaffold_placeholder
from reco.domain.item_meaning.model import ItemMeaning

scaffold_placeholder(module="item_meaning", concept="item_meaning")

__all__ = ["ItemMeaning"]
