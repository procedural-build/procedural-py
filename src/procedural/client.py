import os
import requests
from datetime import datetime
import json
import base64

from procedural.file_handling import encode_files


class Client:
    def __init__(self, url, username=None, password=None):
        self.url = url
        self._access_token = None
        self._refresh_token = None
        self.get_tokens(username, password)

    def get_tokens(self, username, password):
        """Gets the access and refresh token"""
        full_path = os.path.join(self.url, "auth-jwt/get/")
        response = requests.post(full_path, data={"username": username, "password": password})

        if response.status_code == 200:
            data = response.json()
            self._access_token = data.get("access")
            self._refresh_token = data.get("refresh")
        else:
            response.raise_for_status()

    def check_token(self):
        if self.token_exp_time < 0:
            self.get_access_token()

    @property
    def jwt_payload(self):
        """ Get the payload from the JWT
        """
        if not self._access_token:
            return None
        payload_bytes = self._access_token.split(".")[1].encode("utf8")
        missing_padding = len(payload_bytes) % 4
        if missing_padding:
            payload_bytes += b"=" * (4 - missing_padding)
        payload = json.loads(base64.b64decode(payload_bytes))
        return payload

    @property
    def token_exp_time(self):
        """ Seconds remaining until token expiry"""
        payload = self.jwt_payload
        if payload is None:
            return None
        exp_timestamp = payload.get("exp", None)
        if not exp_timestamp:
            raise Exception("Could not get expiry timestamp from JWT token")
        now = datetime.utcnow()
        expiry = datetime.utcfromtimestamp(exp_timestamp)
        return (expiry - now).total_seconds()

    def get_access_token(self):
        full_path = os.path.join(self.url, "auth-jwt/refresh/")
        response = requests.post(full_path, data={"refresh": self._refresh_token})

        if response.status_code == 200:
            data = response.json()
            self._access_token = data.get("access")
        else:
            response.raise_for_status()

    def get_or_create(self, path, query_params={}, create_params={}, extra_headers={}):
        tasks = self.get(path, query_params, extra_headers)

        if len(tasks) == 1:
            return tasks[0]
        elif len(tasks) > 1:
            raise ValueError("Too many tasks returned")
        elif len(tasks) == 0:
            create_params.update(**query_params)
            return self.create(path, create_params, extra_headers)

    def _get_full_path(self, path: str) -> str:
        if path.startswith("/"):
            path = path[1:]
        return os.path.join(self.url, path)

    def get(self, path, query_params={}, extra_headers={}):
        self.check_token()

        full_path = self._get_full_path(path)
        response = requests.get(full_path, params=query_params, headers=self._get_headers(extra_headers))

        return self._handle_response(response)

    def create(self, path, data={}, extra_headers={}):
        self.check_token()

        full_path = self._get_full_path(path)
        response = requests.post(full_path, json=data, headers=self._get_headers(extra_headers))

        return self._handle_response(response)

    def list(self):
        pass

    def delete(self, path, extra_headers={}):
        self.check_token()

        full_path = self._get_full_path(path)
        response = requests.delete(full_path, headers=self._get_headers(extra_headers))

        return self._handle_response(response)

    def update(self, path, data=None, files=None, extra_headers={}):
        self.check_token()

        full_path = self._get_full_path(path)

        if files:
            data = encode_files(files)

        try:
            response = requests.put(full_path, json=data, headers=self._get_headers(extra_headers))
        except TypeError:
            response = requests.put(full_path, data=data, headers=self._get_headers(extra_headers))

        return self._handle_response(response)

    def _get_headers(self, extra_headers={}):
        headers = {"Authorization": f"JWT {self._access_token}"}
        headers.update(**extra_headers)
        return headers

    @staticmethod
    def _handle_response(response):
        if response.ok:
            if response.status_code != 204:
                return response.json()
        else:
            response.raise_for_status()

    def __str__(self):
        return f"{self.url} - Authenticated: {'Yes' if self._access_token else 'No'}"
