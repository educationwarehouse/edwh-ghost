from dataclasses import field, dataclass
from json import JSONDecodeError
from pprint import pprint

import jwt
import requests
import time
import sys

from datetime import datetime as dt

from .abs_resources import GhostAdminResource
from .exceptions import *
from .resources import (
    PostResource,
    PageResource,
    AuthorResource,
    TagResource,
    ImageResource,
    ThemeResource,
    SiteResource,
    SettingsResource,
    MemberResource,
)

MAX_ERROR_LIMIT = 3


@dataclass
class GhostAdmin:
    url: str
    adminAPIKey: str = field(repr=False)
    contentAPIKey: str = field(repr=False)
    headers: dict = field(init=False, repr=False)
    api_version: str = "v4"  # or v3

    _session = requests.Session()

    def __post_init__(self):
        """
        Setup the JWT Authentication headers
        """

        self.headers = self._create_headers()

        # resources:
        self.posts = PostResource(self)
        self.pages = PageResource(self)
        self.authors = AuthorResource(self)
        self.tags = TagResource(self)
        self.images = ImageResource(self)
        self.themes = ThemeResource(self)
        self.members = MemberResource(self)

        self.post = PostResource(self, single=True)
        self.page = PageResource(self, single=True)
        self.author = AuthorResource(self, single=True)
        self.tag = TagResource(self, single=True)
        self.image = ImageResource(self, single=True)
        self.theme = ThemeResource(self, single=True)
        self.member = MemberResource(self, single=True)

        # there's only one site/one settings:
        self.site = SiteResource(self, single=True)
        self.settings = SettingsResource(self, single=True)

    def resource(self, name, single=False):
        class _Resource(GhostAdminResource):
            # Temporary Resource
            resource = name

        return _Resource(self, single=single)

    def _interact(
        self, verb, endpoint, params=None, files=None, json=None, api_version=None
    ):
        if endpoint.startswith("content"):
            endpoint += "?key=" + self.contentAPIKey

        if api_version is None:
            # default
            api_version = self.api_version
            headers = self.headers
        else:
            # custom api version, new headers:
            headers = self._create_headers(api_version)

        verb = verb.lower()

        # url + /ghost/api/ + /v3/admin/ + ...
        url = "/".join([self.url.strip("/"), "ghost/api", api_version, endpoint])

        error_count = 0

        while error_count < MAX_ERROR_LIMIT:
            if verb == "get":
                resp = self._session.get(url, headers=headers, params=params)
            elif verb == "post":
                resp = self._session.post(
                    url, headers=headers, params=params, files=files, json=json
                )
            elif verb == "put":
                resp = self._session.put(
                    url, headers=headers, params=params, files=files, json=json
                )
            elif verb == "delete":
                resp = self._session.delete(url, headers=headers, params=params)
            else:
                raise ValueError(f"Unknown verb: {verb}")
            if resp.status_code == 401 and not error_count:
                # retry instantly with new headers
                self.headers = self._create_headers()
                error_count += 1
            elif resp.status_code == 401 and error_count:
                # after the first error, try again after a timeout
                time.sleep(5)
                self.headers = self._create_headers()
                error_count += 1
            else:
                # on other error codes, print and return
                if not resp.ok:
                    # print(
                    #     {
                    #         "endpoint": url,
                    #         "method": verb,
                    #         "code": resp.status_code,
                    #         "message": resp.text,
                    #     },
                    #     file=sys.stderr,
                    # )
                    pass
                return resp

        raise IOError("Could not contact API correctly after 3 tries.")

    def _handle_errors(self, response):
        try:
            data = response.json()
            err = data.get("errors")
            if not err:
                raise GhostUnknownException(
                    response.status_code,
                    error_message="Unknown Error Occurred",
                    exception=data,
                )

            main_error = err[0]
            raise GhostResponseException(
                response.status_code,
                main_error["type"],
                main_error["message"],
                exception=err,
            )

        except JSONDecodeError as e:
            raise GhostJSONException(
                response.status_code, error_message="JSON Parsing Failed", exception=e
            )

    def GET(self, url, params=None):
        """
        Pass to self.interact with GET
        """
        resp = self._interact("get", url, params=params)

        if not resp.ok:
            self._handle_errors(resp)

        return resp.json()

    def POST(self, url, params=None, json=None, files=None):
        """
        Pass to self.interact with POST
        """
        resp = self._interact("post", url, params=params, json=json, files=files)

        if not resp.ok:
            self._handle_errors(resp)

        return resp.json()

    def PUT(self, url, params=None, json=None, files=None):
        """
        Pass to self.interact with PUT
        """
        resp = self._interact("put", url, params=params, json=json)

        if not resp.ok:
            self._handle_errors(resp)

        return resp.json()

    def DELETE(self, url, params=None):
        """
        Pass to self.interact with DELETE
        """
        return self._interact("delete", url, params=params).status_code == 204

    def _create_token(self, api_version=None):
        if not (self.adminAPIKey and self.contentAPIKey):
            raise ValueError("Please enter a valid admin and content api key!")

        if api_version is None:
            api_version = self.api_version

        DURATION_IN_MINUTES = 5
        id, secret = self.adminAPIKey.split(":")
        iat = int(dt.now().timestamp())
        header = {"alg": "HS256", "typ": "JWT", "kid": id}
        payload = {
            "iat": iat,
            "exp": iat + (DURATION_IN_MINUTES * 60),
            "aud": f"/{api_version}/admin/",
        }
        return jwt.encode(
            payload, bytes.fromhex(secret), algorithm="HS256", headers=header
        )

    def _create_headers(self, api_version=None):
        """
        Create the ghost authentication header

        Args:
            api_version (string): for which API version to create a token

        Returns:
            dict: Authorization header
        """

        return {"Authorization": f"Ghost {self._create_token(api_version)}"}


# todo: ghost content client that doesn't use adminAPI key, only content API key and only READ
