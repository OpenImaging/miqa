# flake8: noqa N806

import argparse
import csv
import io
import json
import os


def jsonObjectToCsvContent(jsonObject):
    experiments = {}
    for exper in jsonObject['experiments']:
        experiments[exper['id']] = exper['note']

    scans = jsonObject['scans']
    dataRoot = jsonObject['data_root']

    rowList = []

    optionalFields = {'decision': True, 'IQMs': True, 'scan_note': True, 'good_prob': True}

    for scan in scans:
        expId = scan['experiment_id']

        scanPath = scan['path']
        pathComps = scanPath.split(os.path.sep)
        firstComps = pathComps[:-1]
        lastComp = pathComps[-1]

        try:
            splitIdx = lastComp.index('_')
        except ValueError as valErr:
            print('ERROR: the following scan cannot be converted to CSV row')
            print(scan)
            continue

        scanId = scan['id']
        parsedScanId = lastComp[:splitIdx]
        if scanId != parsedScanId:
            print('ERROR: expected scan id {0}, but found {1} instead'.format(scanId, parsedScanId))
            print(scan)
            continue

        scanType = scan['type']
        parsedScanType = lastComp[splitIdx + 1 :]
        if scanType != parsedScanType:
            print(
                'ERROR: expected scan type {0}, but found {1} instead'.format(
                    scanType, parsedScanType
                )
            )
            print(scan)
            continue

        niftiFolder = os.path.join(dataRoot, *firstComps)

        nextRow = {
            'xnat_experiment_id': expId,
            'nifti_folder': niftiFolder,
            'scan_id': scanId,
            'scan_type': scanType,
            'experiment_note': experiments[expId],
        }

        if 'decision' in scan:
            nextRow['decision'] = scan['decision']
        else:
            optionalFields['decision'] = False

        if 'note' in scan:
            nextRow['scan_note'] = scan['note']
        else:
            optionalFields['note'] = False

        if 'iqms' in scan:
            nextRow['IQMs'] = scan['iqms']
        else:
            optionalFields['IQMs'] = False

        if 'good_prob' in scan:
            nextRow['good_prob'] = scan['good_prob']
        else:
            optionalFields['good_prob'] = False

        rowList.append(nextRow)

    fieldNames = ['xnat_experiment_id', 'nifti_folder', 'scan_id', 'scan_type', 'experiment_note']

    fieldNames.extend([key for (key, val) in optionalFields.items() if val])

    # Now we have the dictionary representing the data and the field names, we
    # can write them to the stringio object
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldNames, dialect='unix')
    writer.writeheader()
    for row in rowList:
        writer.writerow(row)

    return output


def jsonToCsv(jsonFilePath, csvFilePath):
    print('Reading input json from {0}'.format(jsonFilePath))

    with open(jsonFilePath) as jsonFile:
        jsonObject = json.load(jsonFile)

    csvContent = jsonObjectToCsvContent(jsonObject)

    print('Writing output csv to {0}'.format(csvFilePath))

    with open(csvFilePath, 'w') as fd:
        fd.write(csvContent.getvalue())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert JSON file to original CSV format')
    parser.add_argument(
        'inputfile', type=str, help='Absolute system path to JSON file to be converted'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Absolute systemn path where CSV output should be '
        + 'written.  If not provided, the default is to write '
        + 'the output to the directory where the input file '
        + 'is located and replace the "json" extension with "csv".',
    )
    args = parser.parse_args()

    inputFilePath = args.inputfile

    if not os.path.isfile(inputFilePath):
        print(
            'Please absolute provide path to input JSON file, {0} is not valid'.format(
                inputFilePath
            )
        )
        sys.exit(1)

    outputFilePath = args.output

    if not outputFilePath:
        filePath = os.path.dirname(inputFilePath)
        fileName = os.path.basename(inputFilePath)
        nameWithoutExtension = fileName[: fileName.rindex('.')]
        outputFilePath = os.path.join(filePath, '{0}.csv'.format(nameWithoutExtension))

    jsonToCsv(inputFilePath, outputFilePath)
