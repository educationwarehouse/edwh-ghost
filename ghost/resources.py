import abc
import json
from dataclasses import field, dataclass
from json import JSONDecodeError
from pathlib import Path
from pprint import pprint

import jwt
import requests
import time
import sys
import shutil

from datetime import datetime as dt
from io import BytesIO

from typing import BinaryIO, Iterable

# fixme: from .exceptions
from exceptions import GhostUnknownException, GhostResponseException, GhostJSONException, GhostResourceNotFoundException

MAX_ERROR_LIMIT = 3


def is_iterable(value):
    """
    "If the value is iterable and not a string, return True."

    The first part of the function checks if the value is iterable. The second part checks if the value is not a string

    Args:
      value: The value to check.

    Returns:
      A boolean value.
    """
    return isinstance(value, Iterable) and not isinstance(value, str)


class GhostResult:
    def __init__(self, d, resource):
        self.__data__ = d
        self.type = resource

    def __getattr__(self, item):
        return self.__data__.get(item)

    def __repr__(self):
        return f"<{self.type}: {self.slug}>"


class GhostResultSet:
    def __init__(self, lst, resource):
        self.__list__ = [GhostResult(_, resource) for _ in lst]

    def __repr__(self):
        return f"[{', '.join([repr(_) for _ in self.__list__])}]"


class GhostResource(abc.ABC):
    single: bool

    @property
    def resource(self):
        raise NotImplementedError("Please choose a resource")

    @property
    def api(self):
        raise NotImplementedError("Please choose an api")

    def __init__(self, ghost_admin, single=False):
        self.ga = ghost_admin
        self.single = single

    def __call__(self, id=None, /, **filters):
        if id is not None:
            return self._get_by_id(id)
        elif 'slug' in filters and len(filters) == 1:
            return self._get_by_slug(filters['slug'])
        else:
            return self._get_by_filters(**filters)

    def _get_by_id(self, id):
        params = {"formats": "html,mobiledoc"}
        return self._get(id, params)

    def _get_by_slug(self, slug):
        return self._get_by_id(f"slug/{slug}")

    def _list_join(self, value, paren='square'):
        """
        It takes a list of strings, joins them with commas, and then wraps them in square or round brackets

        Args:
          value (Iterable): the list of values to join
          paren (string|False): the type of parenthesis to use. Defaults to square

        Returns:
          A joined string of values
        """
        value = ','.join(value)
        if not paren:
            return value
        elif paren == 'square':
            return f'[{value}]'
        elif paren == 'round':
            return f'({value})'
        else:
            # todo: other?
            raise NotImplementedError(f"Parentheses type '{paren}' not supported.")

    def _filters_to_ghost(self, filters):
        """
        It takes a dictionary of filters and returns a string of filters in the format that Ghost expects

        Args:
          filters (dict): A dictionary of filters to apply to the search.

        Returns:
          A string of filters
        """
        ghost_filters = []

        for key, value in filters.items():
            if is_iterable(value):
                value = self._list_join(value)

            ghost_filters.append(
                f'{key}:{value}'
            )

        return '+'.join(ghost_filters)

    def _get_by_filters(self, limit=None, page=None, order=None, fields=None, **filter):
        args = self._create_args(locals())
        args["formats"] = "html,mobiledoc"

        return self._get(params=args)

    def _create_args(self, d):
        # todo: use Operators (greater than etc), combinations (+ for AND), etc.
        d.pop('self')
        args = {}

        for key, value in d.items():
            if value is None:
                continue
            if isinstance(value, dict):
                value = self._filters_to_ghost(value)
            elif is_iterable(value):
                value = self._list_join(value, paren=False)

            args[key] = value

        return args

    def _get(self, path="", params=None):
        if params is None:
            params = {}

        data = self.ga.GET(f"{self.api}/{self.resource}/{path}", params=params).get(self.resource)

        if not data:
            raise GhostResourceNotFoundException(200, "Resource Not Found", id)

        if self.single:
            return GhostResult(data[0], self.resource)
        else:
            return GhostResultSet(data, self.resource)


class PostResource(GhostResource):
    resource = 'posts'
    api = 'admin'


class PageResource(GhostResource):
    resource = 'pages'
    api = 'admin'


class TagResource(GhostResource):
    resource = 'tags'
    api = 'admin'


class AuthorResource(GhostResource):
    resource = 'authors'
    api = 'content'


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

        self.post = PostResource(self, single=True)
        self.page = PageResource(self, single=True)
        self.author = AuthorResource(self, single=True)
        self.tag = TagResource(self, single=True)

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
                    print(
                        {
                            "endpoint": url,
                            "method": verb,
                            "code": resp.status_code,
                            "message": resp.text,
                        },
                        file=sys.stderr,
                    )
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
                    exception=data)

            main_error = err[0]
            raise GhostResponseException(response.status_code,
                                         main_error['type'],
                                         main_error['message'],
                                         exception=err)

        except JSONDecodeError as e:
            raise GhostJSONException(response.status_code,
                                     error_message="JSON Parsing Failed",
                                     exception=e)

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
        return self._interact("post", url, params=params, json=json, files=files)

    def PUT(self, url, params=None, json=None, files=None):
        """
        Pass to self.interact with PUT
        """
        return self._interact("put", url, params=params, json=json)

    def DELETE(self, url, params=None):
        """
        Pass to self.interact with DELETE
        """
        return self._interact("delete", url, params=params)

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


def main():
    ga = GhostAdmin(

    )

    pprint([
        # ga.post('627532af413f5e000107448b'),
        ga.post(slug='other'),
        # ga.posts(limit=3, tags=['getting-started', 'hotspot'], fields=['title', 'slug']),
        ga.authors(limit=2)
    ])


if __name__ == '__main__':
    main()
