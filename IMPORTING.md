## Importing / Exporting Data
In MIQA, each Project has settings that allow you to specify file paths to an import file and an export file. The import file is how you ingest data into the project and the export file will write project contents into an ingestable format. These files must be either CSV or JSON. The file paths you specify should be absolute and visible to wherever your server is running.

If you are using a production instance with native deployment, be sure that these paths are on the same machine and readable by the user that runs the Django server.

If you are using a development instance with the `docker-compose` setup, you should specify an environment variable `SAMPLES_DIR` as a directory containing any absolute paths you wish to access from the server. The `docker-compose` configuration will mount this directory as visible to the server.

## Format of the Import File
### Import CSV
If your import file is a CSV, it should contain a header row and any following rows will represent Frame objects in the Project. Each Frame object in the Project represents a single image file, and each Frame is organized into an Experiment, then into a Scan. The header row defines these columns:

```
project_name, experiment_name, scan_name, scan_type, frame_number, file_location
```
- Project name: The name of the Project you create in MIQA that points to this file as its import file
- Experiment name: The name you would like to apply to the experiment to which this Frame belongs
- Scan name: The name you would like to apply to the scan to which this Frame belongs
- Scan type: Can be one of "T1", "T2", "FMRI", "MRA", "PD", "DTI", "DWI", or any of the ncanda-specific scan types (see miqa.core.models.scan for more)
- Frame number: An integer to determine the order of Frames in a Scan. If only one Frame exists, enter 0 for this value.
- File location: The file path of the image file (.nii.gz, .nii, .mgz, .nrrd). This can be an absolute path (with the same restrictions as above for the import file) or a relative path to the parent of the import file itself.

### Import JSON
If your import file is a JSON, the representation for Frames is nested into the representations for Scans within Experiments within your project. Below is an example of an import JSON:

```json
"projects": {
   "My Project" :{
      "experiments": {
         "Experiment One": {
            "scans": {
               "Scan One": {
                  "type": "T1",
                  "frames": {
                    0: "path/to/frame1.nii.gz",
                    1: "path/to/frame2.nii.gz",
                    2: "path/to/frame3.nii.gz"
                  }
               },
               "Scan Two": {
                  "type": "T1",
                  "frames": {
                    0: "path/to/frame4.nii.gz"
                  }
               }
            }
         },
         "Experiment Two": {
            "scans": {
               "Scan Three": {
                  "type": "T1",
                  "frames": {
                    0: "path/to/frame5.nii.gz"
                  }
               }
            }
         }
      }
   }
}
```

## Old CSV format
The original Girder 3 MIQA server used a different CSV format with different column names. If you have CSV files in the old format, they can be converted using the `convert_miqa_import_csv_format.py` script:
```bash
python dev/convert_miqa_import_csv_format.py old_import.csv another_import.csv
```
This will create two new files `new_import.csv` and `new_another_import.csv` containing the same data in the new CSV format.