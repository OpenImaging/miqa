import json
from pathlib import Path

from celery import shared_task
from jsonschema.exceptions import ValidationError
import pandas

from miqa.core.conversion.csv_to_json import find_common_prefix
from miqa.core.conversion.json_to_csv import jsonObjectToCsvContent
from miqa.core.models import Decision, Evaluation, Experiment, Image, Project, Scan
from miqa.learning.evaluation_models import available_evaluation_models
from miqa.learning.nn_inference import evaluate_many

# from django.contrib.auth.models import User


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

    new_projects = []
    new_experiments = []
    new_scans = []
    new_frames = []

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
        if list(df.columns) != expected_columns:
            raise ValidationError(
                f'Import file has invalid columns. Expected {str(expected_columns)}'
            )

        # TODO: put this back for support of multiple projects in one import
        # these_projects = {
        #     project_name: Project(name=project_name, creator=user)
        #     for project_name in df['project_id'].unique()
        # })
        # new_projects.extend([project for _name, project in these_projects.items()])
        # for project_name, project_object in new_projects[0].items():
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
            new_experiments.extend([experiment for _name, experiment in these_experiments.items()])
            for experiment_name, experiment_object in these_experiments.items():
                these_scans = {
                    scan_name: Scan(
                        name=scan_name, scan_type=scan_type, experiment=experiment_object
                    )
                    for scan_name, scan_type in df[
                        (df['experiment_id'] == experiment_name)
                        & (df['project_id'] == project_name)
                    ]
                    .groupby(['scan_id', 'scan_type'])
                    .groups
                }
                new_scans.extend([scan for _name, scan in these_scans.items()])
                for scan_name, scan_object in these_scans.items():
                    these_frames = {}
                    for row in df[
                        (df['scan_id'] == scan_name)
                        & (df['experiment_id'] == experiment_name)
                        & (df['project_id'] == project_name)
                    ].iterrows():
                        raw_path = row[1]['file_location']
                        if raw_path[0] != '/':
                            # not an absolute file path; refer to project import csv location
                            # TODO: add support for interpreting URIs not on host machine
                            raw_path = str(Path(project.import_path).parent.parent / raw_path)
                        these_frames[row[1]['frame_number']] = Image(
                            frame_number=int(row[1]['frame_number']),
                            scan=scan_object,
                            raw_path=raw_path,
                        )
                    new_frames.extend([frame for _name, frame in these_frames.items()])

        Project.objects.bulk_create(new_projects)
        Experiment.objects.bulk_create(new_experiments)
        Scan.objects.bulk_create(new_scans)
        Image.objects.bulk_create(new_frames)

        evaluate_data.delay([frame.id for frame in new_frames], project.id)

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
