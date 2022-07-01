from typing import List

from scan import Scan


class Experiment:
    """
    Attributes:
      id, name, scans, project_id
    Functions:
      list_all_objects

    """

    def __init__(
        self,
        id: str,
        name: str,
        scans: List[dict],
        project: str,
        **kwargs,
    ):
        self.id = id
        self.name = name
        self.scans = [Scan(**scan) for scan in scans]
        self.project_id = project

    def list_all_objects(self, indent=0):
        print(" " * indent, str(self))
        for scan in self.scans:
            scan.list_all_objects(indent=indent + 2)

    def __repr__(self):
        return f"Experiment {self.name}"
