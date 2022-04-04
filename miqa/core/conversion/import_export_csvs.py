from pathlib import Path
from typing import Optional as TypingOptional

from rest_framework.exceptions import APIException
from schema import And, Optional, Or, Schema, SchemaError, Use

from miqa.core.models import GlobalSettings, Project

# subjectid and sessionid are for compatibility with PREDICT and other BidS datasets
IMPORT_CSV_COLUMNS = [
    'project_name',
    'experiment_name',
    'scan_name',
    'scan_type',
    'frame_number',
    'file_location',
    'subject_id',
    'session_id',
    'scan_link',
    'last_decision',
    'last_decision_creator',
    'last_decision_note',
    'identified_artifacts',
    'location_of_interest',
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


def validate_import_dict(import_dict, project: TypingOptional[Project]):
    import_schema = Schema(
        {
            'projects': {
                And(Use(str)): {
                    'experiments': {
                        And(Use(str)): {
                            'scans': {
                                And(Use(str)): {
                                    'type': And(Use(str)),
                                    Optional('subject_id'): Or(str, None),
                                    Optional('session_id'): Or(str, None),
                                    Optional('scan_link'): Or(str, None),
                                    'frames': {And(Use(int)): {'file_location': And(str)}},
                                    Optional('last_decision'): Or(
                                        {
                                            'decision': And(str),
                                            'creator': Or(str, None),
                                            'note': Or(str, None),
                                            'user_identified_artifacts': Or(str, None),
                                            'location': Or(str, None),
                                        },
                                        None,
                                    ),
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
    df_columns = list(df.columns)
    # The columns after the first 6 are optional
    if df_columns != IMPORT_CSV_COLUMNS and (
        len(df_columns) < 6 or df_columns != IMPORT_CSV_COLUMNS[: len(df_columns)]
    ):
        raise APIException(f'Import file has invalid columns. Expected {IMPORT_CSV_COLUMNS}')
    ingest_dict = {'projects': {}}
    for project_name, project_df in df.groupby('project_name'):
        project_dict = {'experiments': {}}
        for experiment_name, experiment_df in project_df.groupby('experiment_name'):
            experiment_dict = {'scans': {}}
            for scan_name, scan_df in experiment_df.groupby('scan_name'):
                scan_dict = {
                    'type': scan_df['scan_type'].iloc[0],
                    'frames': {
                        row[1]['frame_number']: {'file_location': row[1]['file_location']}
                        for row in scan_df.iterrows()
                    },
                }
                if 'subject_id' in scan_df.columns:
                    scan_dict['subject_id'] = scan_df['subject_id'].iloc[0]
                if 'session_id' in scan_df.columns:
                    scan_dict['session_id'] = scan_df['session_id'].iloc[0]
                if 'scan_link' in scan_df.columns:
                    scan_dict['scan_link'] = scan_df['scan_link'].iloc[0]
                if (
                    'last_decision' in scan_df.columns
                    and str(scan_df['last_decision'].iloc[0]) != 'nan'
                ):
                    decision_dict = {
                        'decision': scan_df['last_decision'].iloc[0],
                        'creator': scan_df['last_decision_creator'].iloc[0],
                        'note': scan_df['last_decision_note'].iloc[0],
                        'user_identified_artifacts': scan_df['identified_artifacts'].iloc[0],
                        'location': scan_df['location_of_interest'].iloc[0],
                    }
                    decision_dict = {
                        k: (v if str(v) != 'nan' else None) for k, v in decision_dict.items()
                    }
                    scan_dict['last_decision'] = decision_dict
                else:
                    scan_dict['last_decision'] = None

                experiment_dict['scans'][scan_name] = scan_dict
            project_dict['experiments'][experiment_name] = experiment_dict
        ingest_dict['projects'][project_name] = project_dict
    return ingest_dict
