from io import BytesIO, StringIO
import json
from pathlib import Path
import tempfile
from typing import Dict, List, Optional

import boto3
from botocore import UNSIGNED
from botocore.client import Config
from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
import pandas
from rest_framework.exceptions import APIException

from miqa.core.conversion.import_export_csvs import (
    IMPORT_CSV_COLUMNS,
    import_dataframe_to_dict,
    validate_import_dict,
)
from miqa.core.conversion.nifti_to_zarr_ngff import nifti_to_zarr_ngff
from miqa.core.models import (
    Evaluation,
    Experiment,
    Frame,
    GlobalSettings,
    Project,
    Scan,
    ScanDecision,
)
from miqa.core.models.frame import StorageMode
from miqa.core.models.scan_decision import default_identified_artifacts


def _get_s3_client(public: bool):
    if public:
        return boto3.client('s3', config=Config(signature_version=UNSIGNED))
    else:
        return boto3.client('s3')


def _download_from_s3(path: str, public: bool) -> bytes:
    bucket, key = path.strip()[5:].split('/', maxsplit=1)
    client = _get_s3_client(public)
    buf = BytesIO()
    client.download_fileobj(bucket, key, buf)
    return buf.getvalue()


@shared_task
def evaluate_frame_content(frame_id):
    from miqa.learning.evaluation_models import available_evaluation_models
    from miqa.learning.nn_inference import evaluate1

    frame = Frame.objects.get(id=frame_id)
    eval_model_name = frame.scan.experiment.project.evaluation_models[[frame.scan.scan_type][0]]
    s3_public = frame.scan.experiment.project.s3_public
    eval_model = available_evaluation_models[eval_model_name].load()
    with tempfile.TemporaryDirectory() as tmpdirname:
        # need to send a local version to NN
        if frame.storage_mode == StorageMode.LOCAL_PATH:
            dest = Path(frame.raw_path)
        else:
            dest = Path(tmpdirname, frame.content.name.split('/')[-1])
            with open(dest, 'wb') as fd:
                if frame.storage_mode == StorageMode.S3_PATH:
                    fd.write(_download_from_s3(frame.content.url, s3_public))
                else:
                    fd.write(frame.content.open().read())
        result = evaluate1(eval_model, dest)

        Evaluation.objects.create(
            frame=frame,
            evaluation_model=eval_model_name,
            results=result,
        )


@shared_task
def evaluate_data(frames_by_project):
    from miqa.learning.evaluation_models import available_evaluation_models
    from miqa.learning.nn_inference import evaluate_many

    model_to_frames_map = {}
    for project_id, frame_ids in frames_by_project.items():
        project = Project.objects.get(id=project_id)
        for frame_id in frame_ids:
            frame = Frame.objects.get(id=frame_id)
            file_path = frame.raw_path
            if frame.storage_mode == StorageMode.S3_PATH or Path(file_path).exists():
                eval_model_name = project.evaluation_models[[frame.scan.scan_type][0]]
                if eval_model_name not in model_to_frames_map:
                    model_to_frames_map[eval_model_name] = []
                model_to_frames_map[eval_model_name].append(frame)

    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)
        for model_name, frame_set in model_to_frames_map.items():
            current_model = available_evaluation_models[model_name].load()
            file_paths = {frame: frame.raw_path for frame in frame_set}
            for frame, file_path in file_paths.items():
                if frame.storage_mode == StorageMode.S3_PATH:
                    s3_public = frame.scan.experiment.project.s3_public
                    dest = tmpdir / frame.path.name
                    with open(dest, 'wb') as fd:
                        fd.write(_download_from_s3(file_path, s3_public))
                    file_paths[frame] = dest
            results = evaluate_many(current_model, list(file_paths.values()))

            Evaluation.objects.bulk_create(
                [
                    Evaluation(
                        frame=frame,
                        evaluation_model=model_name,
                        results=results[file_paths[frame]],
                    )
                    for frame in frame_set
                ]
            )


def import_data(project_id: Optional[str]):
    if project_id is None:
        project = None
        import_path = GlobalSettings.load().import_path
        s3_public = False  # TODO we don't support this for global imports yet
    else:
        project = Project.objects.get(id=project_id)
        import_path = project.import_path
        s3_public = project.s3_public

    try:
        if import_path.endswith('.csv'):
            if import_path.startswith('s3://'):
                buf = _download_from_s3(import_path, s3_public).decode('utf-8')
            else:
                with open(import_path) as fd:
                    buf = fd.read()
            import_dict = import_dataframe_to_dict(pandas.read_csv(StringIO(buf)))
        elif import_path.endswith('.json'):
            if import_path.startswith('s3://'):
                import_dict = json.loads(_download_from_s3(import_path, s3_public))
            else:
                with open(import_path) as fd:
                    import_dict = json.load(fd)
        else:
            raise APIException(f'Invalid import file {import_path}. Must be CSV or JSON.')
    except (FileNotFoundError, boto3.exceptions.Boto3Error):
        raise APIException(f'Could not locate import file at {import_path}.')

    import_dict, not_found_errors = validate_import_dict(import_dict, project)
    perform_import.delay(import_dict, project_id)
    return not_found_errors


