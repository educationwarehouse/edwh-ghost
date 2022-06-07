from __future__ import annotations  # allow type hint without actual import
import abc
import json
from abc import ABC
from typing import Iterable

# noinspection PyUnreachableCode
if False:
    # prevent circular import
    from .client import GhostClient

from .exceptions import GhostResourceNotFoundException
from .results import GhostResult, GhostResultSet


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


class GhostResource(abc.ABC):
    single: bool
    content: bool
    ga: GhostClient

    def __repr__(self):
        return f"<GhostResource {self.resource}>"

    @property
    def resource(self):
        raise NotImplementedError("Please choose a resource")

    @property
    def api(self):
        raise NotImplementedError("Please choose an api")

    def __init__(self, ghost_admin: GhostClient, single=False, content=False):
        self.ga = ghost_admin
        self.single = single
        self.content = content

    # def __call__(self, id: str = None, /, **filters): # <- Python 3.8+
    def __call__(self, id: str = None, **filters):
        """
        Magic method to make it possible to call something like ghost.pages(tag='sometag') or ghost.page('some id')
        instead of ghots.pages.get(tag='sometag')
        """

        return self.get(id, **filters)

    def _list_join(self, value: list, paren: str = "square"):
        """
        Join a list and wrap it in different parentheses
        """

        value = ",".join(value)
        if not paren:
            return value
        elif paren == "square":
            return f"[{value}]"
        elif paren == "round":
            return f"({value})"
        else:
            # todo: other?
            raise NotImplementedError(f"Parentheses type '{paren}' not supported.")

    def _filters_to_ghost(self, filters: dict):
        """
        Ghost requires params to be supplied as strings,
        but for developer experience it is much nicer to work with e.g. lists.
        This method converts this for ease of use.


        Returns:
            str: filters joined by +
        """
        ghost_filters = []

        for key, value in filters.items():
            if is_iterable(value):
                value = self._list_join(value)

            ghost_filters.append(f"{key}:{value}")

        return "+".join(ghost_filters)

    def _create_url(self, path: Iterable):
        """
        Build a valid Ghost API endpoint URL.

        Args:
            path (Iterable): parts of path to combine

        Returns:
            str: URL path, joined by /
        """
        api = "content" if self.content else self.api
        return "/".join([api, self.resource, *path])

    def GET(self, *path, **args):
        """
        Perform a GET request
        (forwarded to the Client passed to this class)

        Returns:
            GhostResult | GhostResultSet: depending on the request
        """
        url = self._create_url(path)
        return self.ga.GET(url, **args)

    def POST(self, *path, **args):
        """
        Perform a POST request
        (forwarded to the Client passed to this class)

        Returns:
            dict: json response
        """
        url = self._create_url(path)
        return self.ga.POST(url, **args)

    def PUT(self, *path, **args):
        """
        Perform a PUT request
        (forwarded to the Client passed to this class)

        Returns:
            dict: json reponse
        """
        url = self._create_url(path)
        return self.ga.PUT(url, **args)

    def DELETE(self, *path, **args):
        """
        Perform a DELETE request
        (forwarded to the Client passed to this class)

        Returns:
            bool: if successfull
        """
        url = self._create_url(path)
        return self.ga.DELETE(url, **args)

    def _create_args(self, d: dict):
        """
        Turn arguments such as fields, page, order, filters etc. into the format Ghost expects
        """

        # todo: use Operators (greater than etc), combinations (+ for AND), etc.
        d.pop("self")  # needed since locals() is passed to this method
        args = {}

        for key, value in d.items():
            if value is None:
                continue
            if isinstance(value, dict):
                value = self._filters_to_ghost(value)
            elif is_iterable(value):
                value = self._list_join(value, paren="")

            args[key] = value

        return args

    def _get(self, path: str = "", params: dict = None, single: bool = None):
        """
        GET some resource and handle the result(s)

        Args:
          path (str): The path to the resource you want to get.
          params (dict): A dictionary of query parameters to be passed to the API.
          single (bool): If True, a GhostResult will be returned, even when the Resource is not single.
          Otherwise, a GhostResultSet will be returned.

        Returns:
          GhostResult | GhostResultSet
        """

        if params is None:
            params = {}

        resp = self.GET(path, params=params)
        data = resp.get(self.resource)

        if not data and self.single:
            raise GhostResourceNotFoundException(200, "Resource Not Found", path)

        if self.single or single:
            return GhostResult(data[0] if isinstance(data, list) else data, self)
        else:
            return GhostResultSet(
                data,
                self,
                meta=resp["meta"],
                request={
                    "path": path,
                    "params": params,
                    "single": single,
                },
            )

    def paginate(self, *, per: int = 25, **filters):
        """
        Generator that yields all the data for this resource

        Args:
          per (int): The number of results to return per page. Defaults to 25
          filters: modifiers passed to the GET request

        Yields:
            GhostResult: items matching the supplied filters
        """

        data = True
        page = 1
        filters["limit"] = per

        while data:
            filters["page"] = page
            try:
                data = self.get(**filters)
                for d in data:
                    yield d
            except GhostResourceNotFoundException:
                break
            page += 1

    def _get_by_id(self, id: str, **_params):
        """
        Get a specific instance of this resource, by ID.

        Args:
          id (str): The id of the item to retrieve.
          params: modifiers such as 'fields' to limit which columns to get

        Returns:
          GhostResult: item with id
        """

        params = {"formats": "html,mobiledoc", **_params}
        return self._get(id, params, single=True)

    def _get_by_filters(
        self,
        limit: int = None,
        page: int = None,
        order: str = None,
        fields: list = None,
        **filter,
    ):
        """
        Get resource items matching filter

        Args:
          limit (int): The number of results to return.
          page (int): The page number of the results to return.
          order (str): The order in which to return the posts.
          fields (list): A list of fields to include in the response.
          filter: a dictionary of key-value pairs to filter by (e.g. author, slug, etc.)

        Returns:
          GhostResultSet:
        """
        args = self._create_args(locals())
        args["formats"] = "html,mobiledoc"

        return self._get(params=args)

    # def get(self, id: str = None, /, **filters): # <- Python 3.8+
    def get(self, id: str = None, **filters):
        """
        Either get

        Args:
            id (str): if the ID of the item is known
            filters: parameters to filter data on.
            See https://ghost.org/docs/admin-api/#parameters and https://ghost.org/docs/content-api/#parameters
            for more info

        Returns:
            GhostResult | GhostResultSet: depending on if 'single' is used.
        """

        if id is not None:
            return self._get_by_id(id)
        elif "slug" in filters and len(filters) == 1:
            return self._get_by_id(f"slug/{filters['slug']}")
        else:
            if "fields" in filters:
                if "id" not in filters["fields"]:
                    filters["fields"].append("id")

                if "updated_at" not in filters["fields"]:
                    filters["fields"].append("updated_at")

            return self._get_by_filters(**filters)

    def delete(self, *_, **__):
        raise NotImplementedError("Implement this in the Admin Resources")

    def update(self, *_, **__):
        raise NotImplementedError("Implement this in the Admin Resources")

    def create(self, *_, **__):
        raise NotImplementedError("Implement this in the Admin Resources")


