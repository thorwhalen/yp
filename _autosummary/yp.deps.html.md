# yp.deps

Tools for getting dependencies info.

### Examples

Simple usage:

```pycon
>>> sorted(package_dependencies("bs4", format="names"))
['beautifulsoup4', 'soupsieve', 'typing_extensions']
```

More involved:

```pycon
>>> d = package_dependencies_tree('bs4')
>>> assert d == [
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
```

```pycon
>>> info_by_key, flat_deps = parse_pipdeptree(d)
>>> assert info_by_key == {
...     'beautifulsoup4': {'package_name': 'beautifulsoup4', 'installed_version': '4.13.3'},
...     'bs4': {'package_name': 'bs4', 'installed_version': '0.0.2'},
...     'soupsieve': {'package_name': 'soupsieve', 'installed_version': '2.6'},
...     'typing-extensions': {
...         'package_name': 'typing_extensions',
...         'installed_version': '4.12.2',
...     },
... }
>>> assert flat_deps == {
...     'beautifulsoup4': {'soupsieve': '>1.2', 'typing-extensions': '>=4.0.0'},
...     'bs4': {'beautifulsoup4': 'Any'},
...     'soupsieve': {},
...     'typing-extensions': {},
... }
```

```pycon
>>> nested_tree = build_nested_deps("bs4")
>>> assert nested_tree == {
...     'beautifulsoup4': {
...         'required_version': 'Any',
...         'dependencies': {
...             'soupsieve': {'required_version': '>1.2', 'dependencies': {}},
...             'typing-extensions': {'required_version': '>=4.0.0', 'dependencies': {}},
...         },
...     }
... }
```

### Functions

| [`build_nested_deps`](#yp.deps.build_nested_deps)(package_key[, flat_deps])        | Recursively build a nested dict of dependencies for `package_key`.   |
|-----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| [`package_dependencies`](#yp.deps.package_dependencies)(package_key[, format, ...])   | Return the dependencies of `package_key` in one of three formats:    |
| [`package_dependencies_tree`](#yp.deps.package_dependencies_tree)(package_name, \*[, ...]) | Fetches raw dependency data from pipdeptree for a specific package.  |
| [`parse_pipdeptree`](#yp.deps.parse_pipdeptree)(data)                             | Turn pipdeptree JSON (list of PackageInfo dicts) into                |

### yp.deps.build_nested_deps(package_key, flat_deps=None)

Recursively build a nested dict of dependencies for `package_key`.
Each node is { dep_key: {“required_version”:…, “dependencies”: {…}}, … }

### yp.deps.package_dependencies(package_key, format='names', , flat_deps=None, info_by_key=None, include_transitive=True, include_details=False, only_include_problematic_versions=False)

Return the dependencies of `package_key` in one of three formats:

format=”names”            -> [“dep1”, “dep2”, …]
format=”names_with_req”   -> [“dep1>=1.2.0”, “dep2<0.5”, …]
format=”tuples”           -> [(“dep1”, “>=”, “1.2.0”), (“dep2”, “<”, “0.5”), …]

When include_details=True, returns a list of dicts instead:

```default
[{"package_name":…, "required_version":…, "installed_version":…}, …]
```

- package_key: the package key whose deps you want
- flat_deps: output of parse_pipdeptree (dict pkg_key → {dep_key: req_str,…})
- info_by_key: output of parse_pipdeptree (dict pkg_key → installed/info)
- include_transitive: whether to include transitive (indirect) dependencies
- include_details: whether to return detailed information about each dependency
- only_include_problematic_versions: when True, only include dependencies where installed version
  doesn’t satisfy the required version (only used when include_details=True)

```pycon
>>> sorted(package_dependencies("bs4", format="names"))
['beautifulsoup4', 'soupsieve', 'typing_extensions']
```

### yp.deps.package_dependencies_tree(package_name, , return_none_if_package_not_installed=False)

Fetches raw dependency data from pipdeptree for a specific package.

* **Parameters:**
  **package_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The name of the installed package to inspect.
* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)
* **Returns:**
  List of package data from pipdeptree.
* **Raises:**
  * [**CalledProcessError**](https://docs.python.org/3/library/subprocess.html#subprocess.CalledProcessError) – If pipdeptree command fails
  * [**JSONDecodeError**](https://docs.python.org/3/library/json.html#json.JSONDecodeError) – If parsing JSON output fails
  * [**FileNotFoundError**](https://docs.python.org/3/builtins/exceptions.html#FileNotFoundError) – If pipdeptree is not installed

### yp.deps.parse_pipdeptree(data)

Turn pipdeptree JSON (list of PackageInfo dicts) into

> 1. info_by_key:  { pkg_key: {“package_name”:…, “installed_version”:…}, … }
> 2. flat_deps:    { pkg_key: {dep_key: required_version, …}, … }
