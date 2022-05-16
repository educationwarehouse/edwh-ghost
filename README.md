# EDWH Ghost Client

This Client is compatible with v3 and v4 of the Ghost CMS [Admin](https://ghost.org/docs/admin-api) and [Content](https://ghost.org/docs/content-api/) API's.

### Installation
```bash
pip install edwh-ghost
```

### Usage

The `GhostAdmin` class can be instantiated as follows:
```python
from ghost import GhostAdmin
from dotenv import dotenv_values
config = dotenv_values(".env")

# .env can be used, but config values can also be simply hardcoded
ga = GhostAdmin(
    config["GHOST_SITE"],
    adminAPIKey=config["GHOST_ADMIN_KEY"],
    contentAPIKey=config["GHOST_CONTENT_KEY"],
    api_version="v4",  # works like a train
)
print(ga.site())
```

If no admin API key is available, the `GhostContent` class can be used, which has read-only access to public endpoints.

After creating a `GhostClient` instance, the different Resources can be used:
```python
from ghost.resources import *

posts: PostResource = ga.posts

# READ
multiple = posts(limit=5) # Ghost Result Set
# alias for
posts.get(limit=5)  # Ghost Result Set

some_post = posts.get("some_id")  # Ghost Result 

for post in posts.paginate():
    # iterate without limit
    print(post) # Ghost Result

# UPDATE
some_post.update({...}) # response dict  
# alias:
posts.update("some_id", {...}) # response dict  
# bulk:
multiple.update({...}) # response dict 


# DELETE
some_post.delete() # bool of success
# alias:
posts.delete("some_id") # bool of success
# bulk:
multiple.delete() # list of bools of success

# CREATE
# one:
posts.create(title="...", etc="...") # response dict
# bulk:
posts.create({...}, {...}) # list of response dicts

# some resources are read only:
authors: AuthorResource = ga.authors

authors()  # Ghost Result Set

authors.delete()  # error
```