from typing import List

from scan import Scan


class Experiment:
    """
    Attributes:
      id, name, scans, project
    Functions:
      get_scan_by_id, add_scan,
      list_all_objects

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
        try:
            response = self.project.MIQA.make_request(f"scans/{id}", GET=True)
        except Exception:
            return None
        new_scan = Scan(**dict(response, experiment=self))
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
        response = self.project.MIQA.make_request(
            'scans',
            POST=True,
            body={
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
        if not response:
            raise Exception('Failed to create scan.')
        return Scan(**dict(response, experiment=self))

    def update_note(self, note: str):
        response = self.project.MIQA.make_request(
            f'experiments/{self.id}/note',
            POST=True,
            body={
                'note': note,
            },
        )
        return True if response else False

    def list_all_objects(self, indent=0):
        print(" " * indent, str(self))
        for scan in self.scans:
            scan.list_all_objects(indent=indent + 2)

    def __repr__(self):
        return f"Experiment {self.name}"
