"""The OpenAPI schema documents every Phase 2 endpoint."""

import pytest
from drf_spectacular.generators import SchemaGenerator


@pytest.fixture(scope="module")
def paths():
    return SchemaGenerator().get_schema(request=None, public=True)["paths"]


def _has_response(op, code):
    return "content" in op["responses"][code]


def test_register_documents_request_and_201(paths):
    op = paths["/api/v1/accounts/register/"]["post"]
    assert "requestBody" in op
    assert "201" in op["responses"]
    assert _has_response(op, "201")


@pytest.mark.parametrize(
    "path",
    ["/api/v1/patients/me/", "/api/v1/psychologists/me/", "/api/v1/ngo/me/"],
)
def test_me_endpoints_documented(paths, path):
    item = paths[path]
    assert _has_response(item["get"], "200")
    assert _has_response(item["patch"], "200")
    assert "requestBody" in item["patch"]


def test_logout_documents_request_and_205(paths):
    op = paths["/api/v1/accounts/logout/"]["post"]
    assert "requestBody" in op
    assert "205" in op["responses"]


def test_public_stats_documented(paths):
    assert _has_response(paths["/api/v1/stats/public/"]["get"], "200")


def test_cities_lists_country_parameter(paths):
    params = paths["/api/v1/reference/cities/"]["get"]["parameters"]
    names = {p["name"] for p in params}
    assert {"country", "search"} <= names


@pytest.mark.parametrize("name", ["countries", "languages", "specializations"])
def test_reference_lists_documented(paths, name):
    assert _has_response(paths[f"/api/v1/reference/{name}/"]["get"], "200")
