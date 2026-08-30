"""Base functionality of yp"""

import gzip
from functools import wraps
import tempfile
import pickle
from pathlib import Path
import re
from collections.abc import Mapping

import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
from dol import KvReader, wrap_kvs

from yp.util import dpath, app_path

pkg_list_url = "https://pypi.org/simple"
pkg_info_furl = "https://pypi.python.org/pypi/{pkg_name}/json"
pypi_user_furl = "https://pypi.org/user/{user}/"
pkg_existence_check_timeout = 10  # seconds, for live JSON-API availability checks
#: Canonical cache file: gzipped TSV of ``pkg_name<TAB>pkg_stub`` lines, where the
#: tab and stub are omitted for the ~96% of projects whose stub equals their name.
#: That keeps the copy shipped in the distribution at ~4MB, against ~27MB for the
#: equivalent pickle, and avoids unpickling data at import time.
PKG_LIST_FILENAME = "pkg_list.tsv.gz"

#: Seed copy shipped inside the installed distribution (read-only in most installs).
pkg_names_package_filepath = Path(dpath(PKG_LIST_FILENAME))
#: Where ``refresh_saved_pkg_name_stub`` writes; takes precedence when it exists.
pkg_names_user_filepath = app_path / PKG_LIST_FILENAME
#: Pre-0.0.12 pickle cache, still read when no gzipped TSV is found.
pkg_names_legacy_pickle_filepath = Path(dpath("pkg_list.p"))

pkg_names_filepath = pkg_names_package_filepath  # backwards-compatible alias
pkg_names_text_filepath = dpath("pkg_list.txt")
pkg_name_re = re.compile(r"/simple/([^/]+)/")
nums_re = re.compile(r"\d+")

user_projects_info_path = app_path / "user_projects_info"
# ensure directory exists
user_projects_info_path.mkdir(parents=True, exist_ok=True)


class MissingPackageNamesError(FileNotFoundError):
    """Raised when yp's cached list of PyPI project names cannot be found or read.

    Previously this condition was swallowed, which left ``pkg_name_stub`` undefined
    and surfaced downstream as a bare ``ImportError: cannot import name
    'pkg_name_stub'`` -- with no hint as to the real cause.
    """


def _encode_pkg_name_stub(pkg_name_stub):
    """Encode a ``{pkg_name: pkg_stub}`` mapping as gzipped TSV bytes."""
    lines = (
        name if name == stub else f"{name}\t{stub}"
        for name, stub in pkg_name_stub.items()
    )
    # mtime=0 keeps the output byte-for-byte reproducible across builds
    return gzip.compress("\n".join(lines).encode("utf-8"), 6, mtime=0)


def _decode_pkg_name_stub(data: bytes):
    """Inverse of ``_encode_pkg_name_stub``."""
    pkg_name_stub = {}
    for line in gzip.decompress(data).decode("utf-8").split("\n"):
        if line:
            name, _, stub = line.partition("\t")
            pkg_name_stub[name] = stub or name
    return pkg_name_stub


def _read_pkg_name_stub():
    """Read the cached ``{pkg_name: pkg_stub}`` mapping, freshest source first.

    Raises ``MissingPackageNamesError``, with instructions, if no cache is readable.
    """
    for filepath in (pkg_names_user_filepath, pkg_names_package_filepath):
        if filepath.is_file():
            return _decode_pkg_name_stub(filepath.read_bytes())
    if pkg_names_legacy_pickle_filepath.is_file():  # pre-0.0.12 cache
        with open(pkg_names_legacy_pickle_filepath, "rb") as f:
            return pickle.load(f)
    raise MissingPackageNamesError(
        "yp could not find its cached list of PyPI project names.\n"
        "Looked for:\n"
        f"  {pkg_names_user_filepath}\n"
        f"  {pkg_names_package_filepath}\n"
        f"  {pkg_names_legacy_pickle_filepath} (legacy)\n"
        "This usually means yp was installed from a distribution built without its "
        "data files. To download and cache the list yourself (a few MB from "
        f"{pkg_list_url}), run:\n"
        "    python -c 'import yp; yp.refresh_saved_pkg_name_stub()'"
    )


