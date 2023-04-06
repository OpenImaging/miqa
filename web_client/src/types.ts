/* eslint camelcase: "off" */
/* eslint no-unused-vars: "off" */
/* eslint no-shadow: "off" */
import type { WorkerPool } from 'itk/WorkerPool';

interface ResponseData {
  detail: string,
  errors: string[],
  warnings: string[],
  default_email_recipients?: string[],
  permissions?: string[],
  id?: string,
}

interface User {
  id: number,
  username: string,
  email: string,
  is_superuser: boolean
}

interface Email {
  to: string[],
  cc: string[],
  bcc: string[],
  subject: string,
  body: string,
  screenshots: any[],
}

interface Experiment {
  id: string,
  name: string,
  lock_owner: { // TODO: Can remove?
    id: number,
    username: string,
  },
  lockOwner: {
    id: number,
    username: string,
  },
  // eslint-disable-next-line no-use-before-define
  scans?: Scan[],
  project: string,
  note: string,
}

interface Frame {
  id: string,
  name: string,
  scan: string,
  extension: string,
  experiment?: string,
  frame_evaluation?: string,
}

interface MIQAConfig {
  version: string,
  artifact_states: {
    PRESENT: boolean,
  }
  artifact_options?: {
    [key: string]: {
      name: string,
    }
  }
}

interface Project {
  id: string,
  name: string,
  experiments?: Experiment[],
  // eslint-disable-next-line no-use-before-define
  settings: ProjectSettings,
  status: {
    total_scans: number,
    total_complete: number,
  }
  creator: string;
}

interface ProjectSettings {
  import_path: string,
  export_path: string,
  anatomy_orientation?: string,
  permissions?: {
    collaborator: [],
    tier_1_reviewer: [],
    tier_2_reviewer: [],
  },
}

interface ProjectTaskOverview {
  project_id: string,
  total_experiments: number,
  total_scans: number,
  my_project_role: string,
  scan_states: {
    string: string,
  },
}

interface Scan {
  id: string,
  name: string,
  scan_id: string,
  scan_type: string,
  experiment: string,
  // eslint-disable-next-line no-use-before-define
  decisions: ScanDecision[],
  frames: Frame[],
  subject_id: string, // TODO: Can remove?
  subjectID: string,
  session_id: string, // TODO: Can remove?
  sessionID: string,
  scan_link: string, // TODO: Can remove?
  link: string,
  notes: string,
  cumulativeRange?: number,
}

interface ScanDecision {
  id: string,
  creator: User,
  created: string,
  decisions: [],
  note: string,
  user_identified_artifacts: {
    present: string[],
    absent: string[],
  },
  location: {
    i: number,
    j: number,
    k: number,
  }
}

enum ScanState {
  unreviewed = '#1460A3',
  needs_tier_2_review = '#6DB1ED',
  complete = '#00C853',
}

interface WindowLock {
  lock: boolean;
  duration?: number;
  target?: string;
  associatedImage?: string;
}

interface MIQAStore {
  MIQAConfig: MIQAConfig;
  me: User | null;
  allUsers: User[];
  reviewMode: boolean;
  globalSettings?: ProjectSettings;
  currentProject: Project | null;
  currentTaskOverview: ProjectTaskOverview | null;
  currentProjectPermissions: {
    [key: string]: User[];
  };
  projects: Project[];
  experimentIds: string[];
  experiments: {
    [key: string]: Experiment;
  };
  experimentScans: {
    [key: string]: string[];
  },
  scans: {
    [key: string]: Scan;
  };
  scanFrames: any;
  frames: {
    [key: string]: Frame;
  };
  proxyManager: any;
  vtkViews: any[];
  currentFrameId: string | null;
  loadingFrame: boolean;
  errorLoadingFrame: boolean;
  loadingExperiment: boolean;
  currentScreenshot: any;
  screenshots: any[];
  scanCachedPercentage: number;
  showCrosshairs: boolean;
  storeCrosshairs: boolean;
  sliceLocation: {
    [key: string]: number;
  };
  iIndexSlice: number;
  jIndexSlice: number;
  kIndexSlice: number;
  currentWindowWidth: number;
  currentWindowLevel: number;
  renderOrientation: string;
  windowLocked: WindowLock;
  workerPool: WorkerPool;
  lastApiRequestTime: number;
}

export {
  User, ResponseData, Project, ProjectTaskOverview, ProjectSettings,
  Scan, ScanDecision, Frame, ScanState, Email, Experiment, MIQAConfig,
  WindowLock, MIQAStore,
};
