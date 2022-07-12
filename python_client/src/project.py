from typing import List
import requests

from .experiment import Experiment


class Project:
    """
    Attributes:
      id, name, creator, experiments,
      total_scans, total_complete,
      MIQA
    Functions:
      get_experiment_by_id, add_experiment,
      print_all_objects, delete

    """

    def __init__(
        self,
        id: str,
        name: str,
        creator: dict,
        status: dict,
        experiments: List[dict],
        MIQA,
        **kwargs,
    ):
        self.id = id
        self.name = name
        self.creator = creator
        self.total_scans = status["total_scans"]
        self.total_complete = status["total_complete"]
        self.experiments = [Experiment(**dict(exp, project=self)) for exp in experiments]
        self.MIQA = MIQA

    def get_experiment_by_id(self, id: str):
        if self.experiments:
            matches = [exp for exp in self.experiments if exp.id == id]
            if len(matches) == 1:
                return matches[0]
        api_path = f"experiments/{id}"
        response = requests.get(
            f"{self.MIQA.url}/{api_path}",
            headers=self.MIQA.headers,
        )
        if response.status_code == 404:
            return None
        new_experiment = Experiment(**dict(response.json(), project=self))
        self.experiments.append(new_experiment)
        return new_experiment

    def add_experiment(self, name: str):
        api_path = "experiments"
        response = requests.post(
            f"{self.MIQA.url}/{api_path}",
            headers=self.MIQA.headers,
            json={
                'name': name,
                'project': self.id,
            },
        )
        response.raise_for_status()
        return Experiment(**dict(response.json(), project=self))

    def print_all_objects(self, indent=0):
        print(" " * indent, str(self))
        for exp in self.experiments:
            exp.print_all_objects(indent=indent + 2)

    def delete(self):
        api_path = f'projects/{self.id}'
        response = requests.delete(
            f"{self.MIQA.url}/{api_path}",
            headers=self.MIQA.headers,
        )
        response.raise_for_status()
        self.MIQA.projects = [proj for proj in self.MIQA.projects if proj.id != self.id]
        return True

    def __repr__(self):
        return f"Project {self.name}"
