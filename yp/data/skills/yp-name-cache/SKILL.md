---
name: yp-name-cache
description: >-
  Cached PyPI name-index tooling for the yp package. Use this skill to maintain
  and understand yp's local snapshot of every PyPI project name: refresh it from
  pypi.org, learn where it is stored, how current it is, its normalization
  caveats, and how the fast offline membership primitive works. Trigger when the
  user wants to "refresh/update the PyPI package list", "rebuild the name cache",
  "how do I update yp's package names", "how current/fresh is the cached name
  list", "where does yp store the package names", or asks how yp's cached
  membership check works under the hood. For actually finding or deciding on an
  available name (brainstorm, filter, present free options) use
  yp-name-availability; this skill maintains and explains the underlying index.
metadata:
  audience: users
---

# Operate yp's cached PyPI name index

`yp` keeps a **local snapshot of every project name on PyPI** so it can answer
"does this name exist?" instantly and offline. This skill covers refreshing that
snapshot and using it as a fast availability primitive — and the caveats that
make a live check still necessary for a final answer.

## What the cache is

- Two files under the package's `data/` dir, written together on every refresh:
  - `pkg_list.p` — a pickled dict `{lowercased_name: pep503_stub}` (the
    authoritative store; ~800k+ entries).
  - `pkg_list.txt` — the same names, one per line (human-grep-friendly).
- At import, yp loads the dict into `yp.base.pkg_name_stub`. `Pypi()` (with no
  args) exposes its **keys** as the set of known names.
- The files live at `{rootdir}/data/pkg_list.p`, where `rootdir` defaults to the
  installed `yp/` package dir but can be redirected with the `YP_ROOTDIR`
  environment variable (see `yp/util.py`).

## Fast offline availability check (the efficient primitive)

```python
from yp import Pypi

p = Pypi()                 # builds a frozenset of all cached names — construct ONCE
"numpy" in p               # True  (known to PyPI as of last refresh)
p.is_available("numpy")    # False (== "numpy" not in p)
p.is_available("totally-made-up-xyz")  # True

# Bulk-filter candidate names (instant, no network):
candidates = ["foo", "bar", "baz"]
maybe_free = [c for c in candidates if p.is_available(c.lower())]
```

`is_available(name)` is just `name not in self` over the cached frozenset, so
each check is O(1). This is what the **yp-name-availability** workflow uses as
its cheap pre-filter before the authoritative live check.

## Refresh the cache

Refetch the full name list from `https://pypi.org/simple` and rewrite both files:

```python
from yp import Pypi
Pypi.with_fresh_cached_package_names()   # canonical; returns a fresh Pypi() over the new names
# Pypi.refresh_cached_package_names() is a backwards-compatibility alias for the same call
```

Or call the underlying function directly (prints before/after counts when
`verbose=True`):

```python
from yp.base import refresh_saved_pkg_name_stub
refresh_saved_pkg_name_stub(verbose=True)
# -> Updated the pkg_name_stub. Had 802360 items; now has 834011. ...
```

It downloads and parses the entire simple index (hundreds of thousands of
entries) — expect **tens of seconds**. Run it **regularly, but not too
regularly** (the README's guidance) — e.g. before a naming session if the cache
is stale. Refreshing mutates files inside the installed package; if `yp` is a
pip-installed (non-editable) copy, refresh under a writable `YP_ROOTDIR`
instead.

## Freshness & normalization caveats

The cache is a **point-in-time snapshot of raw names**, so treat a cached
"available" as *probably* free, not *certainly* free:

- **Staleness.** Names registered since the last refresh aren't in the cache, so
  they look available. Refresh, or confirm live.
- **No separator normalization.** PEP 503 makes `-`, `_`, `.` (and case)
  equivalent on PyPI, but the cache keys are stored as lowercased *raw* names.
  So `is_available("scikit_learn")`, `is_available("zope-interface")`, and
  `is_available("ruamel-yaml")` all return `True` even though `scikit-learn`,
  `zope.interface`, and `ruamel.yaml` are taken. A live JSON check normalizes
  server-side and catches these.

For a definitive answer, always confirm a survivor with a live check — the
**yp-name-availability** skill (JSON-API check) and **yp-package-info** skill
both cover this.

## Related

- **yp-name-availability** — the end-to-end "find a free name" workflow that uses
  this cache as its pre-filter.
- **yp-package-info** — fetch live details for any (taken) name.
