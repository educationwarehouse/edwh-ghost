# EDWH Ghost Client

This Client is compatible with v3 and v4 of the Ghost CMS [Admin](https://ghost.org/docs/admin-api) and [Content](https://ghost.org/docs/content-api/) API's.

### Usage
```bash
pip install edwh-ghost
```

```python
# see also `demo` in ghost.py
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
