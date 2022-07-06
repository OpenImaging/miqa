from getpass import getpass
import requests
from s3_file_field_client import S3FileFieldClient


from project import Project


class MIQA:
    """
    Attributes:
      url, headers, token, version,
      projects, artifact_options
    Functions:
      login, get_config, make_request, upload_file,
       get_all_objects, get_project_by_id, list_all_objects
    """

    def __init__(self, url, username=None, password=None):
        if not username:
            username = input("MIQA username: ")
        if not password:
            password = getpass(f"Enter MIQA password for {username}")
        self.url = url.rstrip("/")
        if "/api" not in self.url:
            self.url += "/api/v1"
        self.headers = {
            "Accept": "application/json",
        }
        self.projects = []
        self.login(username, password)
        self.get_config()

    def login(self, username, password):
        auth_url = self.url.replace("/api/v1", "/api-token-auth/")
        response = requests.post(
            auth_url,
            data={
                "username": username,
                "password": password,
            },
        )
        if response.status_code != 200:
            raise Exception("Invalid username or password provided")
        self.token = response.json()["token"]
        self.headers["Authorization"] = f"Token {self.token}"

    def get_config(self):
        content = requests.get(f"{self.url}/configuration", headers=self.headers).json()
        self.version = content["version"]
        self.artifact_options = content["artifact_options"]
        return content

    def make_request(
        self,
        api_path,
        GET=False,
        POST=False,
        DELETE=False,
        body=None,
    ):
        api_path = api_path.rstrip('/').lstrip('/')
        content = None
        if GET:
            content = requests.get(f"{self.url}/{api_path}", headers=self.headers)
        elif POST:
            content = requests.post(
                f"{self.url}/{api_path}",
                headers=self.headers,
                json=body,
            )
        elif DELETE:
            content = requests.delete(f"{self.url}/{api_path}", headers=self.headers)
        try:
            content.raise_for_status()
        except requests.exceptions.HTTPError:
            raise Exception(f'Request failed: {content.json()}')
        return content.json() if content else None

    def upload_file(self, file_path: str, field_id: str):
        sess = requests.Session()
        sess.headers.update(**self.headers)
        s3ff = S3FileFieldClient(f'{self.url}/s3-upload/', sess)
        with open(file_path, 'rb') as file_stream:
            return s3ff.upload_file(
                file_stream,
                file_path.split('/')[-1],
                field_id,
            )

    def get_all_objects(self):
        content = self.make_request("projects", GET=True)
        self.projects = [Project(**result, MIQA=self) for result in content["results"]]
        return self.projects

    def get_project_by_id(self, id: str):
        if self.projects:
            matches = [proj for proj in self.projects if proj.id == id]
            if len(matches) == 1:
                return matches[0]
        try:
            content = requests.get(f"{self.url}/projects/{id}", headers=self.headers).json()
        except Exception:
            return None
        new_project = Project(**content, MIQA=self)
        self.projects.append(new_project)
        return new_project

    def list_all_objects(self, indent=0):
        if len(self.projects) < 1:
            self.get_all_objects()
        print(" " * indent, str(self))
        for proj in self.projects:
            proj.list_all_objects(indent=indent)

    def __repr__(self):
        return f"MIQA Instance {self.url}"
