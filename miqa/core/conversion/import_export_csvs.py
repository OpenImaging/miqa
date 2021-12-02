from pathlib import Path

from schema import And, Schema, SchemaError, Use

from miqa.core.models import Project

IMPORT_CSV_COLUMNS = [
    'project_name',
    'experiment_name',
    'scan_name',
    'scan_type',
    'frame_number',
    'file_location',
]


def validate_file_locations(input_dict, project):
    if not isinstance(input_dict, dict):
        return input_dict
    for key, value in input_dict.items():
        if key == 'file_location':
            raw_path = Path(value)
            if not raw_path.is_absolute():
                # not an absolute file path; refer to project import csv location
                raw_path = Path(project.import_path).parent.parent / raw_path
                # TODO: add support for interpreting URIs not on host machine
            if not raw_path.exists():
                raise ValueError(f'Could not locate file "{raw_path}".')
            input_dict[key] = str(raw_path)
        else:
            input_dict[key] = validate_file_locations(value, project)
    return input_dict


def validate_import_dict(import_dict, project: Project):
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
    try:
        import_schema.validate(import_dict)
        import_dict = validate_file_locations(import_dict, project)
    except SchemaError:
        raise ValueError(f'Invalid format of import file {project.import_path}')
    if project.global_import_export:
        for project_name in import_dict['projects']:
            if not Project.objects.filter(name=project_name).exists():
                raise ValueError(f'Project {project_name} does not exist')
    return import_dict


def import_dataframe_to_dict(df):
    if list(df.columns) != IMPORT_CSV_COLUMNS:
        raise ValueError(f'Import file has invalid columns. Expected {IMPORT_CSV_COLUMNS}')
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
