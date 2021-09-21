/* eslint camelcase: "off" */

interface User {
  id: number,
  username: string,
  email: string,
  is_superuser: boolean
}

interface Project {
  id: string,
  name: string
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
