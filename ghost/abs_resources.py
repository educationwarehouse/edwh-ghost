import abc
import json
from pprint import pprint
from typing import Iterable
from datetime import datetime

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

    def __repr__(self):
        return f"<GhostResource {self.resource}>"

    @property
    def resource(self):
        raise NotImplementedError("Please choose a resource")

    @property
    def api(self):
        raise NotImplementedError("Please choose an api")

    def __init__(self, ghost_admin, single=False):
        self.ga = ghost_admin
        self.single = single  # fixme: remove

    def __call__(self, id=None, /, **filters):
        return self.get(id, **filters)

    def _list_join(self, value, paren="square"):
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

    def _filters_to_ghost(self, filters):
        ghost_filters = []

        for key, value in filters.items():
            if is_iterable(value):
                value = self._list_join(value)

            ghost_filters.append(f"{key}:{value}")

        return "+".join(ghost_filters)

    def _create_url(self, path):
        return "/".join([self.api, self.resource, *path])

    def GET(self, *path, **args):
        url = self._create_url(path)
        return self.ga.GET(url, **args)

    def POST(self, *path, **args):
        url = self._create_url(path)
        return self.ga.POST(url, **args)

    def PUT(self, *path, **args):
        url = self._create_url(path)
        return self.ga.PUT(url, **args)

    def DELETE(self, *path, **args):
        url = self._create_url(path)
        return self.ga.DELETE(url, **args)

    def _create_args(self, d):
        # todo: use Operators (greater than etc), combinations (+ for AND), etc.
        d.pop("self")
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

        resp = self.GET(path, params=params)
        data = resp.get(self.resource)

        if not data and self.single:
            raise GhostResourceNotFoundException(200, "Resource Not Found", path)

        if self.single:
            return GhostResult(data[0] if isinstance(data, list) else data, self)
        else:
            return GhostResultSet(data, self, meta=resp["meta"])

    def paginate(self, *, per=25, **filters):
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

    def _get_by_id(self, id, **_params):
        params = {"formats": "html,mobiledoc", **_params}
        return self._get(id, params)

    def _get_by_filters(self, limit=None, page=None, order=None, fields=None, **filter):
        args = self._create_args(locals())
        args["formats"] = "html,mobiledoc"

        return self._get(params=args)

    def get(self, id=None, /, **filters):
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


class GhostAdminResource(GhostResource):
    api = "admin"

    def __md_card(self, md, idx=0):
        return [
            "markdown",
            {"cardName": f"markdown-{idx}", "markdown": md},
        ]

    def _transform_markdown(self, item):
        if item.get("markdown"):
            raise NotImplementedError("Creating posts with markdown is currently not yet supported.")
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

    def _create_multiple(self, items):
        raise NotImplementedError("Can only create one item at a time!")
        data = {self.resource: items}

        return self.POST(json=data)

    def _create_one(self, item):

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

    def _delete_by_id(self, id):
        return self.DELETE(id)

    def _delete_by_filters(self, filters):
        try:
            ids = self._get_by_filters(**filters)
            if not ids:
                return []

            return [self._delete_by_id(_["id"]) for _ in ids]
        except GhostResourceNotFoundException:
            return []

    def delete(self, id=None, /, **filters):
        if id is not None:
            return self._delete_by_id(id)
        else:
            filters["fields"] = "id"  # not more is needed for delete
            return self._delete_by_filters(filters=filters)

    def _update_by_id(self, id, data):
        return self.PUT(id, json={self.resource: [data]})

    def _update_by_filters(self, data, filters):
        try:
            ids = self._get_by_filters(**filters)
            return [self._update_by_id(_["id"], data) for _ in ids]
        except GhostResourceNotFoundException:
            return []

    def update(self, id=None, data=None, old=None, /, **filters):
        if data is None:
            raise ValueError("Please include new and old values in data!")

        if old is None:
            old = self._get_by_id(id, fields=["updated_at"])
            if not self.single:
                old = old[0]

        data["updated_at"] = old.updated_at

        if id is not None:
            return self._update_by_id(id, data=data)
        else:
            return self._update_by_filters(data=data, filters=filters)


class GhostContentResource(GhostResource):
    api = "content"
