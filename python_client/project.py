from typing import List

from experiment import Experiment


class Project:
    """
    Attributes:
      id, name, creator, experiments,
      total_scans, total_complete
    Functions:
      list_all_objects

    """

    def __init__(
        self,
        id: str,
        name: str,
        creator: dict,
        status: dict,
        experiments: List[dict],
        **kwargs,
    ):
        self.id = id
        self.name = name
        self.creator = creator
        self.total_scans = status["total_scans"]
        self.total_complete = status["total_complete"]
        self.experiments = [Experiment(**exp) for exp in experiments]

    def list_all_objects(self, indent=0):
        print(" " * indent, str(self))
        for exp in self.experiments:
            exp.list_all_objects(indent=indent + 2)

    def __repr__(self):
        return f"Project {self.name}"
