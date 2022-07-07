from typing import List

from experiment import Experiment


class Project:
    """
    Attributes:
      id, name, creator, experiments,
      total_scans, total_complete,
      MIQA
    Functions:
      get_experiment_by_id, add_experiment,
      list_all_objects, delete

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
        try:
            response = self.MIQA.make_request(f"experiments/{id}", GET=True)
        except Exception:
            return None
        new_experiment = Experiment(**dict(response, project=self))
        self.experiments.append(new_experiment)
        return new_experiment

    def add_experiment(self, name: str):
        response = self.MIQA.make_request(
            'experiments',
            POST=True,
            body={
                'name': name,
                'project': self.id,
            },
        )
        if not response:
            raise Exception('Failed to create experiment.')
        return Experiment(**dict(response, project=self))

    def list_all_objects(self, indent=0):
        print(" " * indent, str(self))
        for exp in self.experiments:
            exp.list_all_objects(indent=indent + 2)

    def delete(self):
        self.MIQA.make_request(
            f'projects/{self.id}',
            DELETE=True,
        )
        self.MIQA.projects = [proj for proj in self.MIQA.projects if proj.id != self.id]
        return True

    def __repr__(self):
        return f"Project {self.name}"
