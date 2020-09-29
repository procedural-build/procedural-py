#!/usr/bin/python3

"""
Utilities for API Access.  Specifically a User class which gets or refreshes the
access token and
"""

from urllib import request as Req
from urllib.parse import urlencode
from datetime import datetime
import base64
import json


# Common function for pretty-print JSON data
def printJSON(pyObj):
    print(json.dumps(pyObj, indent=4))


# Store each user in a class with their access token and a method
# "request" to GET, POST, PUT, DELETE to the API urls
class User():

    content_header = {"content-type": "application/json"}

    def __init__(self, username, password, host="https://test.sustainabilitytool.net"):
        self.host_url = host[:-1] if host[-1] == "/" else host
        self.username   = username
        self.password   = password
        self._access_token   = ""
        self._refresh_token  = ""

    @property
    def token(self):
        return self._access_token

    @property
    def jwt_payload(self):
        """ Get the payload from the JWT
        """
        if not self._access_token:
            return None
        payload_bytes = self._access_token.split('.')[1].encode('utf8')
        missing_padding = len(payload_bytes) % 4
        if missing_padding:
            payload_bytes += b'=' * (4 - missing_padding)
        payload = json.loads(base64.b64decode(payload_bytes))
        return payload

    @property
    def token_exp_time(self):
        """ Seconds remaining until token expiry
        """
        payload = self.jwt_payload
        if payload is None:
            return None
        exp_timestamp = payload.get('exp', None)
        if not exp_timestamp:
            raise Exception('Could not get expiry timestamp from JWT token')
        now = datetime.utcnow()
        expiry = datetime.utcfromtimestamp(exp_timestamp)
        return (expiry - now).total_seconds()

    def headers(self, extra_headers=None):
        header = self.content_header
        if self.token:
            header.update({'Authorization': 'JWT %s'%(self.token)})
        if extra_headers:
            header.update(extra_headers)
        return header

    def clear_tokens(self):
        self._access_token = ""
        self._refresh_token = ""

    def get_token(self):
        self.clear_tokens()
        response_dict = self.request('POST', '/auth-jwt/get/', {'username': self.username, 'password': self.password})
        self._access_token = response_dict.get('access', None)
        self._refresh_token = response_dict.get('refresh', None)
        for token_type in ['access', 'refresh']:
            if response_dict.get(token_type, None) is None:
                raise Exception("Error getting token: %s", self.printJSON(response_dict))
        print("Got new token. Will expire in", self.token_exp_time)
        return self.token

    def refresh_token(self, time_remaining = 20):
        # Check that we have a refresh token first
        if not self._refresh_token:
            return None
        # Check if the current access token is valid
        exp_time = self.token_exp_time
        if exp_time and exp_time > time_remaining:
            print("No refresh required. Token will expire in", exp_time)
            return self.token
        # Do the refresh
        response_dict = self.request('POST', '/auth-jwt/refresh/', {'refresh': self._refresh_token})
        self._access_token = response_dict['access']
        print("Refreshed token. Will expire in", self.token_exp_time)
        return self.token

    def verify_token(self):
        response_dict = self.request('POST', '/auth-jwt/verify/', {'token': self.token})
        self._access_token = response_dict['access']
        return self.token

    def get_full_url(self, url, query_params):
        # Append query parameters to the url
        url = self.host_url + url
        url_params = urlencode(query_params) if query_params else None
        return '%s?%s'%(url, url_params) if url_params else url

    def request(self, method, url, data=None, params=None, extra_headers=None):
        # Check if the access token needs refreshing unless we are calling an auth-jwt endpoint
        if not url.startswith('/auth-jwt/'):
            self.refresh_token()

        # Get the full url
        url = self.get_full_url(url, params)

        # Set the data that should be sent
        if method == 'POST':
            # Send POST requst with JSON encoded data
            data = json.dumps(data).encode('utf8')

        # Remove data from GET requests (otherwise urllib will conver this to a POST automatically)
        if method == "GET":
            data = None

        # Get the actual request object
        request = Req.Request(url, method=method, data=data, headers=self.headers(extra_headers))
        self.last_response = Req.urlopen(request)

        # Try to parse the response as JSON, otherwise just return the raw response
        try:
            return json.loads(self.last_response.read().decode('utf8'))
        except TypeError:
            return self.last_response
        except json.JSONDecodeError:
            return self.last_response

        return self.last_response
