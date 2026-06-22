---
name: yp-dependencies
description: >-
  Dependency-analysis tooling for the yp package. Use this skill to inspect the
  dependency tree of an INSTALLED Python package via yp's pipdeptree-backed
  helpers: list direct and transitive dependencies, get required vs installed
  versions, find packages whose installed version violates a requirement, and
  build a nested dependency tree. Trigger when the user asks "what does package X
  depend on", "show the dependency tree of X", "which of X's deps are out of
  spec / have version conflicts", "list transitive dependencies", or wants to
  reason about an installed environment's dependency graph. Operates on the
  currently installed environment, not on live PyPI.
metadata:
  audience: users
---

# Analyze an installed package's dependencies with yp

These helpers wrap `pipdeptree` to answer "what does this package depend on?"
for the **currently installed environment**. They are about *installed* packages,
not live PyPI metadata (for that, see **yp-package-info**).

## Quick usage

```python
from yp import package_dependencies

package_dependencies("bs4")                         # transitive names (default)
# ['beautifulsoup4', 'soupsieve', 'typing_extensions']

package_dependencies("bs4", include_transitive=False)   # direct deps only
```

## Output formats

`format=` controls the shape:

- `"names"` (default) → `["beautifulsoup4", "soupsieve", "typing_extensions"]`
- `"names_with_req"` → `["soupsieve>1.2", "typing_extensions>=4.0.0", ...]`
- `"tuples"` → `[("soupsieve", ">", "1.2"), ...]`

The version constraint is only populated for **direct** dependencies
(`include_transitive=False`); the two examples above assume that. With the
default `include_transitive=True`, the string formats can't recover which parent
required a transitive dep, so `names_with_req` returns bare names and `tuples`
returns empty operator/version slots — see Gotchas. (Names use the distribution's
`package_name`, e.g. `typing_extensions` with an underscore, not the
`typing-extensions` dict key.)

For full records, use `include_details=True` (returns dicts instead of strings):

```python
package_dependencies("bs4", include_details=True)
# [{'package_name': 'soupsieve', 'required_version': '>1.2',
#   'installed_version': '2.6'}, ...]
```

## Find version conflicts

Surface only deps whose **installed** version does not satisfy the **required**
specifier (needs `include_details=True`):

```python
package_dependencies(
    "some-package",
    include_details=True,
    only_include_problematic_versions=True,
)
# [] means every installed dependency satisfies its requirement.
```

## Raw tree and nested view

```python
from yp.deps import package_dependencies_tree, parse_pipdeptree, build_nested_deps

raw = package_dependencies_tree("bs4")          # raw pipdeptree JSON (list of dicts)
info_by_key, flat_deps = parse_pipdeptree(raw)  # {key: info}, {key: {dep: req}}
build_nested_deps("bs4")                         # recursive nested dict
```

## Gotchas

- **Requires `pipdeptree` installed** in the same environment. If it's missing,
  the helpers raise a clear `ImportError` ("Please install it using
  `pip install pipdeptree`"). It is declared in yp's dependencies but may be
  absent in a minimal/editable env — install it on demand.
- **The package must be installed.** `package_dependencies_tree` raises
  `ValueError` for a package that isn't installed (pass
  `return_none_if_package_not_installed=True` to get `None` instead).
- **Required-version is unreliable for transitive deps in the string formats.**
  With `include_transitive=True`, the `names_with_req`/`tuples` formats can't
  recover which parent required a transitive dep, so its version constraint comes
  out empty. For accurate required-version info either query **direct** deps
  (`include_transitive=False`) or use `include_details=True`, which looks up the
  requiring parent.
- Pass `package_dependencies` a key as pipdeptree knows it (usually the canonical
  distribution name, e.g. `beautifulsoup4`, though import-name aliases like `bs4`
  also resolve here).

## Related

- **yp-package-info** — live `requires_dist` and metadata straight from PyPI
  (no install needed), via `extract_main_info`.
