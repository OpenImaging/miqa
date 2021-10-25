/* eslint camelcase: "off" */

interface User {
  id: number,
  username: string,
  email: string,
  is_superuser: boolean
}

interface Image {
  id: string,
  name: string,
}

interface ScanNote {
  // TODO
}

interface ScanDecision {
  // TODO
}

interface Scan {
  id: string,
  name: string,
  scan_id: string,
  scan_type: string,
  notes: ScanNote[],
  experiment: string,
  site: string,
  decisions: ScanDecision[],
  images: Image[],
}

interface Experiment {
  id: string,
  name: string,
  lock_owner: {
    id: number,
    username: string,
  },
  scans?: Scan[],
}

interface Project {
  id: string,
  name: string,
  experiments?: Experiment[],
}

interface Settings {
  importPath: string,
  exportPath: string
}

interface HTMLInputEvent extends Event {
  target: HTMLInputElement & EventTarget;
}

export {
  User, Project, Settings, HTMLInputEvent,
};
