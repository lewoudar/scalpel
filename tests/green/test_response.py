import httpx
import pytest
from gevent.queue import JoinableQueue

from scalpel.green.response import SeleniumResponse, StaticResponse


class TestStaticResponse:
    """Tests StaticResponse.follow method"""

    @pytest.mark.parametrize(
        ('reachable_urls', 'followed_urls'), [({'http://foo.com'}, set()), (set(), {'http://foo.com'})]
    )
    def test_should_not_follow_already_processed_url(self, mocker, reachable_urls, followed_urls):
        logger_mock = mocker.patch('logging.Logger.debug')
        url = 'http://foo.com'
        request = httpx.Request('GET', url)
        httpx_response = httpx.Response(200, request=request)
        response = StaticResponse(
            reachable_urls=reachable_urls,
            followed_urls=followed_urls,
            queue=JoinableQueue(),
            httpx_response=httpx_response,
        )
        response.follow(url)
        assert mocker.call('url %s has already been processed, nothing to do here', url) in logger_mock.call_args_list

    def test_should_follow_unprocessed_url(self):
        url = 'http://foo.com'
        request = httpx.Request('GET', url)
        httpx_response = httpx.Response(200, request=request)
        response = StaticResponse(
            reachable_urls={'http://bar.com'}, followed_urls=set(), queue=JoinableQueue(), httpx_response=httpx_response
        )
        response.follow(url)

        assert {'http://bar.com'} == response._reachable_urls
        assert {url} == response._followed_urls
        assert 1 == response._queue.qsize()


class TestSeleniumResponse:
    """Tests Selenium.follow response"""

    @pytest.mark.parametrize(
        ('reachable_urls', 'followed_urls'), [({'http://foo.com'}, set()), (set(), {'http://foo.com'})]
    )
    def test_should_not_follow_already_processed_url(self, mocker, chrome_driver, reachable_urls, followed_urls):
        logger_mock = mocker.patch('logging.Logger.debug')
        url = 'http://foo.com'
        response = SeleniumResponse(
            driver=chrome_driver,
            handle='4',
            reachable_urls=reachable_urls,
            followed_urls=followed_urls,
            queue=JoinableQueue(),
        )
        response.follow(url)
        assert mocker.call('url %s has already been processed, nothing to do here', url) in logger_mock.call_args_list

    def test_should_follow_unprocessed_url(self, chrome_driver):
        url = 'http://foo.com'
        response = SeleniumResponse(
            driver=chrome_driver,
            handle='4',
            reachable_urls={'http://bar.com'},
            followed_urls=set(),
            queue=JoinableQueue(),
        )
        response.follow(url)

        assert {'http://bar.com'} == response._reachable_urls
        assert {url} == response._followed_urls
        assert 1 == response._queue.qsize()
