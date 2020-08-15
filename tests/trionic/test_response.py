import httpx
import pytest
import trio

from scalpel.trionic.response import StaticResponse


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
        send_channel, receive_channel = trio.open_memory_channel(0)
        response = StaticResponse(
            reachable_urls=reachable_urls,
            followed_urls=followed_urls,
            send_channel=send_channel,
            httpx_response=httpx_response
        )
        await response.follow(url)
        await send_channel.aclose()
        await receive_channel.aclose()

        assert mocker.call('url %s has already been processed, nothing to do here', url) in logger_mock.call_args_list

    async def test_should_follow_unprocessed_url(self):
        url = 'http://foo.com'
        request = httpx.Request('GET', url)
        httpx_response = httpx.Response(200, request=request)
        send_channel, receive_channel = trio.open_memory_channel(2)
        response = StaticResponse(
            reachable_urls={'http://bar.com'},
            followed_urls=set(),
            send_channel=send_channel,
            httpx_response=httpx_response
        )
        await response.follow(url)
        stats = send_channel.statistics()
        await send_channel.aclose()
        await receive_channel.aclose()

        assert {'http://bar.com'} == response._reachable_urls
        assert {url} == response._followed_urls
        assert 1 == stats.current_buffer_used
