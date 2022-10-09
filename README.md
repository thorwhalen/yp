# yp

A mapping view to pypi projects

To install:	```pip install yp```

# Example Usage

Get a mapping of all of ``pypi`` projects.

    >>> from yp import Pypi
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

