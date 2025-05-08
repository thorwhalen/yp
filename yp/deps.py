"""
Tools for getting dependencies info.


Examples
--------
Simple usage:

>>> sorted(package_dependencies("bs4", format="names"))
['beautifulsoup4', 'soupsieve', 'typing_extensions']

More involved:

>>> d = package_dependencies_tree('bs4')
>>> assert d == [  # doctest: +SKIP
...     {
...         'package': {
...             'key': 'beautifulsoup4',
...             'package_name': 'beautifulsoup4',
...             'installed_version': '4.13.3',
...         },
...         'dependencies': [
...             {
...                 'key': 'soupsieve',
...                 'package_name': 'soupsieve',
...                 'installed_version': '2.6',
...                 'required_version': '>1.2',
...             },
...             {
...                 'key': 'typing-extensions',
...                 'package_name': 'typing_extensions',
...                 'installed_version': '4.12.2',
...                 'required_version': '>=4.0.0',
...             },
...         ],
...     },
...     {
...         'package': {'key': 'bs4', 'package_name': 'bs4', 'installed_version': '0.0.2'},
...         'dependencies': [
...             {
...                 'key': 'beautifulsoup4',
...                 'package_name': 'beautifulsoup4',
...                 'installed_version': '4.13.3',
...                 'required_version': 'Any',
...             }
...         ],
...     },
...     {
...         'package': {
...             'key': 'soupsieve',
...             'package_name': 'soupsieve',
...             'installed_version': '2.6',
...         },
...         'dependencies': [],
...     },
...     {
...         'package': {
...             'key': 'typing-extensions',
...             'package_name': 'typing_extensions',
...             'installed_version': '4.12.2',
...         },
...         'dependencies': [],
...     },
... ]

>>> info_by_key, flat_deps = parse_pipdeptree(d)
>>> assert info_by_key == {  # doctest: +SKIP
...     'beautifulsoup4': {'package_name': 'beautifulsoup4', 'installed_version': '4.13.3'},
...     'bs4': {'package_name': 'bs4', 'installed_version': '0.0.2'},
...     'soupsieve': {'package_name': 'soupsieve', 'installed_version': '2.6'},
...     'typing-extensions': {
...         'package_name': 'typing_extensions',
...         'installed_version': '4.12.2',
...     },
... }
>>> assert flat_deps == {  # doctest: +SKIP
...     'beautifulsoup4': {'soupsieve': '>1.2', 'typing-extensions': '>=4.0.0'},
...     'bs4': {'beautifulsoup4': 'Any'},
...     'soupsieve': {},
...     'typing-extensions': {},
... }

>>> nested_tree = build_nested_deps("bs4")
>>> assert nested_tree == {  # doctest: +SKIP
...     'beautifulsoup4': {
...         'required_version': 'Any',
...         'dependencies': {
...             'soupsieve': {'required_version': '>1.2', 'dependencies': {}},
...             'typing-extensions': {'required_version': '>=4.0.0', 'dependencies': {}},
...         },
...     }
... }
"""

import subprocess
import json


