# flake8: noqa N806

import argparse
import csv
import io
import json
import os
import sys


def find_common_prefix(p1, p2):
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


def csvContentToJsonObject(csvContent):
    csvReader = csv.DictReader(io.StringIO(csvContent))

    print('field names: {0}'.format(csvReader.fieldnames))

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
    site_set = set()
    for scan in scans_raw:
        common_path_prefix = find_common_prefix(common_path_prefix, scan['nifti_folder'])
        scan['scan_path'] = '_'.join([scan['scan_id'], scan['scan_type']])
        experiment_dict[scan['xnat_experiment_id']] = scan['experiment_note']

    print('common path prefix: {0}'.format(common_path_prefix))

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
            'imagePattern': r"^image[\d]*\.nii\.gz$",
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

    # Build output JSON object
    outputObject = {}
    outputObject['data_root'] = common_path_prefix
    outputObject['scans'] = scans
    outputObject['experiments'] = experiments
    outputObject['sites'] = [{'id': site} for site in site_set]

    return outputObject


def csvToJson(csvFilePath, jsonFilePath):
    print('Reading input csv from {0}'.format(csvFilePath))

    with open(csvFilePath) as fd:
        csvContent = fd.read()

    jsonObject = csvContentToJsonObject(csvContent)

    print('Writing output json to {0}'.format(jsonFilePath))

    with open(jsonFilePath, 'w') as fd:
        json.dump(jsonObject, fd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert CSV file to JSON format')
    parser.add_argument(
        'inputfile', type=str, help='Absolute system path to CSV file to be converted'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Absolute systemn path where JSON output should be '
        + 'written.  If not provided, the default is to write '
        + 'the output to the directory where the input file '
        + 'is located and replace the "csv" extension with "json".',
    )
    args = parser.parse_args()

    inputFilePath = args.inputfile

    if not os.path.isfile(inputFilePath):
        print(
            'Please absolute provide path to input CSV file, {0} is not valid'.format(inputFilePath)
        )
        sys.exit(1)

    outputFilePath = args.output

    if not outputFilePath:
        filePath = os.path.dirname(inputFilePath)
        fileName = os.path.basename(inputFilePath)
        nameWithoutExtension = fileName[: fileName.rindex('.')]
        outputFilePath = os.path.join(filePath, '{0}.json'.format(nameWithoutExtension))

    csvToJson(inputFilePath, outputFilePath)