class CachedPkgNameStub(Mapping):
    """The ``{pkg_name: pkg_stub}`` mapping of every project on PyPI, loaded lazily.

    Reading the cache is deferred to first use, so ``import yp`` stays cheap and,
    more importantly, never fails because of a missing data file: a missing cache
    raises ``MissingPackageNamesError`` -- with an actionable message -- only if and
    when the names are actually needed.

    >>> stub = CachedPkgNameStub()
    >>> 'numpy' in stub
    True
    >>> stub['scikit-learn']
    'scikit-learn'
    >>> len(stub) > 100_000
    True
    """

    def __init__(self, mapping=None):
        self._mapping = mapping

    @property
    def mapping(self):
        """The underlying ``dict``, read from cache on first access."""
        if self._mapping is None:
            self._mapping = _read_pkg_name_stub()
        return self._mapping

    def update_cache(self, mapping):
        """Replace the in-memory contents, keeping this object's identity.

        Rebinding the module global instead would leave every ``from yp import
        pkg_name_stub`` pointing at the stale mapping.
        """
        self._mapping = mapping

    @property
    def is_loaded(self):
        """Whether the cache has been read yet."""
        return self._mapping is not None

    def __getitem__(self, k):
        return self.mapping[k]

    def __iter__(self):
        return iter(self.mapping)

    def __len__(self):
        return len(self.mapping)

    def __contains__(self, k):
        return k in self.mapping

    def __repr__(self):
        state = f"{len(self._mapping)} names" if self.is_loaded else "not loaded yet"
        return f"{type(self).__name__}(<{state}>)"


#: Mapping of every PyPI project name to its normalized stub. Loaded on first use.
pkg_name_stub = CachedPkgNameStub()


def asis(x):
    return x


class Pypi(KvReader):
    """
    Get a mapping of all of ``pypi`` projects.

    >>> p = Pypi()

    The keys of this mapping are the project names. There are lots!

    >>> len(p)  # doctest: +SKIP
    405120
    >>> 'numpy' in p and 'dol' in p
    True
    >>> 'no_way_this_is_a_package' in p
    False

    The values of the mapping are the corresponding project's info, which is a
    nested dict of good stuff.

    >>> info = p['numpy']
    >>> {'info', 'last_serial', 'releases', 'urls'}.issubset(info)
    True

    Tip: To only get the info you want, you'll

    The project info is obtained, live, making requests to the
    ``https://pypi.python.org/pypi/{pkg_name}/json`` API,
    but the list of all project names is actually taken from a local file.
    You should update that file regularly (but not TOO regularly!) to be in sync
    with pypi.org. To do so, do this:

    >>> Pypi.refresh_cached_package_names()  # doctest: +SKIP

    If, on the other hand, you don't want all projects of Pypi to be the collection
    you're working with, you can specify what ``user`` they should belong to:

    >>> p = Pypi(user='thorwhalen1')  # doctest: +SKIP
    >>> len(p)  # doctest: +SKIP
    131

    You can also explicitly give ``Pypi`` a collection of projects you want to work
    with:

    >>> p = Pypi(proj_names={'numpy', 'pandas', 'dol'})
    >>> len(p)
    3

    You can do a lot more by simply using the tools of ``dol`` to change the mapping
    you want to work with in all kinds of ways!

    """

    _src_kind = None
    _src_info = None

    # TODO: init has keyword only to make it easier to extend to other filters than user,
    #  such as classification etc.
    def __init__(
        self, *, info_extractor=None, proj_names=None, user=None, strict_getitem=False
    ):
        """
        :param strict_getitem: By default, any valid package can be fetched,
        not just those contained in the particular ``Pypi` instance.
        Set ``strict_getitem`` to ``True`` will, on the other hand, do this check,
        and raise a ``KeyError`` if a key that's not in the instance is requested.
        """
        if proj_names:
            self._src_kind = "collection"
            self.proj_names = proj_names
        elif user:
            self._src_kind = "user"
            self._src_info = user
            self.proj_names = [d["name"] for d in slurp_user_projects_info(user)]
        else:
            self._src_kind = "all"
            self.proj_names = frozenset(pkg_name_stub)
        self.strict_getitem = strict_getitem
        self.info_extractor = info_extractor or asis

    @classmethod
    def with_fresh_cached_package_names(cls):
        """Download and save a fresh copy of pypi's package names"""
        refresh_saved_pkg_name_stub()
        return cls()

    refresh_cached_package_names = (
        with_fresh_cached_package_names  # backwards compatibility alias
    )

    def __iter__(self):
        yield from self.proj_names

    def __getitem__(self, k):
        """
        Note that any valid package can be fetched, not just those contained in the
        particular ``Pypi`` instance.
        """
        if self.strict_getitem and k not in self.proj_names:
            raise KeyError(f"Key not found in this Pypi instance: {k}")
        return self.info_extractor(self.live_package_info(k))

    def __contains__(self, k):
        return k in self.proj_names

    def __len__(self):
        return len(self.proj_names)

    def live_package_info(self, pkg_name):
        return info_of_pkg_from_web(pkg_name)

    def pkg_has_pypi_page(self, pkg_name):
        """Return True iff ``pkg_name`` has a project on PyPI (i.e. the name is
        taken). Uses the authoritative JSON API (see ``_pkg_exists_on_pypi``)."""
        return _pkg_exists_on_pypi(pkg_name)

    def __repr__(self):
        prefix = f"{type(self).__name__}"
        if self._src_kind == "all":
            suffix = f"()"
        elif self._src_kind == "user":
            suffix = f"(user={self.user})"
        elif self._src_kind == "collection":
            suffix = f"(<a collection of length {len(self.proj_names)}>)"
        else:
            suffix = f"(...)"
        return prefix + suffix

    def is_available(self, word):
        return word not in self

    @staticmethod
    def live_is_available(pkg_name):
        """Check if a package name is available, live (directly on pypi, not a
        cache). Returns ``True`` iff the name is free to register.

        Uses the PyPI JSON API as the authoritative signal (404 => free,
        200 => taken), which is more reliable than scraping the HTML project
        page (that can return a soft 200 for non-existent names in some network
        environments). PyPI normalizes names per PEP 503, so separator/case
        variants of a taken name correctly report as unavailable.
        """
        return not _pkg_exists_on_pypi(pkg_name)


