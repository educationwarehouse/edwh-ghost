# EDWH Ghost Client

This Client is compatible with v3 and v4 of the Ghost CMS [Admin](https://ghost.org/docs/admin-api) and [Content](https://ghost.org/docs/content-api/) API's.

### Usage
```bash
pip install edwh-ghost
```

```python
# see also `demo` in ghost.py
from ghost import GhostAdmin
ga = GhostAdmin(
    "https://some.domain.tld",
    adminAPIKey=".....",
    contentAPIKey="...",
)
print(ga.getSite())
```
