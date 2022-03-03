from pathlib import Path
from typing import Optional

from rest_framework.exceptions import APIException
from schema import And, Schema, SchemaError, Use

from miqa.core.models import GlobalSettings, Project

IMPORT_CSV_COLUMNS = [
    'project_name',
    'experiment_name',
    'scan_name',
    'scan_type',
    'frame_number',
    'file_location',
]


def validate_file_locations(input_dict, project, not_found_errors):
    if not isinstance(input_dict, dict):
        return input_dict, not_found_errors
    import_path = GlobalSettings.load().import_path if project is None else project.import_path
    for key, value in input_dict.items():
        if key == 'file_location':
            raw_path = Path(value)
            if not value.startswith('s3://'):
                if not raw_path.is_absolute():
                    # not an absolute file path; refer to project import csv location
                    raw_path = Path(import_path).parent.parent / raw_path
                if not raw_path.exists():
                    not_found_errors.append(f'File not found: {raw_path}')
            input_dict[key] = str(raw_path) if 's3://' not in value else value
        else:
            new_value, not_found_errors = validate_file_locations(value, project, not_found_errors)
            input_dict[key] = new_value
    return input_dict, not_found_errors


def validate_import_dict(import_dict, project: Optional[Project]):
    import_schema = Schema(
        {
            'projects': {
                And(Use(str)): {
                    'experiments': {
                        And(Use(str)): {
                            'scans': {
                                And(Use(str)): {
                                    'type': And(Use(str)),
                                    'frames': {And(Use(int)): {'file_location': And(Use(str))}},
                                }
                            }
                        }
                    }
                }
            }
        }
    )
    not_found_errors = []
    try:
        import_schema.validate(import_dict)
        import_dict, not_found_errors = validate_file_locations(
            import_dict, project, not_found_errors
        )
    except SchemaError:
        import_path = GlobalSettings.load().import_path if project is None else project.import_path
        raise APIException(f'Invalid format of import file {import_path}')
    if not project:
        for project_name in import_dict['projects']:
            if not Project.objects.filter(name=project_name).exists():
                raise APIException(f'Project {project_name} does not exist')
    return import_dict, not_found_errors


def import_dataframe_to_dict(df):
    if list(df.columns) != IMPORT_CSV_COLUMNS:
        raise APIException(f'Import file has invalid columns. Expected {IMPORT_CSV_COLUMNS}')
    return {
        'projects': {
            project_name: {
                'experiments': {
                    experiment_name: {
                        'scans': {
                            scan_name: {
                                'type': scan_df['scan_type'].mode()[0],
                                'frames': {
                                    row[1]['frame_number']: {
                                        'file_location': row[1]['file_location']
                                    }
                                    for row in scan_df.iterrows()
                                },
                            }
                            for scan_name, scan_df in experiment_df.groupby('scan_name')
                        }
                    }
                    for experiment_name, experiment_df in project_df.groupby('experiment_name')
                }
            }
            for project_name, project_df in df.groupby('project_name')
        }
    }
