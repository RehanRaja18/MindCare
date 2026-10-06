"""The OpenAPI schema documents every Phase 2 endpoint."""

from unittest import mock

import pytest
from drf_spectacular.drainage import GENERATOR_STATS
from drf_spectacular.generators import SchemaGenerator


@pytest.fixture(scope="module")
def generated():
    """Generate the schema once and collect every warning drf-spectacular emits.

    All warn()/error() calls funnel through GENERATOR_STATS.emit. openapi.py imports
    warn by name, so patching drainage.warn would miss it; wrapping emit does not."""
    GENERATOR_STATS.reset()
    with mock.patch.object(GENERATOR_STATS, "emit", wraps=GENERATOR_STATS.emit) as emit:
        schema = SchemaGenerator().get_schema(request=None, public=True)
    warnings = [str(c.args[0]) for c in emit.call_args_list if c.args[1] == "warning"]
    return schema, warnings


@pytest.fixture(scope="module")
def schema(generated):
    return generated[0]


@pytest.fixture(scope="module")
def paths(schema):
    return schema["paths"]


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


def test_no_unresolved_authenticator_warnings(generated):
    _, warnings = generated
    assert not [w for w in warnings if "could not resolve authenticator" in w]


def test_jwt_security_scheme_documented(schema):
    assert schema["components"]["securitySchemes"]["jwtAuth"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }


def test_authenticated_endpoint_requires_jwt(paths):
    assert {"jwtAuth": []} in paths["/api/v1/relationships/current/"]["get"]["security"]


@pytest.mark.parametrize(
    ("path", "method"),
    [("/api/v1/stats/public/", "get"), ("/api/v1/accounts/register/", "post")],
)
def test_public_endpoint_does_not_require_jwt(paths, path, method):
    assert {"jwtAuth": []} not in paths[path][method].get("security", [])
