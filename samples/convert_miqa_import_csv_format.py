import pandas
from pathlib import Path
import sys

for file_name in sys.argv[1:]:
    if not Path(file_name).exists():
        raise Exception(f"{file_name} does not exist.")
    if not file_name.endswith(".csv"):
        raise Exception(f"{file_name} is not a CSV file.")
    df = pandas.read_csv(file_name)
    expected_columns = [
        "xnat_experiment_id",
        "nifti_folder",
        "scan_id",
        "scan_type",
        "experiment_note",
        "decision",
        "scan_note",
    ]
    if len(df.columns) != len(expected_columns) or any(df.columns != expected_columns):
        raise Exception(
            f"{file_name} is not congruent with the old"
            f" MIQA import format. Expected columns {str(expected_columns)} but recieved {str(df.columns)}."
        )

    project_name = str(input("Enter a project name for these scans:\n"))
    print()
    new_rows = []
    for index, row in df.iterrows():
        new_rows.append(
            [
                project_name,
                row["xnat_experiment_id"],
                f"{row['xnat_experiment_id']}_{row['scan_type']}",
                row["scan_type"],
                row["scan_id"],
                str(
                    Path(
                        row["nifti_folder"],
                        f"{row['scan_id']}_{row['scan_type']}",
                        "image.nii.gz",
                    )
                ),
            ]
        )
    new_df = pandas.DataFrame(
        new_rows,
        columns=[
            "project_name",
            "experiment_name",
            "scan_name",
            "scan_type",
            "frame_number",
            "file_location",
        ],
    )
    new_filename = f"new_{file_name.replace('old_', '')}"
    new_df.to_csv(new_filename, index=False)
    print(f"Wrote converted CSV to {new_filename}.")
