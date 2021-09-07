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

export { User, Session }
