# yp

A mapping view to pypi projects

To install:	```pip install yp```

See also: `pipoke`, for more pypi interaction tools.

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


# Extras

`yp` ships a cached list of every PyPI project name (`yp/data/pkg_list.tsv.gz`), so
name lookups are instant and offline. The cache is loaded lazily -- the first lookup
pays for it, `import yp` does not.

`yp.refresh_saved_pkg_name_stub()` fetches the current list and saves it to your app
folder, which then takes precedence over the copy shipped with the package. (It writes
there rather than into the installed package, which is read-only in many installs.)
Pass `save_to=` to write elsewhere.

I also refresh the shipped copy from time to time and push the results. You can find
the list (as a text file with one name per line) here:
https://raw.githubusercontent.com/thorwhalen/yp/refs/heads/master/yp/data/pkg_list.txt


# Skills

`yp` ships [AI agent skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)
(SKILL.md files) that teach an agent how to drive its tools. They live in
`yp/data/skills/` (so they install with the package) and are mirrored into
`.claude/skills/` for Claude Code.

| Skill | What it helps you do |
|---|---|
| `yp-name-availability` | Find an **available** PyPI name for a new package: brainstorm → fast cached pre-filter → authoritative live check → present the free options. |
| `yp-name-cache` | Operate the cached PyPI name index: refresh it, check names fast/offline, understand freshness & normalization caveats. |
| `yp-package-info` | Fetch live PyPI info: full project JSON, a tidy digest, latest version(s), last-upload time, a user's projects, bulk download. |
| `yp-dependencies` | Inspect an installed package's dependency tree (direct/transitive, required vs installed, version conflicts). |

Install one into an agent host with [`gh skill`](https://github.com/github/gh-skill):

    gh skill install thorwhalen/yp yp-name-availability
