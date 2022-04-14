import csv
import io
from pathlib import Path


def generate_import_csv(sample_scans):
    output = io.StringIO()
    fieldnames = [
        'project_name',
        'experiment_name',
        'scan_name',
        'scan_type',
        'frame_number',
        'file_location',
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, dialect='unix')
    writer.writeheader()
    for scan_folder, scan_id, scan_type in sample_scans:
        # The project name is encoded somewhere in the path
        for potential_name in ['ohsu', 'ucsd']:
            if potential_name in scan_folder:
                project_name = potential_name
        writer.writerow(
            {
                'project_name': project_name,
                'experiment_name': f'{scan_id}_experiment',
                'scan_name': scan_id,
                'scan_type': scan_type,
                'frame_number': 0,
                'file_location': f'{scan_folder}/{scan_id}_{scan_type}/image.nii.gz',
            }
        )

    return output, writer


def generate_import_json(samples_dir: Path, sample_scans):
    projects = {}
    for scan_folder, scan_id, scan_type in sample_scans:
        # The project name is encoded somewhere in the path
        for potential_name in ['ohsu', 'ucsd']:
            if potential_name in scan_folder:
                project_name = potential_name
        experiment_name = f'{scan_id}_experiment'
        projects[project_name] = {
            'experiments': {
                experiment_name: {
                    'scans': {
                        scan_id: {
                            'type': scan_type,
                            'frames': {
                                0: {
                                    'file_location': str(
                                        Path(
                                            scan_folder,
                                            f'{scan_id}_{scan_type}',
                                            'image.nii.gz',
                                        )
                                    )
                                }
                            },
                        }
                    }
                }
            }
        }
    return {'projects': projects}
