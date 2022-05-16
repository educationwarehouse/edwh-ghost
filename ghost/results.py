import hashlib
import json

# noinspection PyUnreachableCode
if False:
    # annotation only
    from .abs_resources import GhostResource


def dict_hash(dictionary):
    """MD5 hash of a dictionary."""
    dhash = hashlib.md5()
    # We need to sort arguments so {'a': 1, 'b': 2} is
    # the same as {'b': 2, 'a': 1}
    encoded = json.dumps(dictionary, sort_keys=True).encode()
    dhash.update(encoded)
    return dhash.hexdigest()


class GhostResult:
    def __init__(self, d, resource):
        self.__data__ = d
        self._resource: GhostResource = resource

    def __getitem__(self, item):
        # result[item]
        return self.__data__.get(item)

    def __getattr__(self, item):
        # result.item
        return self.__getitem__(item)

    def __repr__(self):
        # repr(result)
        return f"<{self._resource.resource}: {self.slug}>"

    def as_dict(self):
        # result.as_dict()
        return self.__data__

    def delete(self):
        return self._resource.delete(self.id)

    def update(self, **data):
        return self._resource.update(self.id, data, self)

    def __eq__(self, other):
        return dict_hash(self.__data__) == dict_hash(other.__data__)


class GhostResultSet:
    def __init__(self, lst, resource, meta):
        self.__list__ = [GhostResult(_, resource) for _ in lst]
        self._resource = resource
        self._meta = meta

    def __repr__(self):
        return f"[{', '.join([repr(_) for _ in self.__list__])}]"

    def __iter__(self):
        for _ in self.__list__:
            yield _

    def __len__(self):
        return len(self.__list__)

    def __getitem__(self, idx):
        return self.__list__[idx]

    def as_dict(self):
        return {_["id"]: _.as_dict() for _ in self.__list__}

    def as_list(self):
        return [_.as_dict() for _ in self.__list__]

    def delete(self):
        return [i.delete() for i in self.__list__]

    def update(self, **data):
        return [i.update(**data) for i in self.__list__]

    # todo: paginate .next()
