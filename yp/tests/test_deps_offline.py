"""Offline tests for yp.deps: pipdeptree data is injected, so no pipdeptree or subprocess is needed."""

import pytest

from yp import deps
from yp.deps import (
    build_nested_deps,
    package_dependencies,
    package_dependencies_tree,
    parse_pipdeptree,
)

TREE = [
    {
        "package": {"key": "app", "package_name": "app", "installed_version": "1.0"},
        "dependencies": [
            {"key": "lib-a", "package_name": "lib_a", "installed_version": "2.0",
             "required_version": ">=1.0"},
            {"key": "lib-b", "package_name": "lib_b", "installed_version": "0.5",
             "required_version": ">=1.0"},
        ],
    },
    {
        "package": {"key": "lib-a", "package_name": "lib_a", "installed_version": "2.0"},
        "dependencies": [
            {"key": "lib-c", "package_name": "lib_c", "installed_version": "3.1",
             "required_version": "<4"},
        ],
    },
    {"package": {"key": "lib-b", "package_name": "lib_b", "installed_version": "0.5"},
     "dependencies": []},
    {"package": {"key": "lib-c", "package_name": "lib_c", "installed_version": "3.1"},
     "dependencies": []},
]


@pytest.fixture
def parsed():
    return parse_pipdeptree(TREE)


def test_parse_pipdeptree(parsed):
    info, flat = parsed
    assert info["lib-a"] == {"package_name": "lib_a", "installed_version": "2.0"}
    assert flat["app"] == {"lib-a": ">=1.0", "lib-b": ">=1.0"}
    assert flat["lib-b"] == {}


def test_build_nested_deps(parsed):
    _, flat = parsed
    nested = build_nested_deps("app", flat)
    assert nested["lib-a"]["dependencies"]["lib-c"] == {
        "required_version": "<4", "dependencies": {},
    }
    assert nested["lib-b"]["dependencies"] == {}


def test_names_transitive_and_direct(parsed):
    info, flat = parsed
    kw = dict(flat_deps=flat, info_by_key=info)
    assert sorted(package_dependencies("app", **kw)) == ["lib_a", "lib_b", "lib_c"]
    assert sorted(package_dependencies("app", include_transitive=False, **kw)) == [
        "lib_a", "lib_b",
    ]


def test_formats_direct(parsed):
    info, flat = parsed
    kw = dict(flat_deps=flat, info_by_key=info, include_transitive=False)
    assert sorted(package_dependencies("app", "names_with_req", **kw)) == [
        "lib_a>=1.0", "lib_b>=1.0",
    ]
    assert sorted(package_dependencies("app", "tuples", **kw)) == [
        ("lib_a", ">=", "1.0"), ("lib_b", ">=", "1.0"),
    ]
    assert package_dependencies("lib-b", "tuples", **kw) == []
    with pytest.raises(ValueError, match="unknown format"):
        package_dependencies("app", "nope", **kw)


@pytest.mark.xfail(
    strict=True,
    reason="transitive mode looks the requirement up in the dependency's own deps "
    "(flat_deps[dep][dep]), so required versions are always dropped",
)
def test_formats_transitive_keep_requirements(parsed):
    info, flat = parsed
    out = package_dependencies("app", "names_with_req", flat_deps=flat, info_by_key=info)
    assert "lib_a>=1.0" in out


def test_details(parsed):
    info, flat = parsed
    kw = dict(flat_deps=flat, info_by_key=info, include_details=True)
    direct = package_dependencies("app", include_transitive=False, **kw)
    assert {d["package_name"] for d in direct} == {"lib_a", "lib_b"}
    allr = package_dependencies("app", **kw)
    assert {d["package_name"] for d in allr} == {"lib_a", "lib_b", "lib_c"}
    # lib_b 0.5 does not satisfy >=1.0
    bad = package_dependencies("app", only_include_problematic_versions=True, **kw)
    assert [d["package_name"] for d in bad] == ["lib_b"]
    bad_direct = package_dependencies(
        "app", include_transitive=False, only_include_problematic_versions=True, **kw
    )
    assert [d["package_name"] for d in bad_direct] == ["lib_b"]


def test_flat_and_info_must_come_together(parsed):
    info, flat = parsed
    with pytest.raises(ValueError, match="both"):
        package_dependencies("app", flat_deps=flat)


def test_package_dependencies_tree_with_fake_subprocess(monkeypatch):
    import json
    import subprocess
    import sys
    import types

    monkeypatch.setitem(sys.modules, "pipdeptree", types.ModuleType("pipdeptree"))

    def run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(TREE), stderr="")

    monkeypatch.setattr(deps.subprocess, "run", run)
    assert package_dependencies_tree("app") == TREE

    monkeypatch.setattr(
        deps.subprocess, "run", lambda c, **k: subprocess.CompletedProcess(c, 0, "", "")
    )
    assert package_dependencies_tree("x", return_none_if_package_not_installed=True) is None
    with pytest.raises(ValueError, match="installed"):
        package_dependencies_tree("x")
