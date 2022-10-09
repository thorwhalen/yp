"""Base functionality of yb"""

import os
from functools import wraps
import tempfile
import pickle
import re

import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
from dol import KvReader, wrap_kvs

from yp.util import dpath

pkg_list_url = 'https://pypi.org/simple'
pkg_info_furl = 'https://pypi.python.org/pypi/{pkg_name}/json'
pypi_user_furl = 'https://pypi.org/user/{user}/'
pkg_names_filepath = dpath('pkg_list.p')
pkg_name_re = re.compile(r'/simple/([^/]+)/')
nums_re = re.compile(r'\d+')

try:
    pkg_name_stub = pickle.load(open(pkg_names_filepath, 'rb'))
except:
    import warnings

    warnings.warn(
        f"Couldn't unpickle {pkg_names_filepath}. Some functionality might not work"
    )


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
    >>> list(info)
    ['info', 'last_serial', 'releases', 'urls', 'vulnerabilities']

    Tip: To only get the info you want, you'll

    The project info is obtained, live, making requests to the
    ``https://pypi.python.org/pypi/{pkg_name}/json`` API,
    but the list of all project names is actually taken from a local file.
    You should update that file regularly (but not TOO regularly!) to be in sync
    with pypi.org. To do so, do this:

    >>> Pypi.refresh_cached_package_names()  # doctest: +SKIP

    If, on the other hand, you don't want all projects of Pypi to be the collection
    you're working with, you can specify what ``user`` they should belong to:

    >>> p = Pypi(user='thorwhalen1')
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
            self._src_kind = 'collection'
            self.proj_names = proj_names
        elif user:
            self._src_kind = 'user'
            self._src_info = user
            self.proj_names = [d['name'] for d in slurp_user_projects_info(user)]
        else:
            self._src_kind = 'all'
            self.proj_names = frozenset(pkg_name_stub)
        self.strict_getitem = strict_getitem
        self.info_extractor = info_extractor or asis

    @classmethod
    def refresh_cached_package_names(self):
        """Download and save a fresh copy of pypi's package names"""
        return refresh_saved_pkg_name_stub()

    def __iter__(self):
        yield from self.proj_names

    def __getitem__(self, k):
        """
        Note that any valid package can be fetched, not just those contained in the
        particular ``Pypi`` instance.
        """
        if self.strict_getitem and k not in self.proj_names:
            raise KeyError(f'Key not found in this Pypi instance: {k}')
        return self.info_extractor(self.live_package_info(k))

    def __contains__(self, k):
        return k in self.proj_names

    def __len__(self):
        return len(self.proj_names)

    def live_package_info(self, pkg_name):
        return info_of_pkg_from_web(pkg_name)

    def pkg_has_pypi_page(self, pkg_name):
        r = requests.get(f'https://pypi.org/project/{pkg_name}')
        return r.status_code == 200

    def __repr__(self):
        prefix = f'{type(self).__name__}'
        if self._src_kind == 'all':
            suffix = f'()'
        elif self._src_kind == 'user':
            suffix = f'(user={self.user})'
        elif self._src_kind == 'collection':
            suffix = f'(<a collection of length {len(self.proj_names)}>)'
        else:
            suffix = f'(...)'
        return prefix + suffix


def slurp_user_projects_info(user):
    """Fetches the list of projects for that user.
    To do so it fetches the html of the user projects page and parses out
    ``name``, ``href`` and ``date`` (of the last release), which can be useful in
    its own, to not have to get it from repeated project info requests.
    """

    def extract_info(node):
        return dict(
            name=node.find('h3').text,
            href=node.get('href'),
            date=node.find('time').get('datetime'),
        )

    url = pypi_user_furl.format(user=user)
    b = BeautifulSoup(
        request_saving_failure_responses('get', url).content, features='lxml'
    )
    expected_n_projects = int(nums_re.search(b.find('h2').text.strip()).group(0))
    proj_infos = b.find_all('a', {'class': 'package-snippet'})
    assert (
        len(proj_infos) == expected_n_projects
    ), f'I expected {expected_n_projects} projects but found {len(proj_infos)} listed'
    return list(map(extract_info, proj_infos))


def get_updated_pkg_name_stub():
    """
    Get ``{pkg_name: pkg_stub}`` data from pypi
    :return: ``{pkg_name: pkg_stub, ...}`` dict
    """
    r = request_saving_failure_responses('get', pkg_list_url)
    t = BeautifulSoup(r.content.decode(), features='lxml')
    return {
        str(x.contents[0]).lower(): pkg_name_re.match(x.get('href')).group(1)
        for x in gen_find(t, 'a')
    }


def refresh_saved_pkg_name_stub(verbose=True):
    """
    Update the ``{pkg_name: pkg_stub}`` stored data with a fresh call to
    ``get_updated_pkg_name_stub``
    """
    n = 0
    if verbose:
        n = (
            os.path.isfile(pkg_names_filepath)
            and len(pickle.load(open(pkg_names_filepath, 'rb')))
        ) or 0
    pkg_name_stub = get_updated_pkg_name_stub()
    pickle.dump(pkg_name_stub, open(pkg_names_filepath, 'wb'))
    if verbose:
        print(
            f'Updated the pkg_name_stub. Had {n} items; now has {len(pkg_name_stub)}.'
            f' The dict is saved here: {pkg_names_filepath}'
        )


def info_of_pkg_from_web(pkg_name):
    """
    Get dict of information for a pkg_name
    :param pkg_name:
    :return:
    """
    r = request_saving_failure_responses('get', pkg_info_furl.format(pkg_name=pkg_name))
    return r.json()


# Utils #################################################################################


@wraps(requests.request)
def request_saving_failure_responses(*args, **kwargs):
    r = requests.request(*args, **kwargs)
    if r.status_code == 200:
        return r
    else:
        msg = f'Request came back with status_code: {r.status_code}'
        tmp_filepath = tempfile.mktemp()
        pickle.dump(r, open(tmp_filepath, 'wb'))
        msg += f'''\nThe response object was pickled in {tmp_filepath}.
        To get it do:
        import pickle
        r = pickle.load(open('{tmp_filepath}', 'rb'))
        '''
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
    assigned=('__module__', '__qualname__', '__annotations__', '__name__'),
)
def gen_find(tag, *args, **kwargs):
    """Does what BeautifulSoup.find_all does, but as an iterator.
        See find_all documentation for more information."""
    if isinstance(tag, str):
        tag = BeautifulSoup(tag, features='lxml')
    next_tag = tag.find(*args, **kwargs)
    while next_tag is not None:
        yield next_tag
        next_tag = next_tag.find_next(*args, **kwargs)
