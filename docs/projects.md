## Projects
### Object organization
There are a few different standards for organizing files for a medical imaging effort, and some researchers may have unique file structures. MIQA is built to ingest data from almost any file structure and present it in a flexible but uniform object organization.

Projects are the top level of the organization tree; they represent whole research efforts. Collaboration and image sharing is set at the project level, so privileged users (superusers and the creator of a project) may set permissions for other users on a project. Each project has a group of collaborators with read-only access and a group of members who may be given tier 1 review access or tier 2 review access.  (see [Users > User roles](./users.md#User-roles) for details).

Within each project is a set of zero or more experiments, and each experiment has within it a set of zero or more scans. There is one final layer of organization at the sub-scan level, since sometimes multiple image files can be associated with a single scan. A scan object has a set of one or more frames, where each frame is associated with one image file. Frames are intended to represent any sub-scan structure, such as time steps or positions. While frames support the use of sub-scan structures, it is not required to have multiple frames per scan. If a scan only needs one image file associated with it, simply use one frame within the scan. In the case that you have multiple image files to associate with a single Scan, this is when multiple Frames can be made for a single Scan and when Frame ordering becomes applicable.

It is up to the project creator how to organize image files in this schema. Projects may be created on the homepage (see [Site navigation > Projects homepage](./site.md#Projects-homepage) for details).

### Imports and exports
There are two ways to add data to a project in MIQA; both are available via the project homepage. The first method is using the “Add Scans” button, which allows users with edit access on the project (superusers, the project creator, and reviewers) to upload images from their local computer to MIQA. The second method is using imports, which involves reading files on the server machine and ingesting them as objects in MIQA. This distinction is important; imports involve files on the server machine, which is why MIQA restricts the permission to configure imports to only superusers.

Imports are configured with import files; only superusers may edit and save the file path which MIQA will use to perform imports. MIQA reads the contents of the import file to understand the desired configuration of objects (experiments, scans, and frames) within a project. To read more about the requirements and format of import files, see the MIQA Administrator Manual.)

Any user with edit access on a project may perform an import once a superuser has specified the file path for a project’s import file. It is important that users perform this action with discretion because when an import is performed, all information in the project is overwritten. This includes any decisions made on scans. If a project needs more scans but cannot be overwritten entirely, do not use the import method; it is recommended to use the “Add Scans” button. Imports are intended to add large volumes of data to a project at its start.

A project export is a similar operation, but does not alter the contents of the project. Instead, exports record the state of a project to a file on the server machine in a format that is congruent with the import file format. This means it is possible to save the state of a project and bring the project to that state by importing the contents of the export file.

### Global imports and exports
Superusers also have permission to perform global imports and exports, which are cross-project operations. A global import file may specify more than one project to change, and a global export will record the states of all projects. To read more about global imports and exports, see the MIQA Administrator Manual.
