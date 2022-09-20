import abc
from dataclasses import field, dataclass
from json import JSONDecodeError

import jwt
import requests
import time

from datetime import datetime as dt

import yarl

from .exceptions import *
from .resources import *

MAX_ERROR_LIMIT = 3


@dataclass
class GhostClient(abc.ABC):
    url: str
    headers: dict = field(init=False, repr=False)
    contentAPIKey: str = field(repr=False)
    adminAPIKey: str = None
    api_version: str = "v4"  # or v3

    _session = requests.Session()

    # noinspection PyUnreachableCode
    if False:
        # Types, instanciated with _setup_resources_on_self:
        # useful for IDE's
        # post: PostResource
        posts: PostResource = field(init=False, repr=False, compare=False)
        page: PageResource = field(init=False, repr=False, compare=False)
        pages: PageResource = field(init=False, repr=False, compare=False)
        author: AuthorResource = field(init=False, repr=False, compare=False)
        authors: AuthorResource = field(init=False, repr=False, compare=False)
        tag: TagResource = field(init=False, repr=False, compare=False)
        tags: TagResource = field(init=False, repr=False, compare=False)
        image: ImageResource = field(init=False, repr=False, compare=False)
        images: ImageResource = field(init=False, repr=False, compare=False)
        theme: ThemeResource = field(init=False, repr=False, compare=False)
        themes: ThemeResource = field(init=False, repr=False, compare=False)
        member: MemberResource = field(init=False, repr=False, compare=False)
        members: MemberResource = field(init=False, repr=False, compare=False)
        user: UserResource = field(init=False, repr=False, compare=False)
        users: UserResource = field(init=False, repr=False, compare=False)
        # End types

    def _setup_resources_on_self(self, resources, content=False):
        """
        Arguments:
            resources (list[type])
            content (bool)
        """
        for resource in resources:
            singular = resource.__name__.lower().split("resource")[0]

            setattr(self, singular, resource(self, content=content, single=True))
            plural = f"{singular}s"
            setattr(self, plural, resource(self, content=content))

    def _create_headers(self, api_version=None):
        """
        Create the ghost authentication header

        Args:
            api_version (string): for which API version to create a token

        Returns:
            dict: Authorization header
        """
        headers = {}

        token = self._create_token(api_version)
        if token:
            headers["Authorization"] = f"Ghost {token}"

        headers["accept-version"] = api_version

        return headers

    def _check_keys(self):
        raise NotImplementedError(
            "Implement _check_keys when inheriting from this class."
        )

    def _create_token(self, api_version: str = None):
        """
        Create a JWT token if an admin API key was supplied.

        Args:
            api_version (str): override the client's api version

        Returns:
            str: auth token for ghost
        """
        if not self._check_keys():
            raise ValueError("Please enter valid auth keys!")

        if self.adminAPIKey:
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

    def resource(self, name, single=False):
        """
        Create an anonymous resource on the fly - to be used if there is no class available for some resource,
        that does have an endpoint in ghost.
        """
        raise NotImplementedError("Implement these in the inherited classes.")

    def _handle_errors(self, response: requests.Response):
        """
        Raise custom ghost exceptions on different types of errors,
        instead of just returning the response JSON
        """
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

    def DELETE(self, *_, **__):
        raise NotImplementedError("Implement this in the GhostAdmin class")

    def PUT(self, *_, **__):
        raise NotImplementedError("Implement this in the GhostAdmin class")

    def POST(self, *_, **__):
        raise NotImplementedError("Implement this in the GhostAdmin class")

    def _interact(
        self,
        verb: str,
        endpoint: str,
        params: dict = None,
        files: dict = None,
        json: dict = None,
        api_version: str = None,
    ):
        """
        Wrapper for requests that deals with Ghost API specifics and handles the response.

        Args:
          verb (str): The HTTP verb to use.
          endpoint: The endpoint you want to access.
            For example, if you want to access the posts endpoint, you would pass in "posts".
          params (dict): A dictionary of query parameters to be appended to the URL.
          files (dict): a dictionary of files to upload.
            E.g. {"file": (name, file, mime_type)}
          json (dict): The JSON data to send in the body of the request.
          api_version (str): The version of the API you want to use.

        Returns:
          requests.Response: A response object.
        """
        if api_version is None:
            # default
            api_version = self.api_version
            headers = self.headers
        else:
            # custom api version, new headers:
            headers = self._create_headers(api_version)

        verb = verb.lower()

        # url + /ghost/api/ + /v3/admin/ + ...
        # in v5, api version is no longer sent in the URL

        url = (
            yarl.URL(self.url)
            / "ghost/api"
            / (api_version if api_version != "v5" else "")
            / endpoint
        )

        if endpoint.startswith("content") or not self.adminAPIKey:
            # yarl URL() % dict() encodes and adds query parameters as e.g. ?key=value
            url %= {"key": self.contentAPIKey}

        error_count = 0

        url = str(url)
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


