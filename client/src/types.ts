/* eslint camelcase: "off" */

interface User {
  id: number,
  username: string,
  email: string,
  is_superuser: boolean
}

interface Session {
  id: number,
  name: string
}

interface Settings {
  importpath: string,
  exportpath: string
}

interface HTMLInputEvent extends Event {
  target: HTMLInputElement & EventTarget;
}

export {
  User, Session, Settings, HTMLInputEvent,
};
