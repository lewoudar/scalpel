import httpx
import pytest

from scalpel.trionic.response import StaticResponse
from scalpel.trionic.utils.queue import Queue


class TestStaticResponse:
    """Tests StaticResponse.follow method"""

    @pytest.mark.parametrize(('reachable_urls', 'followed_urls'), [
        ({'http://foo.com'}, set()),
        (set(), {'http://foo.com'})
    ])
    async def test_should_not_follow_already_processed_url(self, mocker, reachable_urls, followed_urls):
        logger_mock = mocker.patch('logging.Logger.debug')
        url = 'http://foo.com'
        request = httpx.Request('GET', url)
        httpx_response = httpx.Response(200, request=request)
        queue = Queue()
        response = StaticResponse(
            reachable_urls=reachable_urls,
            followed_urls=followed_urls,
            queue=queue,
            httpx_response=httpx_response
        )

        await response.follow(url)
        await queue.close()

        assert mocker.call('url %s has already been processed, nothing to do here', url) in logger_mock.call_args_list

    async def test_should_follow_unprocessed_url(self):
        url = 'http://foo.com'
        request = httpx.Request('GET', url)
        httpx_response = httpx.Response(200, request=request)
        queue = Queue(2)
        response = StaticResponse(
            reachable_urls={'http://bar.com'},
            followed_urls=set(),
            queue=queue,
            httpx_response=httpx_response
        )
        await response.follow(url)
        queue_length = queue.length
        await queue.close()

        assert {'http://bar.com'} == response._reachable_urls
        assert {url} == response._followed_urls
        assert 1 == queue_length
