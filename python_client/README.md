# MIQA Python Client
This simple python library is intended to allow users of a MIQA instance to interact with the MIQA API programmatically and perform tasks they may not be able to accomplish in the web interface.

The structure of classes in this library closely imitates the structure of models in MIQA, so it is recommended that a user understands this structure before proceeding to use the python client. The documentation explaining this structure can be found at https://openimaging.github.io/miqa/projects/.

In summary, Projects are the top-level objects that act as organizational buckets for experiments. Experiments are collections of scans that may be related in some way. Scans are collections of related 3D medical images. Each scan must have at least one image, or Frame, associated with it. A scan may have multiple Frames representing time steps or some other fourth dimension to the images collected. The purpose of MIQA is to annotate the quality of scans that are currently categorized as usable, unusable, or otherwise. Thus, a Scan Decision is an object that stores those determinations. A Scan can have zero or more Scan Decisions.

## Usage
Example usages of available functions are shown in [example.py](example.py). Reading this example is the best way to understand how functions in this client are used. Below are some further explanations of the usages found in the example.

## Explanation of classes
In the MIQA python client, the top-level class, `MIQA`, refers to an instance of MIQA. For a single organization, this is likely the only active instance you will use. This class holds information for connecting to the API.

Each `MIQA` object will hold a collection of `Project` objects, which will each hold a collection of `Experiment` objects, which will each hold a collection of `Scan` objects, which will each hold collections of both `Frame` objects and `ScanDecision` objects.

The following table displays the available attributes and functions on these classes. Attributes are exactly as they are returned by the API.

| Class Name | Attributes | Functions |
|--|--|--|
| MIQA | url, headers, token, version, projects, artifact_options | login, get_config, get_all_objects, get_project_by_id, create_project, print_all_objects |
| Project | id, name, creator, experiments, total_scans, total_complete, MIQA | get_experiment_by_id, add_experiment, print_all_objects, delete |
| Experiment | id, name, scans, project, note | get_scan_by_id, add_scan, update_note, print_all_objects |
| Scan | id, name, experiment, decisions, frames, scan_type, subject_id, session_id, scan_link | add_frames_from_paths, add_decision, print_all_objects |
| Frame | id, frame_number, frame_evaluation, extension, download_url |  |
| ScanDecision | id, decision, creator, created, note, user_identified_artifacts, location |  |

## Explanation of functions
Each level in the object hierarchy can be accessed from the level above it.
 - Projects can be accessed with `MIQA.projects`, `MIQA.get_project_from_id(id)`, or `MIQA.create_project(name)`.
 - Experiments can be accessed with `Project.experiments`, `Project.get_experiment_by_id(id)`, or `Project.add_experiment(name)`.
 - Scans can be accessed with `Experiment.scans`, `Experiment.get_scan_by_id(id)`, or `Experiment.add_scan(name, scan_type, [subject_id, session_id, scan_link])`.
 - Frames can be accessed with `Scan.frames` or `Scan.add_frames_from_paths(paths)`.
 - Scan Decisions can be accessed with `Scan.decisions` or `Scan.add_decision(decision, note, [present_artifacts, absent_artifacts])`


  **print_all_objects**: Classes which store more objects (i.e. not `Frame` nor `ScanDecision`) have a function which recursively prints all objects below the target object. This is for the convenience of the user to see stored objects quickly. For example, calling `print_all_objects` on a MIQA object will result in something similar to the following printout:
```
MIQA Instance http://localhost:8000/api/v1
 Project Guys
   Experiment IXI002
     Scan 0828-DTI
     |Decisions:   []
     |Frames:   [Frame 0, Frame 1, Frame 2, Frame 3, Frame 4, Frame 5, Frame 6, Frame 7, Frame 8, Frame 9, Frame 10, Frame 11, Frame 12, Frame 13, Frame 14, Frame 15, Frame 16]
     Scan 0828-MRA
     |Decisions:   []
     |Frames:   [Frame 0]
     Scan 0828-PD
     |Decisions:   []
     |Frames:   [Frame 0]
     Scan 0828-T1
     |Decisions:   []
     |Frames:   [Frame 0]
     Scan 0828-T2
     |Decisions:   []
     |Frames:   [Frame 0]
   Experiment IXI016
     Scan 0697-MRA
     |Decisions:   []
     |Frames:   [Frame 0]
     Scan 0697-PD
     |Decisions:   []
     |Frames:   [Frame 0]
     Scan 0697-T1
     |Decisions:   []
     |Frames:   [Frame 0]
     Scan 0697-T2
     |Decisions:   []
     |Frames:   [Frame 0]
```
Whereas calling `print_all_objects` on a Scan object will produce a much shorter printout:
```
Scan 0697-T2
 |Decisions:   []
 |Frames:   [Frame 0]
```
