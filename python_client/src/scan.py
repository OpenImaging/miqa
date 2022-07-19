from typing import List
import requests
from s3_file_field_client import S3FileFieldClient

from .decision import ScanDecision
from .frame import Frame
from .exception import MIQAAPIError


class Scan:
    """
    Attributes:
      id, name, experiment, decisions, frames,
      scan_type, suject_id, session_id, scan_link,
    Functions:
      add_frames_from_paths, add_decision
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

    def _upload_file(self, file_path: str, field_id: str):
        sess = requests.Session()
        sess.headers.update(**self.experiment.project.MIQA.headers)
        s3ff = S3FileFieldClient(f'{self.experiment.project.MIQA.url}/s3-upload/', sess)
        with open(file_path, 'rb') as file_stream:
            return s3ff.upload_file(
                file_stream,
                file_path.split('/')[-1],
                field_id,
            )

    def add_frames_from_paths(self, *paths: List[str]):
        new_frames = []
        for index, path in enumerate(paths):
            field_value = self._upload_file(
                path,
                'core.Frame.content',
            )
            api_path = 'frames'
            response = requests.post(
                f"{self.experiment.project.MIQA.url}/{api_path}",
                headers=self.experiment.project.MIQA.headers,
                json={
                    'content': field_value,
                    'filename': path.split('/')[-1],
                    'scan': self.id,
                    'frame_number': index,
                },
            )
            response.raise_for_status()
            new_frame = Frame(**dict(response.json(), scan=self))
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
            raise MIQAAPIError(
                'Unknown decision string. Acceptable values include [usable, unusable, questionable, usable-extra].'
            )
        artifact_options = self.experiment.project.MIQA.artifact_options
        if any(art not in artifact_options for art in present_artifacts):
            raise MIQAAPIError(
                f'Unknown artifact found in present artifacts. Acceptable artifact values are {artifact_options}.'
            )
        if any(art not in artifact_options for art in absent_artifacts):
            raise MIQAAPIError(
                f'Unknown artifact found in absent artifacts. Acceptable artifact values are {artifact_options}.'
            )
        if (
            decision != 'U'
            and len(note) < 1
            and len(present_artifacts) < 1
            and len(absent_artifacts) < 1
        ):
            raise MIQAAPIError(
                'Decisions other than "usable" must have some explanatory note or selection of present artifacts.'
            )

        api_path = f'experiments/{self.experiment.id}/lock'
        response = requests.post(
            f"{self.experiment.project.MIQA.url}/{api_path}",
            headers=self.experiment.project.MIQA.headers,
        )
        response.raise_for_status()

        api_path = 'scan-decisions'
        response = requests.post(
            f"{self.experiment.project.MIQA.url}/{api_path}",
            headers=self.experiment.project.MIQA.headers,
            json={
                "decision": decision,
                "note": note,
                "scan": self.id,
                "artifacts": {
                    "present": present_artifacts,
                    "absent": absent_artifacts,
                },
            },
        )
        response.raise_for_status()
        new_scan_decision = ScanDecision(**dict(response.json(), scan=self))

        api_path = f'experiments/{self.experiment.id}/lock'
        response = requests.delete(
            f"{self.experiment.project.MIQA.url}/{api_path}",
            headers=self.experiment.project.MIQA.headers,
        )
        response.raise_for_status()

        self.decisions.append(new_scan_decision)
        return new_scan_decision

    def print_all_objects(self, indent=0):
        print(" " * indent, str(self))
        print(" " * indent, "|Decisions:  ", self.decisions)
        print(" " * indent, "|Frames:  ", self.frames)

    def __repr__(self):
        return f"Scan {self.name}"
