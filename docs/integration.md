## Integrating MIQA into your current workflow

Since MIQA offers two options for bringing images into a project, it is a flexible tool that may act as either a part of or replacement for your current workflow.

### Setting up MIQA as a primary image repository

In the case that your organization does not have an existing tool for storing, sharing, or organizing scans or your organization is looking for a replacement tool, MIQA can act as a standalone database for your information. In this case, using the import/export feature is optional, and should only be used in the case that images are regularly saved on the server machine and need to be added to the database. Otherwise, your team can simply use the “Upload Scans” feature in the MIQA interface to add images to a project from any machine.

### Integrating MIQA with an existing image repository

Your organization may already have a tool for storing, sharing, and organizing scans that is only lacking a viewer or annotation features. MIQA can work together with your existing repository with a system of imports and exports that keeps the information in the two databases synced. In this case, it is recommended that each project that should be synced uses the same path for the import file and export file, and scheduled jobs on the server machine can be used to complete the following cycle at regular intervals:

1.  Use the MIQA API to perform an export of the project’s current state to the import/export file
    
2.  Make a copy of the export file and move it to a backup location
    
3.  Use the API of your primary image repository to sync new changes written in the import/export file (i.e. decisions on scans saved since the last sync)
    
4.  Use the API of your primary image repository to download any new images in the project
    
5.  Write the new images as new frame rows in the import/export file
    
6.  Use the MIQA API to perform an import of the project’s refreshed state to sync the two databases
    

Some caveats to this approach should be noted:

-   With regular import/export cycles, some saved decisions may be lost, since an export only records the last decision saved. Any decisions saved prior will not be included in the refreshed project state.
    
-   Images added to the project via the “Upload Scans” feature in the MIQA interface are not stored on the server machine, so exports of these scans are not yet supported. Since these scans cannot be exported, they will be lost in the refreshed project state.

### Accessing the MIQA API

MIQA uses a package called `django-oauth-toolkit` for its authentication backend. You may wish to access the MIQA API with `curl`, `python`, or some other request-making library. As an example, here is how you may make a simple authorized request to the MIQA API:

```
import requests
from getpass import getpass
  

base_url = "https://<MIQA_BASE_URL>/api/v1"
headers = {
	"Accept": "application/json",
} 

def login():
	print("Logging in...")
	username = input("MIQA username: ")
	password = getpass("MIQA password: ")
	
	auth_url = base_url.replace("/api/v1", "/api-token-auth/")
	resp = requests.post(
		auth_url,
		data={
			"username": username,
			"password": password,
		},
)

	if resp.status_code != 200:
		raise Exception("Invalid username or password provided")
	token = resp.json()["token"]
	headers["Authorization"] = f"Token {token}"
  
login()
content = requests.get(f"{base_url}/users", headers=headers)
print(content.json())
```


We are considering options to provide access to the MIQA API from command line clients or alternative programming interfaces, such as Jupyter notebooks. This document will be updated as these options mature.

### Additional MIQA Capabilities

If MIQA is close to what your institution needs for its workflow, but some features need adjustment, please contact the MIQA team to discuss customization options. The current state of this document only reflects the needs of MIQA customers so far, but ideas for expansion and enhancements, some of which may apply to your own situation, have been discussed.

-   It is possible to use an alternative vocabulary for scan decision options and artifact options. With custom artifacts, the MIQA neural network would need to be retrained for scan evaluations.
    
-   MIQA may be repurposed for training a neural network for other kinds of image classification; reviewers can provide manual labeling of large image datasets and those labels can be supplied as ground-truths for the neural network.
    
-   Managing multiple users allows a small team of coordinating physicians to interact together, and the email features improve the team’s ability to address complicated cases. If your institution has more specific requirements for collaboration, MIQA can be expanded to include such features.
