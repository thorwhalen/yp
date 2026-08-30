"""Tests for the cached PyPI project-name data and how it is loaded.

These guard the bug that shipped in yp 0.0.11: the distribution carried no data
file at all, the loader swallowed the resulting failure, and ``pkg_name_stub``
was simply never defined -- so ``import yp`` died with a bare ``ImportError``
that named neither the missing file nor the remedy.
"""

import gzip

import pytest

from yp.base import (
    CachedPkgNameStub,
    MissingPackageNamesError,
    PKG_LIST_FILENAME,
    _decode_pkg_name_stub,
    _encode_pkg_name_stub,
    pkg_names_package_filepath,
)


def test_encode_decode_roundtrip():
    """Names whose stub differs from the name survive encoding, as do plain ones."""
    original = {"numpy": "numpy", "scikit.learn": "scikit-learn", "a_b": "a-b"}
    assert _decode_pkg_name_stub(_encode_pkg_name_stub(original)) == original


def test_encode_is_reproducible():
    """Byte-for-byte stable output, so rebuilding data doesn't churn the diff."""
    d = {"numpy": "numpy", "x.y": "x-y"}
    assert _encode_pkg_name_stub(d) == _encode_pkg_name_stub(d)


def test_data_file_ships_in_source_tree():
    """The cache the distribution is supposed to carry must actually be here."""
    assert pkg_names_package_filepath.name == PKG_LIST_FILENAME
    assert pkg_names_package_filepath.is_file(), (
        f"{pkg_names_package_filepath} is missing; the built distribution would "
        "reproduce the 0.0.11 bug"
    )
    names = _decode_pkg_name_stub(pkg_names_package_filepath.read_bytes())
    assert len(names) > 100_000
    assert "numpy" in names and "dol" in names


def test_stub_is_lazy():
    """Constructing must not read the cache; only use does."""
    stub = CachedPkgNameStub()
    assert not stub.is_loaded
    assert "not loaded yet" in repr(stub)
    assert "numpy" in stub
    assert stub.is_loaded


def test_update_cache_keeps_identity():
    """Refreshing must mutate in place, or importers keep a stale mapping."""
    stub = CachedPkgNameStub({"old": "old"})
    stub.update_cache({"new": "new"})
    assert dict(stub) == {"new": "new"}


def test_missing_cache_raises_informative_error(tmp_path, monkeypatch):
    """No cache anywhere => an error naming the paths tried and the fix."""
    import yp.base as base

    for attr in (
        "pkg_names_user_filepath",
        "pkg_names_package_filepath",
        "pkg_names_legacy_pickle_filepath",
    ):
        monkeypatch.setattr(base, attr, tmp_path / f"absent-{attr}")

    stub = CachedPkgNameStub()
    with pytest.raises(MissingPackageNamesError) as excinfo:
        len(stub)

    message = str(excinfo.value)
    assert "refresh_saved_pkg_name_stub" in message, "must name the remedy"
    assert str(tmp_path) in message, "must name the paths it looked in"


def test_legacy_pickle_is_still_read(tmp_path, monkeypatch):
    """Installs cached by an older yp keep working."""
    import pickle

    import yp.base as base

    legacy = tmp_path / "pkg_list.p"
    legacy.write_bytes(pickle.dumps({"legacy": "legacy"}))
    monkeypatch.setattr(base, "pkg_names_user_filepath", tmp_path / "absent.tsv.gz")
    monkeypatch.setattr(base, "pkg_names_package_filepath", tmp_path / "absent2.tsv.gz")
    monkeypatch.setattr(base, "pkg_names_legacy_pickle_filepath", legacy)

    assert dict(CachedPkgNameStub()) == {"legacy": "legacy"}


def test_user_cache_takes_precedence(tmp_path, monkeypatch):
    """A refreshed user copy must win over the seed shipped in the package."""
    import yp.base as base

    user = tmp_path / "user.tsv.gz"
    package = tmp_path / "package.tsv.gz"
    user.write_bytes(_encode_pkg_name_stub({"fresh": "fresh"}))
    package.write_bytes(_encode_pkg_name_stub({"stale": "stale"}))
    monkeypatch.setattr(base, "pkg_names_user_filepath", user)
    monkeypatch.setattr(base, "pkg_names_package_filepath", package)

    assert dict(CachedPkgNameStub()) == {"fresh": "fresh"}


def test_decode_rejects_non_gzip():
    """A truncated or corrupt cache fails loudly, not silently."""
    with pytest.raises(gzip.BadGzipFile):
        _decode_pkg_name_stub(b"not gzipped at all")
