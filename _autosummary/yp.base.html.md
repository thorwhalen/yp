# yp.base

Base functionality of yp

### Module Attributes

| [`PKG_LIST_FILENAME`](#yp.base.PKG_LIST_FILENAME)                | gzipped TSV of `pkg_name<TAB>pkg_stub` lines, where the tab and stub are omitted for the ~96% of projects whose stub equals their name.   |
|-----------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| [`pkg_names_package_filepath`](#yp.base.pkg_names_package_filepath)       | Seed copy shipped inside the installed distribution (read-only in most installs).                                                         |
| [`pkg_names_user_filepath`](#yp.base.pkg_names_user_filepath)          | Where `refresh_saved_pkg_name_stub` writes; takes precedence when it exists.                                                              |
| [`pkg_names_legacy_pickle_filepath`](#yp.base.pkg_names_legacy_pickle_filepath) | Pre-0.0.12 pickle cache, still read when no gzipped TSV is found.                                                                         |
| [`pkg_name_stub`](#yp.base.pkg_name_stub)                    | Mapping of every PyPI project name to its normalized stub.                                                                                |

### Functions

| `asis`(x)                                                                                    |                                                                                                  |
|----------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| [`get_updated_pkg_name_stub`](#yp.base.get_updated_pkg_name_stub)()                 | Get `{pkg_name: pkg_stub}` data from pypi                                                        |
| [`info_of_pkg_from_web`](#yp.base.info_of_pkg_from_web)(pkg_name)              | Get dict of information for a pkg_name                                                           |
| [`pypi_project_json`](#yp.base.pypi_project_json)(name, \*[, timeout])      | The JSON API document of PyPI project `name`.                                                    |
| [`refresh_saved_pkg_name_stub`](#yp.base.refresh_saved_pkg_name_stub)([verbose, ...]) | Update the `{pkg_name: pkg_stub}` stored data with a fresh call to `get_updated_pkg_name_stub`.  |
| [`return_sentinel_on_exception`](#yp.base.return_sentinel_on_exception)([...])         | Decorates a function so it will return a sentinel (default None) instead of raising an exception |
| [`slurp_user_projects_info`](#yp.base.slurp_user_projects_info)(user, \*[, ...])   | The list of projects that `user` owns or maintains on PyPI.                                      |
| [`xmlrpc_user_packages`](#yp.base.xmlrpc_user_packages)(user, \*[, timeout])   | `[(role, name), ...]` for the projects `user` owns or maintains on PyPI.                         |

### Classes

| [`CachedPkgNameStub`](#yp.base.CachedPkgNameStub)([mapping])                      | The `{pkg_name: pkg_stub}` mapping of every project on PyPI, loaded lazily.   |
|----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| [`Pypi`](#yp.base.Pypi)(\*[, info_extractor, proj_names, user, ...]) | Get a mapping of all of `pypi` projects.                                      |

### Exceptions

| [`MissingPackageNamesError`](#yp.base.MissingPackageNamesError)   | Raised when yp's cached list of PyPI project names cannot be found or read.   |
|-----------------------------------------------------------------------------|-------------------------------------------------------------------------------|

### *class* yp.base.CachedPkgNameStub(mapping=None)

Bases: [`Mapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)

The `{pkg_name: pkg_stub}` mapping of every project on PyPI, loaded lazily.

Reading the cache is deferred to first use, so `import yp` stays cheap and,
more importantly, never fails because of a missing data file: a missing cache
raises `MissingPackageNamesError` – with an actionable message – only if and
when the names are actually needed.

```pycon
>>> stub = CachedPkgNameStub()
>>> 'numpy' in stub
True
>>> stub['scikit-learn']
'scikit-learn'
>>> len(stub) > 100_000
True
```

#### *property* is_loaded

Whether the cache has been read yet.

#### *property* mapping

The underlying `dict`, read from cache on first access.

#### update_cache(mapping)

Replace the in-memory contents, keeping this object’s identity.

Rebinding the module global instead would leave every `from yp import
pkg_name_stub` pointing at the stale mapping.

### *exception* yp.base.MissingPackageNamesError

Bases: [`FileNotFoundError`](https://docs.python.org/3/builtins/exceptions.html#FileNotFoundError)

Raised when yp’s cached list of PyPI project names cannot be found or read.

Previously this condition was swallowed, which left `pkg_name_stub` undefined
and surfaced downstream as a bare `ImportError: cannot import name
'pkg_name_stub'` – with no hint as to the real cause.

### yp.base.PKG_LIST_FILENAME *= 'pkg_list.tsv.gz'*

gzipped TSV of `pkg_name<TAB>pkg_stub` lines, where the
tab and stub are omitted for the ~96% of projects whose stub equals their name.
That keeps the copy shipped in the distribution at ~4MB, against ~27MB for the
equivalent pickle, and avoids unpickling data at import time.

* **Type:**
  Canonical cache file

### *class* yp.base.Pypi(, info_extractor=None, proj_names=None, user=None, strict_getitem=False)

Bases: `KvReader`

Get a mapping of all of `pypi` projects.

```pycon
>>> p = Pypi()
```

The keys of this mapping are the project names. There are lots!

```pycon
>>> len(p)
405120
>>> 'numpy' in p and 'dol' in p
True
>>> 'no_way_this_is_a_package' in p
False
```

The values of the mapping are the corresponding project’s info, which is a
nested dict of good stuff.

```pycon
>>> info = p['numpy']
>>> {'info', 'last_serial', 'releases', 'urls'}.issubset(info)
True
```

#### TIP
To only get the info you want, you’ll

The project info is obtained, live, making requests to the
`https://pypi.python.org/pypi/{pkg_name}/json` API,
but the list of all project names is actually taken from a local file.
You should update that file regularly (but not TOO regularly!) to be in sync
with pypi.org. To do so, do this:

```pycon
>>> Pypi.refresh_cached_package_names()
```

If, on the other hand, you don’t want all projects of Pypi to be the collection
you’re working with, you can specify what `user` they should belong to:

```pycon
>>> p = Pypi(user='thorwhalen1')
>>> len(p)
131
```

You can also explicitly give `Pypi` a collection of projects you want to work
with:

```pycon
>>> p = Pypi(proj_names={'numpy', 'pandas', 'dol'})
>>> len(p)
3
```

You can do a lot more by simply using the tools of `dol` to change the mapping
you want to work with in all kinds of ways!

#### *static* live_is_available(pkg_name)

Check if a package name is available, live (directly on pypi, not a
cache). Returns `True` iff the name is free to register.

Uses the PyPI JSON API as the authoritative signal (404 => free,
200 => taken), which is more reliable than scraping the HTML project
page (that can return a soft 200 for non-existent names in some network
environments). PyPI normalizes names per PEP 503, so separator/case
variants of a taken name correctly report as unavailable.

#### pkg_has_pypi_page(pkg_name)

Return True iff `pkg_name` has a project on PyPI (i.e. the name is
taken). Uses the authoritative JSON API (see `_pkg_exists_on_pypi`).

#### *classmethod* refresh_cached_package_names()

Download and save a fresh copy of pypi’s package names

#### *classmethod* with_fresh_cached_package_names()

Download and save a fresh copy of pypi’s package names

### yp.base.get_updated_pkg_name_stub()

Get `{pkg_name: pkg_stub}` data from pypi

* **Returns:**
  `{pkg_name: pkg_stub, ...}` dict

### yp.base.info_of_pkg_from_web(pkg_name)

Get dict of information for a pkg_name

* **Parameters:**
  **pkg_name**
* **Returns:**

### yp.base.pkg_name_stub *= CachedPkgNameStub(<834011 names>)*

Mapping of every PyPI project name to its normalized stub. Loaded on first use.

### yp.base.pkg_names_legacy_pickle_filepath *= PosixPath('/home/runner/work/yp/yp/yp/data/pkg_list.p')*

Pre-0.0.12 pickle cache, still read when no gzipped TSV is found.

### yp.base.pkg_names_package_filepath *= PosixPath('/home/runner/work/yp/yp/yp/data/pkg_list.tsv.gz')*

Seed copy shipped inside the installed distribution (read-only in most installs).

### yp.base.pkg_names_user_filepath *= PosixPath('/home/runner/.config/yp/pkg_list.tsv.gz')*

Where `refresh_saved_pkg_name_stub` writes; takes precedence when it exists.

### yp.base.pypi_project_json(name, , timeout=30)

The JSON API document of PyPI project `name`.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yp.base.refresh_saved_pkg_name_stub(verbose=True, , save_to=None, write_text_file=True)

Update the `{pkg_name: pkg_stub}` stored data with a fresh call to
`get_updated_pkg_name_stub`.

The refreshed copy is written to the user’s app folder by default, not into the
installed package, which is read-only in many installs.

* **Parameters:**
  * **save_to** – Where to write the gzipped TSV cache.
    Defaults to `pkg_names_user_filepath`.
  * **write_text_file** – Also write a plain `pkg_list.txt` of the names, one per
    line, alongside `save_to`.

### yp.base.return_sentinel_on_exception(caught_exceptions=(<class 'Exception'>, ), sentinel=None)

Decorates a function so it will return a sentinel (default None) instead of
raising an exception

### yp.base.slurp_user_projects_info(user, \*, with_details=False, cache_results=True, refresh=False, user_packages=<function xmlrpc_user_packages>, project_json=<function pypi_project_json>, max_workers=8)

The list of projects that `user` owns or maintains on PyPI.

Each record has `name`, `href` (the project’s PyPI page) and `role`
(`'owner'` or `'maintainer'`). With `with_details=True` it also has
`description` (the summary), `version` and `date` (upload time of the
last release), fetched concurrently from the JSON API: one request per project,
so expect some seconds for an account with hundreds of projects.

If `cache_results` is True (the default), results are cached on disk, in
`slurp_user_projects_info.user_projects_info_cache_folder`.
If `refresh` is True, the cache is refreshed.
A cache written without details is refetched when details are asked for.

`user_packages` (`user -> [(role, name), ...]`) and `project_json`
(`name -> dict`) are the transports; the defaults call PyPI.

```pycon
>>> infos = slurp_user_projects_info('thorwhalen1')
>>> sorted(infos[0])
['href', 'name', 'role']
```

### yp.base.xmlrpc_user_packages(user, , timeout=30)

`[(role, name), ...]` for the projects `user` owns or maintains on PyPI.

Calls PyPI’s XML-RPC `user_packages` method, the only official way to list an
account’s projects (deprecated by PyPI but still answered). The HTML user page
(`https://pypi.org/user/{user}/`) answers scripts with a JavaScript challenge,
so it cannot be used.

```pycon
>>> xmlrpc_user_packages('thorwhalen1')[:2]
[['Owner', 'accompy'], ['Owner', 'aix']]
```
