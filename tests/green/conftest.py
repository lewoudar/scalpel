import pytest
import respx


@pytest.fixture()
def httpx_mock():
    """respx mock object"""
    with respx.HTTPXMock(base_url='http://example.com') as _httpx_mock:
        yield _httpx_mock
