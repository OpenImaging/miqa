# flake8: noqa N806

import csv
import io
import json
import os
from typing import Set


def find_common_prefix(p1, p2):
    # TODO obliterate this function
    minStrLen = min(len(p1), len(p2))
    firstNotMatch = 0
    while firstNotMatch < minStrLen:
        if p1[firstNotMatch] != p2[firstNotMatch]:
            break

        firstNotMatch += 1

    # Maybe need to backtrack to the nearest separator if we landed in the middle of a
    # subdirectory name
    while firstNotMatch > 0 and p1[firstNotMatch - 1] != os.path.sep:
        firstNotMatch -= 1

    return p1[:firstNotMatch]


def csvContentToJsonObject(csvContent: str) -> dict:
    csvReader = csv.DictReader(io.StringIO(csvContent))

    print('field names: {0}'.format(csvReader.fieldnames))  # TODO remove

    # First just blindly put everything in
    scans_raw = []
    for row in csvReader:
        nextScan = {}
        for fieldName in csvReader.fieldnames:
            nextScan[fieldName] = row[fieldName]
        scans_raw.append(nextScan)

    # Gather commonalities
    common_path_prefix = scans_raw[0]['nifti_folder']
    experiment_dict = {}
    site_set: Set[str] = set()
    for scan in scans_raw:
        common_path_prefix = find_common_prefix(common_path_prefix, scan['nifti_folder'])
        scan['scan_path'] = '_'.join([scan['scan_id'], scan['scan_type']])
        experiment_dict[scan['xnat_experiment_id']] = scan['experiment_note']

    print('common path prefix: {0}'.format(common_path_prefix))  # TODO remove

    # Produce final scans
    scans = []

    for scan in scans_raw:
        nifti_folder = scan['nifti_folder']
        subdir = nifti_folder.split(common_path_prefix)[1]
        if 'site' in scan:
            site = scan['site']
        elif nifti_folder.startswith('/fs/storage/XNAT/archive/'):
            # Special case handling to match previous implementation
            splits = nifti_folder.split('/')
            site = splits[5].split('_')[0]
        else:
            site = subdir[: subdir.index('_')]
        site_set.add(site)
        scan_obj = {
            'id': scan['scan_id'],
            'type': scan['scan_type'],
            'note': scan['scan_note'],
            'experiment_id': scan['xnat_experiment_id'],
            'path': os.path.join(subdir, scan['scan_path']),
            'image_pattern': r"^image[\d]*\.nii\.gz$",
            'site_id': site,
        }
        if 'decision' in scan:
            scan_obj['decision'] = scan['decision']
        scans.append(scan_obj)

    # Build list of unique experiments
    experiments = []
    for exp_id, exp_note in experiment_dict.items():
        experiments.append(
            {
                'id': exp_id,
                'note': exp_note,
            }
        )

    return {
        'data_root': common_path_prefix,
        'scans': scans,
        'experiments': experiments,
        'sites': [{'name': site} for site in site_set],
    }


def csvToJson(csvFilePath, jsonFilePath):
    print('Reading input csv from {0}'.format(csvFilePath))

    with open(csvFilePath) as fd:
        csvContent = fd.read()

    jsonObject = csvContentToJsonObject(csvContent)

    print('Writing output json to {0}'.format(jsonFilePath))

    with open(jsonFilePath, 'w') as fd:
        json.dump(jsonObject, fd)
