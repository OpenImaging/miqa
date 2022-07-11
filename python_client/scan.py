from typing import List

from decision import ScanDecision
from frame import Frame


class Scan:
    """
    Attributes:
      id, name, experiment, decisions, frames,
      scan_type, suject_id, session_id, scan_link,
    Functions:
      print_all_objects

    """

    def __init__(
        self,
        id: str,
        name: str,
        experiment,
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
        self.experiment = experiment
        self.decisions = [ScanDecision(**dec, scan=self) for dec in decisions]
        self.frames = [Frame(**fr, scan=self) for fr in frames]
        self.scan_type = scan_type
        self.subject_id = subject_id
        self.session_id = session_id
        self.scan_link = scan_link

    def add_frames_from_paths(self, *paths: List[str]):
        new_frames = []
        for index, path in enumerate(paths):
            field_value = self.experiment.project.MIQA.upload_file(
                path,
                'core.Frame.response',
            )
            response = self.experiment.project.MIQA.make_request(
                'frames',
                POST=True,
                body={
                    'response': field_value,
                    'filename': path.split('/')[-1],
                    'scan': self.id,
                    'frame_number': index,
                },
            )
            new_frame = Frame(**dict(response, scan=self))
            new_frames.append(new_frame)
            self.frames.append(new_frame)
        return new_frames

    def add_decision(
        self,
        decision: str,
        note: str = '',
        present_artifacts: List[str] = [],
        absent_artifacts: List[str] = [],
    ):
        if decision.lower() in ['usable', 'u']:
            decision = 'U'
        elif decision.lower() in ['unusable', 'un']:
            decision = 'UN'
        elif decision.lower() in ['questionable', 'q?']:
            decision = 'Q?'
        elif decision.lower() in ['usable-extra', 'usable extra', 'ue']:
            decision = 'UE'
        else:
            raise Exception(
                'Unknown decision string. Acceptable values include [usable, unusable, questionable, usable-extra].'
            )
        artifact_options = self.experiment.project.MIQA.artifact_options
        if any(art not in artifact_options for art in present_artifacts):
            raise Exception(
                f'Unknown artifact found in present artifacts. Acceptable artifact values are {artifact_options}.'
            )
        if any(art not in artifact_options for art in absent_artifacts):
            raise Exception(
                f'Unknown artifact found in absent artifacts. Acceptable artifact values are {artifact_options}.'
            )
        if (
            decision != 'U'
            and len(note) < 1
            and len(present_artifacts) < 1
            and len(absent_artifacts) < 1
        ):
            raise Exception(
                'Decisions other than "usable" must have some explanatory note or selection of present artifacts.'
            )
        self.experiment.project.MIQA.make_request(
            f'experiments/{self.experiment.id}/lock', POST=True
        )
        response = self.experiment.project.MIQA.make_request(
            'scan-decisions',
            POST=True,
            body={
                "decision": decision,
                "note": note,
                "scan": self.id,
                "artifacts": {
                    "present": present_artifacts,
                    "absent": absent_artifacts,
                },
            },
        )
        self.experiment.project.MIQA.make_request(
            f'experiments/{self.experiment.id}/lock', DELETE=True
        )
        new_scan_decision = ScanDecision(**dict(response, scan=self))
        self.decisions.append(new_scan_decision)
        return new_scan_decision

    def print_all_objects(self, indent=0):
        print(" " * indent, str(self))
        print(" " * indent, "|Decisions:  ", self.decisions)
        print(" " * indent, "|Frames:  ", self.frames)

    def __repr__(self):
        return f"Scan {self.name}"