@dataclass
class GhostContent(GhostClient):
    def _check_keys(self):
        """
        This Client only requires a Content Key
        """
        return self.contentAPIKey

    def __post_init__(self):
        """
        Set up the different Resources
        """

        self.headers = {}

        # resources:
        self._setup_resources_on_self(
            [
                PostResource,
                PageResource,
                AuthorResource,
                TagResource,
                ImageResource,
                ThemeResource,
                MemberResource,
                UserResource,
            ],
            content=True,
        )

        # there's only one site/one settings:
        self.site = SiteResource(self, single=True, content=True)
        self.settings = SettingsResource(self, single=True, content=True)

    def DELETE(self, *_, **__):
        raise GhostWrongApiError("DELETE is not allowed for the content API!")

    def PUT(self, *_, **__):
        raise GhostWrongApiError("PUT is not allowed for the content API!")

    def POST(self, *_, **__):
        raise GhostWrongApiError("POST is not allowed for the content API!")

    def resource(self, name, single=False):
        """
        Create an anonymous resource on the fly - to be used if there is no class available for some resource,
        that does have an endpoint in ghost.
        """

        class _Resource(GhostContentResource):
            # Temporary Resource
            resource = name

        return _Resource(self, single=single)


@dataclass
class GhostAdmin(GhostClient):
    url: str
    headers: dict = field(init=False, repr=False)
    contentAPIKey: str = field(repr=False)
    adminAPIKey: str = field(repr=False)
    api_version: str = "v4"  # or v3 or v5

    _session = requests.Session()

    def _check_keys(self):
        """
        The admin API requires both an admin api key and a content api key
        """
        return self.adminAPIKey and self.contentAPIKey

    def __post_init__(self):
        """
        Setup the JWT Authentication headers and the different Resources
        """

        self.headers = self._create_headers()

        # resources:
        self._setup_resources_on_self(
            [
                PostResource,
                PageResource,
                AuthorResource,
                TagResource,
                ImageResource,
                ThemeResource,
                MemberResource,
                UserResource,
            ],
            content=False,
        )

        # there's only one site/one settings:
        self.site = SiteResource(self, single=True)
        self.settings = SettingsResource(self, single=True)

    def POST(self, url, params=None, json=None, files=None):
        """
        Pass to self.interact with POST

        Returns:
            dict: response data
        """
        resp = self._interact("post", url, params=params, json=json, files=files)

        if not resp.ok:
            self._handle_errors(resp)

        return resp.json()

    def PUT(self, url, params=None, json=None, files=None):
        """
        Pass to self.interact with PUT

        Returns:
            dict: response data
        """
        resp = self._interact("put", url, params=params, json=json)

        if not resp.ok:
            self._handle_errors(resp)

        return resp.json()

    def DELETE(self, url, params=None):
        """
        Pass to self.interact with DELETE

        Returns:
            bool: if the status code is right
        """
        return self._interact("delete", url, params=params).status_code == 204

    def resource(self, name, single=False):
        """
        Create an anonymous resource on the fly - to be used if there is no class available for some resource,
        that does have an endpoint in ghost.
        """

        class _Resource(GhostAdminResource):
            # Temporary Resource
            resource = name

        return _Resource(self, single=single)