def package_dependencies_tree(
    package_name: str, *, return_none_if_package_not_installed=False
) -> list:
    """
    Fetches raw dependency data from pipdeptree for a specific package.

    Args:
        package_name: The name of the installed package to inspect.

    Returns:
        List of package data from pipdeptree.

    Raises:
        subprocess.CalledProcessError: If pipdeptree command fails
        json.JSONDecodeError: If parsing JSON output fails
        FileNotFoundError: If pipdeptree is not installed
    """
    try:
        import pipdeptree

        result = subprocess.run(
            ["pipdeptree", "--packages", package_name, "--json"],
            capture_output=True,
            text=True,
            check=True,
        )

        if result.stdout == "":
            if return_none_if_package_not_installed:
                return None
            else:
                raise ValueError(
                    f"It doesn't look like you have this package installed: {package_name}"
                )
        else:
            # Parse the JSON output
            return json.loads(result.stdout)

    except ImportError:
        raise ImportError(
            "pipdeptree is not installed. Please install it using 'pip install pipdeptree'."
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running pipdeptree: {e}")
        print(f"Error output: {e.stderr}")
        raise
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        print(f"Raw output: {result.stdout if 'result' in locals() else 'No output'}")
        raise
    except FileNotFoundError:
        print(
            "Error: pipdeptree is not installed. Please install it using 'pip install pipdeptree'."
        )
        raise


def parse_pipdeptree(data):
    """
    Turn pipdeptree JSON (list of PackageInfo dicts) into
      1) info_by_key:  { pkg_key: {"package_name":…, "installed_version":…}, … }
      2) flat_deps:    { pkg_key: {dep_key: required_version, …}, … }
    """
    info_by_key = {}
    flat_deps = {}
    for entry in data:
        pkg = entry["package"]
        key = pkg["key"]
        # record installed info
        info_by_key[key] = {
            "package_name": pkg["package_name"],
            "installed_version": pkg["installed_version"],
        }
        # record immediate dependencies + their required_version
        flat_deps[key] = {
            dep["key"]: dep["required_version"] for dep in entry["dependencies"]
        }
    return info_by_key, flat_deps


def build_nested_deps(package_key, flat_deps=None):
    """
    Recursively build a nested dict of dependencies for `package_key`.
    Each node is { dep_key: {"required_version":…, "dependencies": {…}}, … }
    """
    if flat_deps is None:
        d = package_dependencies_tree(package_key)
        info_by_key, flat_deps = parse_pipdeptree(d)

    nested = {}
    for dep_key, req_ver in flat_deps.get(package_key, {}).items():
        nested[dep_key] = {
            "required_version": req_ver,
            "dependencies": build_nested_deps(dep_key, flat_deps),
        }
    return nested


from packaging.version import parse as parse_version
from packaging.specifiers import SpecifierSet


def package_dependencies(
    package_key,
    format: str = "names",
    *,
    flat_deps=None,
    info_by_key=None,
    include_transitive: bool = True,
    include_details: bool = False,
    only_include_problematic_versions: bool = False,
):
    """
    Return the dependencies of `package_key` in one of three formats:

    format="names"            -> ["dep1", "dep2", …]
    format="names_with_req"   -> ["dep1>=1.2.0", "dep2<0.5", …]
    format="tuples"           -> [("dep1", ">=", "1.2.0"), ("dep2", "<", "0.5"), …]

    When include_details=True, returns a list of dicts instead:
      [{"package_name":…, "required_version":…, "installed_version":…}, …]

    - package_key: the package key whose deps you want
    - flat_deps: output of parse_pipdeptree (dict pkg_key → {dep_key: req_str,…})
    - info_by_key: output of parse_pipdeptree (dict pkg_key → installed/info)
    - include_transitive: whether to include transitive (indirect) dependencies
    - include_details: whether to return detailed information about each dependency
    - only_include_problematic_versions: when True, only include dependencies where installed version
      doesn't satisfy the required version (only used when include_details=True)

    >>> sorted(package_dependencies("bs4", format="names"))
    ['beautifulsoup4', 'soupsieve', 'typing_extensions']
    """
    if flat_deps is None and info_by_key is None:
        d = package_dependencies_tree(package_key)
        info_by_key, flat_deps = parse_pipdeptree(d)
    elif flat_deps is None or info_by_key is None:
        raise ValueError("flat_deps and info_by_key must both be provided or both not")

    # If detailed information is requested
    if include_details:
        if include_transitive:
            # Collect all dependencies recursively
            all_deps = set()

            def collect_deps(pkg_key):
                deps = flat_deps.get(pkg_key, {})
                for dep_key in deps:
                    if dep_key not in all_deps:
                        all_deps.add(dep_key)
                        collect_deps(dep_key)

            collect_deps(package_key)
            # Process each dependency collected
            details = []
            for dep_key in all_deps:
                # Find which package requires this dependency to get required_version
                required_version = ""
                for pkg, deps in flat_deps.items():
                    if dep_key in deps:
                        required_version = deps[dep_key]
                        break

                pkg_info = info_by_key[dep_key]
                installed = pkg_info["installed_version"]
                record = {
                    "package_name": pkg_info["package_name"],
                    "required_version": required_version or "",
                    "installed_version": installed,
                }

                if only_include_problematic_versions:
                    if required_version:
                        spec = SpecifierSet(required_version)
                        if parse_version(installed) not in spec:
                            details.append(record)
                else:
                    details.append(record)

            return details
        else:
            # Only immediate dependencies with details
            deps = flat_deps.get(package_key, {})
            details = []
            for dep_key, req_str in deps.items():
                pkg_info = info_by_key[dep_key]
                installed = pkg_info["installed_version"]
                record = {
                    "package_name": pkg_info["package_name"],
                    "required_version": req_str or "",
                    "installed_version": installed,
                }

                if only_include_problematic_versions:
                    if req_str:
                        spec = SpecifierSet(req_str)
                        if parse_version(installed) not in spec:
                            details.append(record)
                else:
                    details.append(record)

            return details

    # Original functionality for non-detailed output
    if include_transitive:
        # Collect all dependencies recursively
        all_deps = set()

        def collect_deps(pkg_key):
            deps = flat_deps.get(pkg_key, {})
            for dep_key in deps:
                if dep_key not in all_deps:
                    all_deps.add(dep_key)
                    collect_deps(dep_key)

        collect_deps(package_key)
        dep_items = [
            (dep_key, flat_deps.get(dep_key, {}).get(dep_key, ""))
            for dep_key in all_deps
        ]
    else:
        # Only immediate dependencies
        deps = flat_deps.get(package_key, {})
        dep_items = list(deps.items())

    out = []
    for dep_key, req_str in dep_items:
        pkg_name = info_by_key[dep_key]["package_name"]
        if format == "names":
            out.append(pkg_name)
        elif format == "names_with_req":
            if req_str:
                out.append(f"{pkg_name}{req_str}")
            else:
                out.append(pkg_name)
        elif format == "tuples":
            if req_str:
                spec = SpecifierSet(req_str)
                # split into operator and version
                # choose the first specifier if multiple
                op, ver = next(iter(spec)).operator, next(iter(spec)).version
            else:
                op, ver = "", ""
            out.append((pkg_name, op, ver))
        else:
            raise ValueError(f"unknown format {format!r}")
    return out


# The package_dependencies_details function can now be deprecated or removed
# since its functionality is included in package_dependencies with include_details=True
