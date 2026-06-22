---
name: yp-name-availability
description: >-
  PyPI name-finding tooling for the yp package. Use this skill to help a user
  find an AVAILABLE PyPI package name: the user describes what their package
  does, you brainstorm candidate names, filter them fast against yp's cached
  PyPI name index, then confirm the survivors with a live PyPI check and present
  the free options. Trigger whenever the user wants to name a new package/project
  or library, asks "is <name> available/taken on PyPI", "what should I call my
  package", "find an available pip name", "check if this package name is free",
  "suggest names for a project that does X", or is otherwise picking a
  distribution name to publish to PyPI. Covers brainstorming, the cheap cached
  pre-filter, the authoritative live check, and the exact way to present results.
  For inspecting a name that already EXISTS use yp-package-info; for maintaining
  the cached index itself use yp-name-cache.
metadata:
  audience: users
---

# Find an available PyPI package name

Help a user choose a package name that is actually **free to publish on PyPI**.
The user describes what their package does; you brainstorm candidates, drop the
ones already taken using yp's fast offline index, confirm the rest with a live
check, and present the free options.

The whole point is a **two-stage filter**: a cheap, offline pre-filter over yp's
cached snapshot of every PyPI name (instant, no network), followed by an
**authoritative live check** only on the handful of survivors. Never present a
name as available on the cached check alone — see the gotchas.

## Procedure

### 1. Understand the package

Get (or infer) a one-line description of what the package does, its domain, and
any flavor the user wants (playful, technical, short, brandable). Ask only if
the description is too thin to brainstorm from.

### 2. Brainstorm candidates (aim wide)

Generate **20-40** candidate names so that enough survive the filters. Good
name-generation moves:

- **Domain word + suffix**: `-py`, `-kit`, `-tools`, `-lib`, `-ly`, `-ify`,
  `-flow`, `-box`, `-forge` (e.g. a parsing lib → `parsly`, `parsekit`).
- **Portmanteaus / blends** of two relevant words.
- **Metaphors** for what it does (a cache → `attic`, `larder`).
- **Invented/short coined words** — easiest to get and to brand.
- **Prefix the domain** (e.g. `qa-`, `auto-`, `mini-`).

Respect PyPI / PEP 503 naming rules so a candidate *can* be a real name:

- Names are ASCII, **case-insensitive**, and treat `-`, `_`, `.` (and runs of
  them) as **equivalent**. So `Foo-Bar`, `foo_bar`, `foo.bar` are the SAME name
  on PyPI — a separator variant of a taken name is **not** a way to get a free
  name.
- Prefer short, lowercase, pronounceable, memorable.
- Avoid: overly generic words (almost always taken), trademarks, and names
  confusingly close to popular packages (typosquat risk → may be removed).
- Also keep the **import name** clean: the importable module is usually the name
  with separators turned into `_`, and it must be a valid Python identifier
  (letters/digits/underscores, not starting with a digit) and ideally not shadow
  a stdlib module (`json`, `time`, `string`, …). A great distribution name with a
  broken or stdlib-colliding import name is a poor choice.

### 3. Cheap cached pre-filter (offline, instant)

Construct `Pypi()` **once** (it builds a frozenset of ~800k+ names; reuse it),
then filter:

```python
from yp import Pypi

p = Pypi()  # loads yp's cached PyPI name index once — reuse this object

candidates = ["parsly", "parsekit", "snipsnap", ...]  # your 20-40 ideas

# Pypi.is_available(name) == (name not in the cached index). O(1) per check.
# Note: a name with separators (e.g. "foo-bar") can still slip through here even
# when it's taken — the live check in step 4 resolves those (see Gotchas).
maybe_free = [c for c in candidates if p.is_available(c.lower())]
```

`p.is_available(name)` is the efficient yp tool the cached check is built on —
it's an O(1) set membership test, so filtering dozens of names is instant. (You
can also write `name in p` / `name not in p` directly.)

Keep brainstorming and filtering until you have **enough survivors to be worth a
live check — target ~8-12**. If too few survive, generate another batch.

### 4. Authoritative live check (only on survivors)

The cached index is a *snapshot* and does not normalize separators (see
gotchas), so a survivor of step 3 might still be taken. Confirm each survivor
against PyPI **live** with yp's `Pypi.live_is_available`. It queries the PyPI
**JSON API** (`404` → free, `200` → taken) and normalizes names per PEP 503, so
it correctly catches the separator-variant collisions the cached filter misses:

```python
from yp import Pypi

# live_is_available is a staticmethod — no instance needed. True => free.
free = [n for n in maybe_free if Pypi.live_is_available(n)]
```

The companion `Pypi().pkg_has_pypi_page(name)` answers the inverse (`True` => the
name is **taken**). Both use the JSON API under the hood, which is the reliable
signal — do **not** scrape the HTML `pypi.org/project/<name>` page, which can
return a soft **200 for names that don't exist** in some network environments.

If you'd rather not import yp, hit the JSON API directly — same signal:

```python
import requests

def live_available(name: str) -> bool:
    return requests.get(f"https://pypi.org/pypi/{name}/json", timeout=10).status_code == 404
```

(Avoid `p[name]` / `info_of_pkg_from_web(name)` for this: they hit the same JSON
endpoint but *raise* `RequestException` on a free 404 name and pickle the failed
response to a temp file, so they're awkward for a plain availability boolean.)

### 5. Present the results — in this exact order

1. **Lead with the bare list**, comma-separated, nothing else: just the names
   that passed the live check.
2. **Then the rationale**: one short line per name — what it evokes and why it
   fits the package, plus notes (e.g. clean import name, very short, playful).
3. **Finish with the concise comma-separated list again**, so the user ends with
   an easy-to-copy answer.

Example shape of the reply:

```
parsly, snipsnap, leaftap, quill, tabkit

- parsly — "parse" + "-ly"; short, clearly about parsing; import name `parsly` is clean.
- snipsnap — playful, memorable; evokes cutting/extracting snippets.
- leaftap — "tap a leaf node"; fits a tree-walking parser.
- quill — single short word, very brandable; import `quill`.
- tabkit — "tabular toolkit"; descriptive, easy to spell.

Available: parsly, snipsnap, leaftap, quill, tabkit
```

If none survive, say so plainly and offer another brainstorming round (and
optionally relax constraints, e.g. allow a suffix).

## Gotchas

- **Cached check is a pre-filter, not proof.** The cached index does **not**
  collapse separators, so `is_available("scikit_learn")`, `is_available("zope-interface")`,
  and `is_available("ruamel-yaml")` all return `True` even though those names are
  taken (they're separator variants of `scikit-learn`, `zope.interface`,
  `ruamel.yaml`). The live JSON check normalizes server-side and catches these —
  which is exactly why step 4 is mandatory.
- **Snapshot staleness.** The cache reflects PyPI as of the last refresh, so a
  name registered since then can pass the cached filter yet be taken. The live
  check covers this too. If the cache is old, refresh it first — see the
  **yp-name-cache** skill.
- **Construct `Pypi()` once.** Each construction builds the full name frozenset;
  don't rebuild it inside a loop.
- **Be gentle on the live endpoint.** You're typically checking ~10 names, which
  is fine. Don't fire hundreds of live requests in a tight loop.

## Related

- **yp-name-cache** — refresh the cached index and understand the offline
  availability primitive in depth.
- **yp-package-info** — once a name is taken, inspect who owns it / what it is.
- After you land on a free name, the user's `setup-py-project` skill can scaffold
  the package and repo.
