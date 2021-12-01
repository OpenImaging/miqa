import json
from pathlib import Path

from celery import shared_task
import pandas

from miqa.core.conversion.import_export_csvs import (
    IMPORT_CSV_COLUMNS,
    import_dataframe_to_dict,
    validate_import_dict,
)
from miqa.core.conversion.nifti_to_zarr_ngff import nifti_to_zarr_ngff
from miqa.core.models import Evaluation, Experiment, Frame, Project, Scan
from miqa.learning.evaluation_models import available_evaluation_models
from miqa.learning.nn_inference import evaluate_many


@shared_task
def evaluate_data(frame_ids, project_id):
    frames = Frame.objects.filter(pk__in=frame_ids)
    project = Project.objects.get(id=project_id)

    model_to_frames_map = {}
    for frame in frames:
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


def import_data(user_id, project_id):
    project = Project.objects.get(id=project_id)

    if project.import_path.endswith('.csv'):
        import_dict = import_dataframe_to_dict(pandas.read_csv(project.import_path))
    elif project.import_path.endswith('.json'):
        import_dict = json.load(open(project.import_path))
    else:
        raise ValueError(f'Invalid import file {project.import_path}.')

    import_dict = validate_import_dict(import_dict, project)
    perform_import.delay(import_dict, project_id)


@shared_task
def perform_import(import_dict, project_id):
    new_projects = []
    new_experiments = []
    new_scans = []
    new_frames = []

    # comment out the below line and remove project_id param
    # when multi-project imports are supported
    project = Project.objects.get(id=project_id)

    for project_name, project_data in import_dict['projects'].items():
        if project.global_import_export:
            # A global import uses the project name column to determine which project to import to
            project_object = Project.objects.get(name=project_name)
        else:
            # A normal import ignores the project name column
            project_object = project

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

    evaluate_data.delay([frame.id for frame in new_frames], project.id)


def export_data(project_id):
    project = Project.objects.get(id=project_id)
    parent_location = Path(project.export_path).parent
    if not parent_location.exists():
        raise ValueError(f'No such location {parent_location} to create export file.')

    # In the event of a global export, we only want to export the projects listed in the import
    # file. Read the import file now and extract the project names.
    if project.import_path.endswith('.csv'):
        import_dict = import_dataframe_to_dict(pandas.read_csv(project.import_path))
    elif project.import_path.endswith('.json'):
        import_dict = json.load(open(project.import_path))
    else:
        raise ValueError(f'Invalid import file {project.import_path}.')

    import_dict = validate_import_dict(import_dict, project)
    project_names = import_dict['projects'].keys()

    perform_export.delay(project_id, project_names)


@shared_task
def perform_export(project_id, project_names):
    project = Project.objects.get(id=project_id)
    data = []

    if project.global_import_export:
        # A global export should export all projects listed in the import file
        projects = [Project.objects.get(name=project_name) for project_name in project_names]
    else:
        # A normal export should only export the current project
        projects = [project]

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
    export_df.to_csv(project_object.export_path, index=False)
