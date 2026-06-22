---
name: yp-package-info
description: >-
  PyPI package-info tooling for the yp package. Use this skill to fetch live
  details about PyPI projects through yp's mapping interface: full project JSON,
  a tidy digest (version, summary, license, home page, declared requirements
  (requires_dist), last upload size/time), the latest version of one or many
  packages, and a PyPI user's list of projects. Trigger when the user asks "what
  version is X on PyPI", "get info/metadata for package X", "what's the latest
  release of these packages", "when was X last updated", "summary/license/home
  page of X", "list all projects by PyPI user Y", or wants to bulk-download
  package metadata. The values come live from the PyPI JSON API. Assumes the
  package already EXISTS: to check whether a name is FREE to publish use
  yp-name-availability; for an installed package's resolved dependency tree or
  version conflicts use yp-dependencies.
metadata:
  audience: users
---

# Look up PyPI package info with yp

`yp.Pypi` is a read-only `Mapping` over PyPI: keys are project names, values are
the project's live info from the PyPI JSON API
(`https://pypi.org/pypi/<name>/json`). This skill covers fetching that info and
the helpers that distill it.

## Full project info

```python
from yp import Pypi

p = Pypi()
info = p["numpy"]                 # live request to the PyPI JSON API
list(info)
# ['info', 'last_serial', 'releases', 'urls', 'vulnerabilities']
info["info"]["version"]           # e.g. '2.1.3'
```

`p[name]` fetches **live** (it is not the cached name list — that's only for
membership; see **yp-name-cache**). **Any** valid PyPI name can be fetched, even
one not in the particular instance, unless you pass `strict_getitem=True`:

```python
Pypi(strict_getitem=True)["not-in-this-instance"]   # raises KeyError
```

## Tidy digest of the important fields

`extract_main_info` pulls the fields people usually want out of the big nested
dict:

```python
from yp import Pypi, extract_main_info

digest = extract_main_info(Pypi()["numpy"])
# keys: version, summary, home_page, project_url, license, description,
#       requires_dist, and (from the latest release file) size, upload_time_iso_8601
```

Compose it onto the mapping so indexing returns the digest directly:

```python
p = Pypi(info_extractor=extract_main_info)
p["pandas"]["summary"]            # digest, not the full payload
```

## Latest version(s)

For one or many packages at once:

```python
from yp import recent_versions

recent_versions(["numpy", "pandas", "dol"])
# {'numpy': '2.1.3', 'pandas': '2.2.3', 'dol': '0.3.x'}
```

`recent_versions` is resilient: a name it can't fetch maps to `None` rather than
raising. Pass `egress=...` to post-process the result dict.

## Last-upload time

```python
from yp import latest_release_upload_datetime

latest_release_upload_datetime(Pypi()["numpy"]["releases"])  # '2024-...T...'
```

Pass it the `releases` sub-dict. It picks the highest version (PEP 440 ordering)
and returns the `upload_time` of that release's first file, or `None` if empty.

## A PyPI user's projects

```python
from yp import Pypi
up = Pypi(user="thorwhalen1")     # only that user's projects as keys
list(up)

from yp import slurp_user_projects_info
slurp_user_projects_info("thorwhalen1")
# [{'name':..., 'description':..., 'date':..., 'href':...}, ...]
```

**Gotcha:** the user page is JavaScript-rendered, so this path uses **Selenium**
(`selenium` + `webdriver-manager` + a Chrome driver) and is much slower than the
JSON API. Results are cached under the app config dir; pass `refresh=True` to
`slurp_user_projects_info` to re-fetch.

## Bulk-download metadata to a store

```python
from yp import download_packages_info
download_packages_info(["numpy", "pandas"], "/path/to/json_store")
# save_store may be a path (becomes a dol.Jsons store) or any MutableMapping.
# package_names may be a list, a whitespace-separated string, or a path to a
# file with one name per line. Already-present keys are skipped (resumable).
```

Low-level single fetch: `from yp.base import info_of_pkg_from_web; info_of_pkg_from_web("numpy")`.

## Gotchas

- **Network required.** All of the above hit PyPI live. On a non-200 response
  the underlying fetch raises `requests.exceptions.RequestException` **and
  pickles the failing response to a temp file** — so a 404 (unknown package) is
  an exception, not an empty result. Wrap in `try/except` when probing names that
  may not exist, or use `recent_versions` (which swallows errors to `None`).
- The cached name index is **not** consulted for `p[name]`; it only powers
  membership/availability. To check existence cheaply, use **yp-name-cache**.

## Related

- **yp-name-cache** — fast offline existence/availability checks.
- **yp-name-availability** — find a *free* name for a new package.
- **yp-dependencies** — analyze an installed package's dependency tree.