def _get_text_or_none(tag):
    return tag.text if tag else None


def _extract_project_info_from_user_page(node):
    return dict(
        name=_get_text_or_none(node.find("h3")),
        description=_get_text_or_none(
            node.find("p", {"class": "package-snippet__description"})
        ),
        date=node.find("time").get("datetime"),
        href=node.get("href"),
    )


def get_url_contents_with_selenium(url: str, wait_seconds: int = 5) -> str:
    import time
    from selenium import webdriver  # pip install selenium
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import (
        ChromeDriverManager,
    )  # pip install webdriver-manager

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get(url)
    time.sleep(wait_seconds)  # Wait for the page to load
    page_source = driver.page_source  # Full rendered HTML
    driver.quit()  # Close the browser
    return page_source


_user_projects_info_cache_folder = app_path / "user_projects_info"


def slurp_user_projects_info(
    user,
    *,
    extractor=_extract_project_info_from_user_page,
    validate_project_infos=False,
    cache_results=True,
    refresh=False,
):
    """
    Fetches the list of projects for that user.
    To do so it fetches the html of the user projects page and parses out
    ``name``, ``href`` and ``date`` (of the last release), which can be useful in
    its own, to not have to get it from repeated project info requests.

    If `cache_results` is True (the default), results will be cached.
    If `refresh` is True, the cache will be refreshed.
    """
    import json

    cache_file = _user_projects_info_cache_folder / f"{user}.json"

    if cache_results and cache_file.exists() and not refresh:
        return json.load(open(cache_file))

    url = pypi_user_furl.format(user=user)
    page_contents = get_url_contents_with_selenium(
        url, wait_seconds=5
    )  # see note below
    b = BeautifulSoup(page_contents, features="lxml")
    proj_infos = b.find_all("a", {"class": "package-snippet"})
    if validate_project_infos:
        _validate_user_projects_infos(proj_infos)
    projects_info = list(map(extractor, proj_infos))

    if cache_results:
        json.dump(projects_info, open(cache_file, "w"))

    return projects_info


slurp_user_projects_info.user_projects_info_cache_folder = (
    _user_projects_info_cache_folder
)


def _validate_user_projects_infos(proj_infos):
    _t = _get_text_or_none(nums_re.search(b.find("h2")))
    if _t is not None:
        expected_n_projects = int(_t.strip()).group(0)
        assert (
            len(proj_infos) == expected_n_projects
        ), f"I expected {expected_n_projects} projects but found {len(proj_infos)} listed"


