## User Roles in MIQA
MIQA users have a global role as well as any number of per-project roles.

### Project Roles
Each Project has a list of members specifying who may view and edit that project and the objects within.

- Users added as "Collaborators" have read-only access. Collaborators cannot edit Experiment notes, upload scans, or submit decisions on scans.
- Users added as "Members" have write access. Members can edit Experiment notes, upload scans, and submit decisions on scans. There are two classes of Members; A Member can either be "Tier 1 Reviewer" or "Tier 2 Reviewer".  Tier 1 Reviewers can submit a decision that a scan is either "usable" or "questionable". Tier 2 Reviewers can submit a decision that a scan is "usable", "unusable", or "usable-extra".

A Scan is considered "unreviewed" when no decisions exist for that scan; it is not considered "complete" until a decision has been made by a Tier 2 Reviewer. If a Scan only has decisions made by Tier 1 Reviewers, it is considered as "needs Tier 2 review".

**If a Project has no need to differentiate between reviewer tiers, simply set all reviewers as Tier 2.**

> All Projects implicitly include _all superusers_ as Tier 1 Reviewers, since superusers automatically have edit permissions on every project. See below.

### Global Roles
Users can either be a superuser or a normal user with no heightened privileges. Superusers are trusted with the following privileges:

- Can edit the import path and export path on projects
- Can perform imports and exports on projects
- Can delete projects
- Can grant/revoke project roles to/from other users
- Automatically have at least tier 1 reviewer privileges on every project
- Can claim edit access on any Experiment (as long as the experiment is not currently being edited)
- Can approve the accounts of new Users once the email for that new account has been confirmed

**Normal Users will not be able to view or interact with a Project's settings (i.e. importing and exporting features).**
