import json
from pathlib import Path

from celery import shared_task
import pandas
from rest_framework.exceptions import APIException

from miqa.core.conversion.import_export_csvs import (
    IMPORT_CSV_COLUMNS,
    import_dataframe_to_dict,
    validate_import_dict,
)
from miqa.core.conversion.nifti_to_zarr_ngff import nifti_to_zarr_ngff
from miqa.core.models import Evaluation, Experiment, Frame, GlobalSettings, Project, Scan
from miqa.learning.evaluation_models import available_evaluation_models
from miqa.learning.nn_inference import evaluate_many


@shared_task
def evaluate_data(frames_by_project):
    model_to_frames_map = {}
    for project_id, frame_ids in frames_by_project.items():
        project = Project.objects.get(id=project_id)
        for frame_id in frame_ids:
            frame = Frame.objects.get(id=frame_id)
            eval_model_name = project.evaluation_models[[frame.scan.scan_type][0]]
            if eval_model_name not in model_to_frames_map:
                model_to_frames_map[eval_model_name] = []
            model_to_frames_map[eval_model_name].append(frame)

    for model_name, frame_set in model_to_frames_map.items():
        current_model = available_evaluation_models[model_name].load()
        results = evaluate_many(current_model, [str(frame.raw_path) for frame in frame_set])

        Evaluation.objects.bulk_create(
            [
                Evaluation(
                    frame=frame,
                    evaluation_model=model_name,
                    results=results[str(frame.raw_path)],
                )
                for frame in frame_set
            ]
        )


def import_data(project_id):
    if project_id == 'global':
        project = 'global'
        import_path = GlobalSettings.load().import_path
    else:
        project = Project.objects.get(id=project_id)
        import_path = project.import_path

    if import_path.endswith('.csv'):
        import_dict = import_dataframe_to_dict(pandas.read_csv(import_path))
    elif import_path.endswith('.json'):
        import_dict = json.load(open(import_path))
    else:
        raise APIException(f'Invalid import file {import_path}. Must be CSV or JSON.')

    import_dict = validate_import_dict(import_dict, project)
    perform_import.delay(import_dict, project_id)


@shared_task
def perform_import(import_dict, project_id):
    new_projects = []
    new_experiments = []
    new_scans = []
    new_frames = []

    for project_name, project_data in import_dict['projects'].items():
        if project_id == 'global':
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
                scan_object = Scan(
                    name=scan_name, scan_type=scan_data['type'], experiment=experiment_object
                )
                new_scans.append(scan_object)
                for frame_number, frame_data in scan_data['frames'].items():

                    frame_object = Frame(
                        frame_number=frame_number,
                        raw_path=frame_data['file_location'],
                        scan=scan_object,
                    )
                    new_frames.append(frame_object)
                    nifti_to_zarr_ngff.delay(frame_data['file_location'])

    Project.objects.bulk_create(new_projects)
    Experiment.objects.bulk_create(new_experiments)
    Scan.objects.bulk_create(new_scans)
    Frame.objects.bulk_create(new_frames)

    frames_by_project = {}
    for frame in new_frames:
        project_id = str(frame.scan.experiment.project.id)
        if project_id not in frames_by_project:
            frames_by_project[project_id] = []
        frames_by_project[project_id].append(str(frame.id))
    evaluate_data.delay(frames_by_project)


def export_data(project_id):
    if project_id == 'global':
        export_path = GlobalSettings.load().export_path
    else:
        project = Project.objects.get(id=project_id)
        export_path = project.export_path
    parent_location = Path(export_path).parent
    if not parent_location.exists():
        raise APIException(f'No such location {parent_location} to create export file.')

    perform_export.delay(project_id)


@shared_task
def perform_export(project_id):
    data = []

    if project_id == 'global':
        # A global export should export all projects
        projects = Project.objects.all()
        export_path = GlobalSettings.load().export_path
    else:
        # A normal export should only export the current project
        project = Project.objects.get(id=project_id)
        projects = [project]
        export_path = project.export_path

    for project_object in projects:
        for frame_object in Frame.objects.filter(scan__experiment__project=project_object):
            data.append(
                [
                    project_object.name,
                    frame_object.scan.experiment.name,
                    frame_object.scan.name,
                    frame_object.scan.scan_type,
                    frame_object.frame_number,
                    frame_object.raw_path,
                ]
            )
    export_df = pandas.DataFrame(data, columns=IMPORT_CSV_COLUMNS)
    export_df.to_csv(export_path, index=False)
