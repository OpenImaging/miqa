from typing import List

from decision import ScanDecision
from frame import Frame


class Scan:
    """
    Attributes:
      id, name, decisions, frames,
      scan_type, suject_id, session_id, scan_link,
    Functions:
      list_all_objects

    """

    def __init__(
        self,
        id: str,
        name: str,
        decisions: List[dict],
        frames: List[dict],
        scan_type: str,
        subject_id: str,
        session_id: str,
        scan_link: str,
        **kwargs,
    ):
        self.id = id
        self.name = name
        self.decisions = [ScanDecision(**dec) for dec in decisions]
        self.frames = [Frame(**fr) for fr in frames]
        self.scan_type = scan_type
        self.subject_id = subject_id
        self.session_id = session_id
        self.scan_link = scan_link

    def list_all_objects(self, indent=0):
        print(" " * indent, str(self))
        print(" " * indent, "|Decisions:  ", self.decisions)
        print(" " * indent, "|Frames:  ", self.frames)

    def __repr__(self):
        return f"Scan {self.name}"