class GhostAdminResource(GhostResource, ABC):
    api = "admin"

    def __md_card(self, md: str, idx: int = 0):
        """
        Generate a mobiledoc card for markdown

        Args:
            md (str): markdown text
            idx (int): index, used to give cards a unique cardName

        Returns:
            list: mobiledoc formatted card
        """
        return [
            "markdown",
            {"cardName": f"markdown-{idx}", "markdown": md},
        ]

    def _transform_markdown(self, item: dict):
        """
        Allow developers to use markdown with mobiledoc more easily.
        Currently not implemented as only one block of markdown shows up in Ghost instead of everything.

        Args:
            item (dict): the resource to be created. The value of markdown in item can be a string or a list of strings.

        Returns:
            None: this method only edits item
        """
        if item.get("markdown"):
            raise NotImplementedError(
                "Creating posts with markdown is currently not yet supported."
            )
            md = item["markdown"]

            if is_iterable(md):
                cards = [self.__md_card(_, i) for i, _ in enumerate(md)]
            else:
                cards = [self.__md_card(md)]

            item["mobiledoc"] = json.dumps(
                {
                    "version": "0.3.1",
                    "markups": [],
                    "atoms": [],
                    "cards": cards,
                    "sections": [[10, 0]],
                }
            )

            del item["markdown"]

    def _create_multiple(self, items: list):
        raise NotImplementedError("Can only create one item at a time!")
        data = {self.resource: items}

        return self.POST(json=data)

    def _create_one(self, item: dict):
        """
        Wrapper to create a new item of this resource
        """

        self._transform_markdown(item)

        data = {self.resource: [item]}

        if item.get("html"):
            params = {"source": "html"}
        # elif item.get('mobiledoc'):
        #     params = {"source": "mobiledoc"}
        else:
            params = {}

        return self.POST(params=params, json=data)

    def create(self, *a, **kw):
        """
        Create one or more new items.
        One item is created if kwargs are used:
        e.g. ghost.posts.create(title="something")

        Multiple items are created if args is used:
        e.g. ghost.posts.create({...}, {...})


        """

        if a and kw:
            raise ValueError(
                "Please use either only arguments or only keyword arguments."
            )
        elif a:
            # return self._create_multiple(a)
            return [self._create_one(_) for _ in a]
        else:  # kw
            # return self._create_multiple([kw])
            return self._create_one(kw)

    def _delete_by_id(self, id: str):
        """
        Delete a specific item by ID
        """
        return self.DELETE(id)

    def _delete_by_filters(self, filters):
        """
        Find all items matching filters and delete these

        Returns:
            list[bool]: success of each delete
        """
        try:
            if not filters.get("limit"):
                filters["limit"] = "all"

            ids = self._get_by_filters(**filters)
            if not ids:
                return []

            return [self._delete_by_id(_["id"]) for _ in ids]
        except GhostResourceNotFoundException:
            return []

    # def delete(self, id=None, /, **filters):  # <- Python 3.8+
    def delete(self, id=None, **filters):
        """
        Delete either one item if 'id' is supplied or all items matching filters
        """

        if id is not None:
            return self._delete_by_id(id)
        else:
            filters["fields"] = "id"  # not more is needed for delete
            return self._delete_by_filters(filters=filters)

    def _update_by_id(self, id: str, data: dict, old=None):
        """
        PUT new data for ID

        Args:
            id (str): item to update
            data (dict): data to update
            old (dict|GhostResult): required for the old updated_at

        Returns:
            dict: response data
        """
        if old is None:
            old = self._get_by_id(id, fields=["updated_at"])

        data["updated_at"] = old["updated_at"]

        return self.PUT(id, json={self.resource: [data]})

    def _update_by_filters(self, data: dict, filters: dict):
        """
        For each item matching filters, update its data

        Returns:
            list[dict]: result of each PUT
        """

        try:
            if not filters.get("limit"):
                filters["limit"] = "all"

            ids = self._get_by_filters(**filters, fields=["id", "updated_at"])
            return [self._update_by_id(old["id"], data, old) for old in ids]
        except GhostResourceNotFoundException:
            return []

    # def update(self, id: str = None, data: dict = None, old=None, /, **filters): # <- Python 3.8+
    def update(self, id: str = None, data: dict = None, old=None, **filters):
        """
        Update either one item if 'id' is supplied or all items matching filters.

        Args:
            id (str): one item to update
            data (dict): new data
            old (dict|GhostResult): the old updated at is required to update a post.
              If old is not supplied, it will be GET-requested before updating.
            filters: to find items

        Returns:
            dict | list[dict]: response(s) from Ghost
        """

        if data is None:
            raise ValueError("Please include new and old values in data!")

        if id is not None:
            return self._update_by_id(id, data=data, old=old)
        else:
            return self._update_by_filters(data=data, filters=filters)


class GhostContentResource(GhostResource, ABC):
    api = "content"
