import pytest
import respx


@pytest.fixture()
async def httpx_mock():
    async with respx.mock(base_url='http://example.com') as _http_mock:
        yield _http_mock
