"""Tests for listing a PyPI user's projects, without touching the network.

The listing used to scrape ``https://pypi.org/user/{user}/``, which now answers
scripts with a JavaScript challenge. It goes through XML-RPC ``user_packages``
instead; these tests inject the transports (or fake the HTTP layer) to check the
records, the opt-in details, and the cache.
"""

import xmlrpc.client

import pytest

import yp.base
from yp.base import slurp_user_projects_info, xmlrpc_user_packages, Pypi

PAIRS = [["Owner", "dol"], ["Maintainer", "i2"]]

PROJECT_JSON = {
    "dol": {
        "info": {"summary": "Data object layers", "version": "0.3.1"},
        "urls": [
            {"upload_time_iso_8601": "2026-10-01T10:00:00.000000Z"},
            {"upload_time_iso_8601": "2026-10-01T10:00:05.000000Z"},
        ],
    },
    "i2": {"info": {"summary": "", "version": "0.1.0"}, "urls": []},
}


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(yp.base, "user_projects_info_path", tmp_path)
    return tmp_path


def _fake_user_packages(calls):
    def user_packages(user):
        calls.append(user)
        return PAIRS

    return user_packages


def test_records_have_name_href_role(cache_dir):
    calls = []
    infos = slurp_user_projects_info(
        "someone", user_packages=_fake_user_packages(calls)
    )
    assert calls == ["someone"]
    assert infos == [
        {"name": "dol", "href": "https://pypi.org/project/dol/", "role": "owner"},
        {"name": "i2", "href": "https://pypi.org/project/i2/", "role": "maintainer"},
    ]


def test_with_details(cache_dir):
    infos = slurp_user_projects_info(
        "someone",
        with_details=True,
        user_packages=_fake_user_packages([]),
        project_json=PROJECT_JSON.__getitem__,
    )
    by_name = {d["name"]: d for d in infos}
    assert by_name["dol"]["description"] == "Data object layers"
    assert by_name["dol"]["version"] == "0.3.1"
    assert by_name["dol"]["date"] == "2026-10-01T10:00:05.000000Z"
    assert by_name["i2"]["description"] is None
    assert by_name["i2"]["date"] is None


def test_cache_is_used_then_refreshed(cache_dir):
    calls = []
    fetch = _fake_user_packages(calls)
    first = slurp_user_projects_info("someone", user_packages=fetch)
    assert (cache_dir / "someone.json").exists()
    assert slurp_user_projects_info("someone", user_packages=fetch) == first
    assert calls == ["someone"]  # second call came from the cache
    slurp_user_projects_info("someone", user_packages=fetch, refresh=True)
    assert calls == ["someone", "someone"]


def test_cache_without_details_is_refetched_for_details(cache_dir):
    calls = []
    fetch = _fake_user_packages(calls)
    slurp_user_projects_info("someone", user_packages=fetch)
    infos = slurp_user_projects_info(
        "someone",
        with_details=True,
        user_packages=fetch,
        project_json=PROJECT_JSON.__getitem__,
    )
    assert len(calls) == 2
    assert all("date" in d for d in infos)


def test_no_cache(cache_dir):
    slurp_user_projects_info(
        "someone", user_packages=_fake_user_packages([]), cache_results=False
    )
    assert not (cache_dir / "someone.json").exists()


@pytest.fixture
def fake_post(monkeypatch):
    """Replace the HTTP POST with a fake PyPI XML-RPC endpoint answering ``PAIRS``."""
    sent = {}

    class Response:
        content = xmlrpc.client.dumps((PAIRS,), methodresponse=True).encode()

        def raise_for_status(self):
            pass

    def post(url, data, headers, timeout):
        sent.update(url=url, call=xmlrpc.client.loads(data))
        return Response()

    monkeypatch.setattr(yp.base.requests, "post", post)
    return sent


def test_xmlrpc_user_packages_speaks_xmlrpc(fake_post):
    """The default transport posts an XML-RPC call and decodes the response."""
    assert xmlrpc_user_packages("someone") == PAIRS
    assert fake_post["url"] == "https://pypi.org/pypi"
    assert fake_post["call"] == (("someone",), "user_packages")


def test_pypi_user_mapping_keys(cache_dir, fake_post):
    """The README's ``Pypi(user=...)`` is keyed by the user's project names."""
    assert sorted(Pypi(user="someone")) == ["dol", "i2"]
