from schema import And, Schema, SchemaError, Use

IMPORT_CSV_COLUMNS = [
    'project_name',
    'experiment_name',
    'scan_name',
    'scan_type',
    'frame_number',
    'file_location',
]


def validate_import_dict(import_dict):
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
        return True
    except SchemaError:
        return False


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