@shared_task
def perform_import(import_dict, project_id: Optional[str]):
    new_projects: List[Project] = []
    new_experiments: List[Experiment] = []
    new_scans: List[Scan] = []
    new_frames: List[Frame] = []
    new_scan_decisions: List[ScanDecision] = []

    for project_name, project_data in import_dict['projects'].items():
        if project_id is None:
            # A global import uses the project name column to determine which project to import to
            project_object = Project.objects.get(name=project_name)
        else:
            # A normal import ignores the project name column
            project_object = Project.objects.get(id=project_id)

        # delete old imports of these projects
        Experiment.objects.filter(
            project=project_object
        ).delete()  # cascades to scans -> frames, scan_notes

        for experiment_name, experiment_data in project_data['experiments'].items():
            experiment_object = Experiment(name=experiment_name, project=project_object)
            new_experiments.append(experiment_object)

            for scan_name, scan_data in experiment_data['scans'].items():
                subject_id = scan_data.get('subject_id', None)
                session_id = scan_data.get('session_id', None)
                scan_link = scan_data.get('scan_link', None)
                scan_object = Scan(
                    name=scan_name,
                    scan_type=scan_data['type'],
                    experiment=experiment_object,
                    subject_id=subject_id,
                    session_id=session_id,
                    scan_link=scan_link,
                )
                if 'last_decision' in scan_data:
                    last_decision_dict = scan_data['last_decision']
                    if last_decision_dict:
                        try:
                            creator = User.objects.get(email=last_decision_dict['creator'])
                        except User.DoesNotExist:
                            creator = None
                        note = ''
                        created = timezone.now()
                        location = {}
                        if last_decision_dict['note']:
                            note = last_decision_dict['note'].replace(';', ',')
                        if last_decision_dict['created']:
                            created = last_decision_dict['created']
                        if last_decision_dict['location']:
                            slices = [
                                axis.split('=')[1]
                                for axis in last_decision_dict['location'].split(';')
                            ]
                            location = {
                                'i': slices[0],
                                'j': slices[1],
                                'k': slices[2],
                            }
                        last_decision = ScanDecision(
                            decision=last_decision_dict['decision'],
                            creator=creator,
                            created=created,
                            note=note,
                            user_identified_artifacts={
                                artifact_name: (
                                    1
                                    if last_decision_dict['user_identified_artifacts']
                                    and artifact_name
                                    in last_decision_dict['user_identified_artifacts']
                                    else 0
                                )
                                for artifact_name in default_identified_artifacts().keys()
                            },
                            location=location,
                            scan=scan_object,
                        )
                        new_scan_decisions.append(last_decision)
                new_scans.append(scan_object)
                for frame_number, frame_data in scan_data['frames'].items():

                    frame_object = Frame(
                        frame_number=frame_number,
                        raw_path=frame_data['file_location'],
                        scan=scan_object,
                    )
                    new_frames.append(frame_object)
                    if settings.ZARR_SUPPORT and Path(frame_object.raw_path).exists():
                        nifti_to_zarr_ngff.delay(frame_data['file_location'])

    Project.objects.bulk_create(new_projects)
    Experiment.objects.bulk_create(new_experiments)
    Scan.objects.bulk_create(new_scans)
    ScanDecision.objects.bulk_create(new_scan_decisions)
    Frame.objects.bulk_create(new_frames)

    # must use str, not UUID, to get sent to celery task properly
    frames_by_project: Dict[str, List[str]] = {}
    for frame in new_frames:
        project_id = str(frame.scan.experiment.project.id)
        if project_id not in frames_by_project:
            frames_by_project[project_id] = []
        frames_by_project[project_id].append(str(frame.id))
    evaluate_data.delay(frames_by_project)


def export_data(project_id: Optional[str]):
    if not project_id:
        export_path = GlobalSettings.load().export_path
    else:
        project = Project.objects.get(id=project_id)
        export_path = project.export_path
    parent_location = Path(export_path).parent
    if not parent_location.exists():
        raise APIException(f'No such location {parent_location} to create export file.')

    return perform_export(project_id)


@shared_task
def perform_export(project_id: Optional[str]):
    data = []
    export_warnings = []

    if project_id is None:
        # A global export should export all projects
        projects = list(Project.objects.all())
        export_path = GlobalSettings.load().export_path
    else:
        # A normal export should only export the current project
        project = Project.objects.get(id=project_id)
        projects = [project]
        export_path = project.export_path

    for project_object in projects:
        for frame_object in Frame.objects.filter(scan__experiment__project=project_object):
            if frame_object.storage_mode == StorageMode.LOCAL_PATH:
                row_data = [
                    project_object.name,
                    frame_object.scan.experiment.name,
                    frame_object.scan.name,
                    frame_object.scan.scan_type,
                    frame_object.frame_number,
                    frame_object.raw_path,
                    frame_object.scan.subject_id,
                    frame_object.scan.session_id,
                    frame_object.scan.scan_link,
                ]

                # if a last decision exists for the scan, encode that decision on this row;
                # for example, "... U, rev@miqa.dev, note; without; commas, artifact_1;artifact_2
                last_decision = frame_object.scan.decisions.order_by('created').last()
                if last_decision:
                    location = ''
                    if last_decision.location:
                        location = (
                            f'i={last_decision.location["i"]};'
                            f'j={last_decision.location["j"]};'
                            f'k={last_decision.location["k"]}'
                        )
                    artifacts = last_decision.user_identified_artifacts.items()
                    creator = ''
                    if last_decision.creator:
                        creator = last_decision.creator.email
                    row_data += [
                        last_decision.decision,
                        creator,
                        last_decision.note.replace(',', ';'),
                        last_decision.created,
                        ';'.join([artifact for artifact, value in artifacts if value == 1]),
                        location,
                    ]
                data.append(row_data)
            else:
                export_warnings.append(
                    f'{frame_object.scan.name} not exported; this scan was uploaded, not imported.'
                )
    export_df = pandas.DataFrame(data, columns=IMPORT_CSV_COLUMNS)
    export_df.to_csv(export_path, index=False)
    return export_warnings
