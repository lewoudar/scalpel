import httpx
import pytest
import trio
from asyncmock import AsyncMock


@pytest.fixture()
def trio_tmp_path(tmp_path):
    """Trio tmp_path"""
    return trio.Path(tmp_path)


@pytest.fixture()
def get_response():
    """Factory fixture to create an async mock httpx response"""

    def _get_response(method='GET', url='http://example.com', status_code=200, content='blabla'):
        request = httpx.Request(method, url)
        response = httpx.Response(status_code, request=request, content=content.encode())
        return AsyncMock(return_value=response)

    return _get_response
