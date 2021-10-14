import json
from pathlib import Path

from celery import shared_task
import pandas

from miqa.core.conversion.import_export_csvs import (
    IMPORT_CSV_COLUMNS,
    import_dataframe_to_dict,
    validate_import_dict,
)
from miqa.core.models import Evaluation, Experiment, Image, Project, Scan
from miqa.core.conversion.nifti_to_zarr_ngff import nifti_to_zarr_ngff
from miqa.learning.evaluation_models import available_evaluation_models
from miqa.learning.nn_inference import evaluate_many


@shared_task
def evaluate_data(image_ids, project_id):
    images = Image.objects.filter(pk__in=image_ids)
    project = Project.objects.get(id=project_id)

    model_to_images_map = {}
    for image in images:
        eval_model_name = project.evaluation_models[[image.scan.scan_type][0]]
        if eval_model_name not in model_to_images_map:
            model_to_images_map[eval_model_name] = []
        model_to_images_map[eval_model_name].append(image)

    for model_name, image_set in model_to_images_map.items():
        current_model = available_evaluation_models[model_name].load()
        results = evaluate_many(current_model, [str(image.raw_path) for image in image_set])

        Evaluation.objects.bulk_create(
            [
                Evaluation(
                    image=image,
                    evaluation_model=model_name,
                    results=results[str(image.raw_path)],
                )
                for image in image_set
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

    for _project_name, project_data in import_dict['projects'].items():
        # Switch these lines to support multi-project imports
        # project_object = Project(name=_project_name)
        # new_projects.append(project_object)
        project_object = project

        # delete old imports of these projects
        Experiment.objects.filter(
            project=project_object
        ).delete()  # cascades to scans -> images, scan_notes

        for experiment_name, experiment_data in project_data['experiments'].items():
            experiment_object = Experiment(name=experiment_name, project=project_object)
            new_experiments.append(experiment_object)

            for scan_name, scan_data in experiment_data['scans'].items():
                scan_object = Scan(
                    name=scan_name, scan_type=scan_data['type'], experiment=experiment_object
                )
                new_scans.append(scan_object)
                for frame_number, frame_data in scan_data['frames'].items():

                    frame_object = Image(
                        frame_number=frame_number,
                        raw_path=frame_data['file_location'],
                        scan=scan_object,
                    )
                    new_frames.append(frame_object)
                    nifti_to_zarr_ngff.delay(frame_data['file_location'])

    Project.objects.bulk_create(new_projects)
    Experiment.objects.bulk_create(new_experiments)
    Scan.objects.bulk_create(new_scans)
    Image.objects.bulk_create(new_frames)

    evaluate_data.delay([frame.id for frame in new_frames], project.id)


def export_data(project_id):
    project_object = Project.objects.get(id=project_id)
    parent_location = Path(project_object.export_path).parent
    if not parent_location.exists():
        raise ValueError(f'No such location {parent_location} to create export file.')
    perform_export.delay(project_id)


@shared_task
def perform_export(project_id):
    project_object = Project.objects.get(id=project_id)
    data = []

    for frame_object in Image.objects.filter(scan__experiment__project=project_object):
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
