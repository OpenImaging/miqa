from typing import TYPE_CHECKING
from dataclasses import dataclass


if TYPE_CHECKING:
    from .scan import Scan


@dataclass
class ScanDecision:
    """
    Attributes:
      id, decision, creator, created, note,
      user_identified_artifacts, location
    Functions:

    """

    id: str
    decision: str
    scan: "Scan"
    creator: dict
    created: str
    note: str
    user_identified_artifacts: dict
    location: dict

    def __repr__(self):
        return f"Scan Decision {self.decision}"
