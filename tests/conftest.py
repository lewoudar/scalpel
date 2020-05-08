import pytest
import respx


@pytest.fixture()
def httpx_mock():
    """respx mock object"""
    with respx.HTTPXMock(base_url='http://example.com') as _httpx_mock:
        yield _httpx_mock


@pytest.fixture(scope='session')
def robots_content():
    return """
    User-agent: Googlebot
    Disallow: /videos/
    Disallow: /photos/

    User-agent: *
    Disallow: /admin/
    Allow: /admin/admin-ajax.php
    """