def get_updated_pkg_name_stub():
    """
    Get ``{pkg_name: pkg_stub}`` data from pypi
    :return: ``{pkg_name: pkg_stub, ...}`` dict
    """
    r = request_saving_failure_responses("get", pkg_list_url)
    t = BeautifulSoup(r.content.decode(), features="lxml")
    return {
        str(x.contents[0]).lower(): pkg_name_re.match(x.get("href")).group(1)
        for x in gen_find(t, "a")
    }


def refresh_saved_pkg_name_stub(verbose=True, *, save_to=None, write_text_file=True):
    """
    Update the ``{pkg_name: pkg_stub}`` stored data with a fresh call to
    ``get_updated_pkg_name_stub``.

    The refreshed copy is written to the user's app folder by default, not into the
    installed package, which is read-only in many installs.

    :param save_to: Where to write the gzipped TSV cache.
        Defaults to ``pkg_names_user_filepath``.
    :param write_text_file: Also write a plain ``pkg_list.txt`` of the names, one per
        line, alongside ``save_to``.
    """
    save_to = Path(save_to) if save_to is not None else pkg_names_user_filepath
    n = len(pkg_name_stub) if pkg_name_stub.is_loaded else 0

    fresh = get_updated_pkg_name_stub()
    save_to.parent.mkdir(parents=True, exist_ok=True)
    save_to.write_bytes(_encode_pkg_name_stub(fresh))
    if write_text_file:
        (save_to.parent / "pkg_list.txt").write_text("\n".join(fresh))
    pkg_name_stub.update_cache(fresh)

    if verbose:
        print(
            f"Updated the pkg_name_stub. Had {n} items; now has {len(fresh)}."
            f" The data is saved here: {save_to}"
        )


def info_of_pkg_from_web(pkg_name):
    """
    Get dict of information for a pkg_name
    :param pkg_name:
    :return:
    """
    r = request_saving_failure_responses("get", pkg_info_furl.format(pkg_name=pkg_name))
    return r.json()


def _pkg_exists_on_pypi(pkg_name, *, timeout=pkg_existence_check_timeout):
    """Return True iff ``pkg_name`` exists on PyPI, using the authoritative
    JSON API as the signal (200 => exists/taken, 404 => free).

    A lightweight ``HEAD`` request is used (no payload downloaded). This is more
    reliable than scraping the HTML ``/project/<name>`` page, which can return a
    soft 200 for non-existent names in some network environments. PyPI
    normalizes names per PEP 503, so separator/case variants of a taken name
    (e.g. ``scikit_learn`` for ``scikit-learn``) also report ``True``.
    """
    r = requests.head(
        pkg_info_furl.format(pkg_name=pkg_name), allow_redirects=True, timeout=timeout
    )
    return r.status_code == 200


# Utils #################################################################################


@wraps(requests.request)
def request_saving_failure_responses(*args, **kwargs):
    r = requests.request(*args, **kwargs)
    if r.status_code == 200:
        return r
    else:
        msg = f"Request came back with status_code: {r.status_code}"
        tmp_filepath = tempfile.mktemp()
        pickle.dump(r, open(tmp_filepath, "wb"))
        msg += f"""\nThe response object was pickled in {tmp_filepath}.
        To get it do:
        import pickle
        r = pickle.load(open('{tmp_filepath}', 'rb'))
        """
        raise RequestException(msg)


def return_sentinel_on_exception(caught_exceptions=(Exception,), sentinel=None):
    """Decorates a function so it will return a sentinel (default None) instead of
    raising an exception"""

    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except caught_exceptions:
                return sentinel
            return wrapped

    return decorator


@wraps(
    BeautifulSoup.find_all,
    assigned=("__module__", "__qualname__", "__annotations__", "__name__"),
)
def gen_find(tag, *args, **kwargs):
    """Does what BeautifulSoup.find_all does, but as an iterator.
    See find_all documentation for more information."""
    if isinstance(tag, str):
        tag = BeautifulSoup(tag, features="lxml")
    next_tag = tag.find(*args, **kwargs)
    while next_tag is not None:
        yield next_tag
        next_tag = next_tag.find_next(*args, **kwargs)
