#  pip install miqa-python-client OR pip install ./python_client

import miqa_python_client
from getpass import getpass

# --- MIQA ---
instance_url = 'http://localhost:8000'
username = 'test@miqa.dev'
password = getpass(f'Enter password for {username}: ')
scan_dir = '/path/to/scans'

instance = miqa_python_client.MIQA(
    instance_url,
    username=username,
    password=password,
)
# These do not need to be called, as they are invoked in the constructor
# instance.login()
# instance.get_config()
instance.get_all_objects()  # if we don't call this before print_all_objects
instance.print_all_objects()  # then print_all_objects will invoke get_all_objects
print(
    instance.url,
    instance.version,
    instance.projects,
    instance.headers,
    instance.token,
    instance.artifact_options,
)

# --- Project ---
# if we still haven't called instance.get_all_objects()
# this will request only the target project to load into instance.projects
# this may be useful if you only want certain projects loaded
project_a = instance.get_project_by_id('6c3ecc33-ee41-45a8-a31a-230ca9b574f0')
project_a.print_all_objects()
# You can create projects if you are a privileged user in this MIQA instance
# If you do not have permission, you will receive a 403 Forbidden response.
# Some instances of MIQA may be configured to allow all users to create projects,
# Otherwise, this is a superuser-only privilege.
# An administrator can edit NORMAL_USERS_CAN_CREATE_PROJECTS in the MIQA settings.
project_b = instance.create_project('New Project')
print(
    project_b.id,
    project_b.name,
    project_b.creator,
    project_b.total_scans,
    project_b.total_complete,
    project_b.experiments,  # a list of experiment objects
    project_b.MIQA,  # a reference to instance
)


# --- Experiment ---
experiment_a = project_a.get_experiment_by_id('2c910635-5d25-496f-9594-2b0e47ea69ce')
experiment_a.update_note('Updated note text')
experiment_a.print_all_objects()
experiment_b = project_b.add_experiment('New Experiment')
print(
    experiment_b.id,
    experiment_b.name,
    experiment_b.note,
    experiment_b.scans,  # a list of Scan objects
    experiment_b.project,  # a reference to project_b
)

# --- Scan ---
scan_a = experiment_a.get_scan_by_id('d0fbfcca-3783-46bc-9047-6be5862356a2')
scan_a.print_all_objects()
scan_b = experiment_b.add_scan(
    "New Scan", "MRA", subject_id="sub001", session_id="ses001", scan_link="my.org/scans/001"
)
new_frames = scan_b.add_frames_from_paths(
    f'{scan_dir}/IXI002-Guys-0828-DTI-01.nii.gz',
    f'{scan_dir}/IXI002-Guys-0828-DTI-02.nii.gz',
    f'{scan_dir}/IXI002-Guys-0828-DTI-03.nii.gz',
)
frame_b = new_frames[-1]
print(
    frame_b.id,
    frame_b.frame_number,
    frame_b.frame_evaluation,  # this will likely be empty immediately after creation (it takes time on the server)
    frame_b.extension,
    frame_b.download_url,
)

decision_one = scan_b.add_decision("usable", "I think this scan looks great!")
print(
    decision_one.id,
    decision_one.decision,
    decision_one.creator,
    decision_one.created,
    decision_one.note,
    decision_one.user_identified_artifacts,
    decision_one.location,
)
decision_two = scan_b.add_decision(
    "unusable",
    "I disagree with decision one.",
    present_artifacts=[
        'flow_artifact',
        'truncation_artifact',
        'swap_wraparound',
        'susceptibility_metal',
        'partial_brain_coverage',
        'ghosting_motion',
    ],
)
decision_three = scan_b.add_decision(
    "usable-extra",
    "I think this scan has potential.",
    absent_artifacts=[
        'lesions',
        'misalignment',
        'inhomogeneity',
    ],
)
decision_four = scan_b.add_decision(
    "questionable",
    "I'm not sure about this scan and would like tier 2 review.",
    present_artifacts=[
        'flow_artifact',
        'truncation_artifact',
        'swap_wraparound',
    ],
    absent_artifacts=[
        'lesions',
        'misalignment',
        'inhomogeneity',
    ],
)
print(
    scan_b.id,
    scan_b.name,
    scan_b.decisions,  # a list of ScanDecision objects
    scan_b.frames,  # a list of Frame objects
    scan_b.experiment,  # a reference to experiment_b
    scan_b.scan_type,
    scan_b.subject_id,
    scan_b.session_id,
    scan_b.scan_link,
)


# --- Cleanup ---
project_b.delete()
