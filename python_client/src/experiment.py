from typing import List
import requests

from .scan import Scan


class Experiment:
    """
    Attributes:
      id, name, scans, project, note
    Functions:
      get_scan_by_id, add_scan,
      print_all_objects

    """

    def __init__(
        self,
        id: str,
        name: str,
        project,
        note: str,
        scans: List[dict] = [],
        **kwargs,
    ):
        self.id = id
        self.name = name
        self.scans = [Scan(**dict(scan, experiment=self)) for scan in scans]
        self.project = project
        self.note = note

    def get_scan_by_id(self, id: str):
        if self.scans:
            matches = [scan for scan in self.scans if scan.id == id]
            if len(matches) == 1:
                return matches[0]
        api_path = f"scans/{id}"
        response = requests.get(
            f"{self.project.MIQA.url}/{api_path}",
            headers=self.project.MIQA.headers,
        )
        if response.status_code == 404:
            return None
        new_scan = Scan(**dict(response.json(), experiment=self))
        self.scans.append(new_scan)
        return new_scan

    def add_scan(
        self,
        name: str,
        scan_type: str,
        subject_id: str = None,
        session_id: str = None,
        scan_link: str = None,
    ):
        api_path = "scans"
        response = requests.post(
            f"{self.project.MIQA.url}/{api_path}",
            headers=self.project.MIQA.headers,
            json={
                'name': name,
                'decisions': [],
                'frames': [],
                'scan_type': scan_type,
                'subject_id': subject_id,
                'session_id': session_id,
                'scan_link': scan_link,
                'experiment': self.id,
            },
        )
        response.raise_for_status()
        return Scan(**dict(response.json(), experiment=self))

    def update_note(self, note: str):
        api_path = f'experiments/{self.id}/note'
        response = requests.post(
            f"{self.project.MIQA.url}/{api_path}",
            headers=self.project.MIQA.headers,
            json={
                'note': note,
            },
        )
        response.raise_for_status()
        return True if response else False

    def print_all_objects(self, indent=0):
        print(" " * indent, str(self))
        for scan in self.scans:
            scan.print_all_objects(indent=indent + 2)

    def __repr__(self):
        return f"Experiment {self.name}"
