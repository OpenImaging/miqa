/* eslint camelcase: "off" */
/* eslint no-unused-vars: "off" */
/* eslint no-shadow: "off" */

interface User {
  id: number,
  username: string,
  email: string,
  is_superuser: boolean
}

interface ResponseData {
  detail: string,
  errors: string[],
  warnings: string[],
}

interface Frame {
  id: string,
  name: string,
  scan: string,
  extension: string,
}

interface ScanDecision {
  id: string,
  creator: User,
  created: string,
  decision: string,
  note: string,
  user_identified_artifacts: {
    present: String[],
    absent: String[],
  },
  location: {
    i: number,
    j: number,
    k: number,
  }
}

interface Scan {
  id: string,
  name: string,
  scan_id: string,
  scan_type: string,
  experiment: string,
  decisions: ScanDecision[],
  frames: Frame[],
  subject_id: string,
  session_id: string,
  scan_link: string,
  notes: string,
}

interface Experiment {
  id: string,
  name: string,
  lock_owner: {
    id: number,
    username: string,
  },
  scans?: Scan[],
  project: string,
  note: string,
}

interface ProjectSettings {
  import_path: string,
  export_path: string,
  permissions?: Object,
}

enum ScanState {
  unreviewed = '#1460A3',
  needs_tier_2_review = '#6DB1ED',
  complete = '#00C853',
}

interface ProjectTaskOverview {
  total_experiments: number,
  total_scans: number,
  my_project_role: string,
  scan_states: {
    string: string,
  },
}

interface Project {
  id: string,
  name: string,
  experiments?: Experiment[],
  settings: ProjectSettings,
  status: {
    total_scans: number,
    total_complete: number,
  }
  creator: string;
}

interface Email {
  to: string[],
  cc: string[],
  bcc: string[],
  subject: string,
  body: string,
  screenshots: any[],
}

export {
  User, ResponseData, Project, ProjectTaskOverview, ProjectSettings,
  Scan, ScanDecision, Frame, ScanState, Email, Experiment,
};
