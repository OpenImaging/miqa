import json
import pandas
from pathlib import Path

from celery import shared_task
from jsonschema.exceptions import ValidationError

# from django.contrib.auth.models import User

from miqa.core.conversion.csv_to_json import find_common_prefix
from miqa.core.conversion.json_to_csv import jsonObjectToCsvContent
from miqa.core.models import (
    Decision,
    Evaluation,
    Experiment,
    Image,
    Project,
    Scan,
)
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


@shared_task
def import_data(user_id, project_id):
    # user = User.objects.get(id=user_id)
    project = Project.objects.get(id=project_id)

    all_projects = []
    all_experiments = []
    all_scans = []
    all_frames = []

    if project.import_path.endswith('.csv'):
        df = pandas.read_csv(project.import_path)
        expected_columns = [
            'project_id',
            'experiment_id',
            'scan_id',
            'scan_type',
            'frame_number',
            'file_location',
        ]
        if len(df.columns) != len(expected_columns) or any(df.columns != expected_columns):
            raise ValidationError(
                f'Import file has invalid columns. Expected {str(expected_columns)}'
            )

        # TODO: put this back for support of multiple projects in one import
        # all_projects.append({
        #     project_name: Project(name=project_name, creator=user)
        #     for project_name in df['project_id'].unique()
        # })
        # for project_name, project_object in all_projects[0].items():
        for project_name, project_object in [(df['project_id'].mode()[0], project)]:

            # delete old imports of these projects
            Experiment.objects.filter(
                project=project_object
            ).delete()  # cascades to scans -> images, scan_notes

            these_experiments = {
                experiment_name: Experiment(name=experiment_name, project=project_object)
                for experiment_name in df[df['project_id'] == project_name][
                    'experiment_id'
                ].unique()
            }
            all_experiments.append(these_experiments)
            for experiment_name, experiment_object in these_experiments.items():
                these_scans = {
                    scan_name: Scan(
                        name=scan_name, scan_type=scan_type, experiment=experiment_object
                    )
                    for scan_name, scan_type in df[df['experiment_id'] == experiment_name]
                    .groupby(['scan_id', 'scan_type'])
                    .groups
                }
                all_scans.append(these_scans)
                for scan_name, scan_object in these_scans.items():
                    these_frames = {}
                    for row in df[df['scan_id'] == scan_name].iterrows():
                        raw_path = row[1]['file_location']
                        if raw_path[0] != '/':
                            # not an absolute file path; refer to project import csv location
                            # TODO: add support for interpreting URIs not on host machine
                            raw_path = str(Path(project.import_path).parent.parent) + '/' + raw_path
                        these_frames[row[1]['frame_number']] = Image(
                            frame_number=int(row[1]['frame_number']),
                            scan=scan_object,
                            raw_path=raw_path,
                        )
                    all_frames.append(these_frames)

        for model, list_all in [
            (Project, all_projects),
            (Experiment, all_experiments),
            (Scan, all_scans),
            (Image, all_frames),
        ]:
            all_items = [item for subdict in list_all for item in subdict.values()]
            model.objects.bulk_create(all_items)
            if model == Image:
                # TODO: modify this to support multi-projects, too
                evaluate_data.delay([item.id for item in all_items], project.id)
                # evaluate_data([item.id for item in all_items], project.id)

    # TODO: re-write JSON parsing to be generalized like CSV parsing
    # elif project.import_path.endswith('.json'):
    #     pass
    else:
        raise ValidationError(f'Invalid import file {project.import_path}.')


@shared_task
def export_data(project_id):
    project = Project.objects.get(id=project_id)

    data_root = None
    experiments = []
    scans = []
    sites = set()

    for experiment in project.experiments.all():
        experiments.append(
            {
                'id': experiment.name,
                'note': experiment.note,
            }
        )
        for scan in experiment.scans.all():
            scan_root = None
            for image in scan.images.all():
                if data_root is None:
                    data_root = image.raw_path
                data_root = find_common_prefix(data_root, image.raw_path)

                if scan_root is None:
                    scan_root = image.raw_path
                scan_root = find_common_prefix(scan_root, image.raw_path)

            if scan_root is None:
                # There were no images in this scan, don't export it
                continue

            decision = scan.decisions.order_by('-created').first()
            if decision:
                decision = Decision.to_rating(decision.decision)
            else:
                decision = ''

            note = '\n'.join(
                [f'{note.initials}:{note.note}' for note in scan.notes.order_by('created').all()]
            )

            scans.append(
                {
                    'id': scan.scan_id,
                    'type': scan.scan_type,
                    'note': note,
                    'experiment_id': experiment.name,
                    'path': scan_root,
                    'image_pattern': r'^image[\d]*\.nii\.gz$',
                    'site_id': scan.site.name,
                    'decision': decision,
                }
            )
            sites.add(scan.site.name)

    # scan.path should omit the data_root prefix, so trim it off now
    for scan in scans:
        scan['path'] = scan['path'][len(data_root) :]

    json_content = {
        'data_root': data_root,
        'experiments': experiments,
        'scans': scans,
        'sites': [{'name': site} for site in sites],
    }

    if project.export_path.endswith('.csv'):
        with open(project.export_path, 'w') as csv_file:
            csv_content = jsonObjectToCsvContent(json_content)
            csv_file.write(csv_content.getvalue())
    else:
        # Assume JSON
        with open(project.export_path, 'w') as json_file:
            json_file.write(json.dumps(json_content, indent=4))
