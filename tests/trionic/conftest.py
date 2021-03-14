import pytest
import respx
import trio


@pytest.fixture()
def trio_tmp_path(tmp_path):
    """Trio tmp_path"""
    return trio.Path(tmp_path)


@pytest.fixture()
async def httpx_mock():
    async with respx.mock(base_url='http://example.com') as _http_mock:
        yield _http_mock
