from __future__ import annotations
import hashlib
import json

# noinspection PyUnreachableCode
if False:
    # annotation only
    from .abs_resources import GhostResource


def dict_hash(dictionary: dict):
    """
    MD5 hash of a dictionary, used to compare dicts
    """
    dhash = hashlib.md5()
    # We need to sort arguments so {'a': 1, 'b': 2} is
    # the same as {'b': 2, 'a': 1}
    encoded = json.dumps(dictionary, sort_keys=True).encode()
    dhash.update(encoded)
    return dhash.hexdigest()


def is_admin_resource(obj):
    # GhostAdminResource cannot be imported globally due to circular referencing
    from .abs_resources import GhostAdminResource

    return isinstance(obj, GhostAdminResource)


class GhostResult:
    def __init__(self, d: dict, resource: GhostResource):
        self.__data__ = d
        self._resource: GhostResource = resource

    def __getitem__(self, item):
        """
        Allows to access the result as a dict (result[item])
        """
        return self.__data__.get(item)

    def __getattr__(self, item):
        """
        Allows to access the result as an object (result.item)
        """
        return self.__getitem__(item)

    def __repr__(self):
        """
        human-friendlier representation of the resource
        """
        return f"<{self._resource.resource}: {self.slug}>"

    def as_dict(self):
        """
        Get the Result's raw values as dict
        """
        return self.__data__

    def delete(self):
        """
        Delete this response's item
        """
        rs = self._resource
        if not is_admin_resource(rs):
            raise PermissionError("Please use the admin API to delete resources.")
        return rs.delete(self.id)

    def update(self, **data):
        """
        Update this response's item
        """
        rs = self._resource
        if not is_admin_resource(rs):
            raise PermissionError("Please use the admin API to update resources.")
        return rs.update(self.id, data, self)

    def __eq__(self, other):
        """
        Check if this result's data matches the other's
        """
        return dict_hash(self.__data__) == dict_hash(other.__data__)


class GhostResultSet:
    def __init__(self, lst, resource, meta):
        self.__list__ = [GhostResult(_, resource) for _ in lst]
        self._resource = resource
        self._meta = meta

    def __repr__(self):
        return f"[{', '.join([repr(_) for _ in self.__list__])}]"

    def __iter__(self):
        """
        Iterate the result list
        """
        for _ in self.__list__:
            yield _

    def __len__(self):
        return len(self.__list__)

    def __getitem__(self, idx):
        """
        Get an item by index (resultset[idx])
        """
        return self.__list__[idx]

    def as_dict(self):
        return {_["id"]: _.as_dict() for _ in self.__list__}

    def as_list(self):
        return [_.as_dict() for _ in self.__list__]

    def delete(self):
        """
        Delete all results in this set
        """
        return [i.delete() for i in self.__list__]

    def update(self, **data):
        """
        Update all results in this set
        """
        return [i.update(**data) for i in self.__list__]

    # todo: paginate .next()
