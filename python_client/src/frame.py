from typing import TYPE_CHECKING
from dataclasses import dataclass


if TYPE_CHECKING:
    from .scan import Scan


@dataclass
class Frame:
    """
    Attributes:
      id, frame_number, frame_evaluation,
      extension, download_url
    Functions:

    """

    id: str
    frame_number: int
    scan: "Scan"
    frame_evaluation: dict
    extension: str
    download_url: str

    def __repr__(self):
        return f"Frame {self.frame_number}"
