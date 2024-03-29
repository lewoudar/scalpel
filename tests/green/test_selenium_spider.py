from datetime import datetime

import httpx
import pytest
import respx
from gevent.lock import RLock
from gevent.pool import Pool
from gevent.queue import JoinableQueue
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from scalpel.core.config import Browser, Configuration
from scalpel.core.message_pack import datetime_decoder
from scalpel.green import read_mp
from scalpel.green.robots import RobotsAnalyzer
from scalpel.green.selenium_spider import SeleniumResponse, SeleniumSpider, StaticSpider


class TestSeleniumSpider:
    """Tests class SeleniumSpider"""

    def test_selenium_spider_class_is_a_subclass_of_static_spider(self):
        assert issubclass(SeleniumSpider, StaticSpider)

    def test_selenium_attributes_are_correctly_instantiated(self):
        config = Configuration(selenium_driver_log_file=None)
        spider = SeleniumSpider(urls=['http://foo.com'], parse=lambda x, y: None, config=config)
        assert isinstance(spider._start_time, float)
        assert isinstance(spider._http_client, httpx.Client)
        assert isinstance(spider._robots_analyser, RobotsAnalyzer)
        assert config == spider._config
        assert isinstance(spider._lock, RLock)
        assert isinstance(spider._queue, JoinableQueue)
        assert len(spider.urls) == spider._queue.qsize()
        assert isinstance(spider._pool, Pool)
        assert isinstance(spider._driver, WebDriver)

        # cleanup
        spider._cleanup()

    # _get_selenium_response test

    @pytest.mark.parametrize(('browser', 'handle'), [(Browser.FIREFOX, '4'), (Browser.CHROME, '4')])
    def test_should_return_selenium_response_when_giving_correct_input(self, browser, handle):
        config = Configuration(selenium_driver_log_file=None, selenium_browser=browser)
        spider = SeleniumSpider(urls=['http://foo.com'], parse=lambda x, y: None, config=config)
        response = spider._get_selenium_response(handle)

        assert isinstance(response, SeleniumResponse)
        assert response._reachable_urls == spider.reachable_urls
        assert response._followed_urls == spider.followed_urls
        assert response._queue == spider._queue
        assert response.driver is spider._driver
        assert response.handle == handle

        # cleanup
        spider._cleanup()

    # _handle_url test

    @pytest.mark.parametrize(
        ('reachable_urls', 'unreachable_urls', 'robots_excluded_urls'),
        [(set(), set(), {'http://foo.com'}), (set(), {'http://foo.com'}, set()), ({'http://foo.com'}, set(), set())],
    )
    def test_should_do_nothing_if_url_is_already_present_in_one_url_set(
        self, mocker, reachable_urls, unreachable_urls, robots_excluded_urls
    ):
        url = 'http://foo.com'
        logger_mock = mocker.patch('logging.Logger.debug')
        config = Configuration(selenium_driver_log_file=None)
        spider = SeleniumSpider(urls=['http://bar.com'], parse=lambda x, y: None, config=config)
        spider.reachable_urls = reachable_urls
        spider.unreachable_urls = unreachable_urls
        spider.robots_excluded_urls = robots_excluded_urls
        spider._handle_url(url)

        logger_mock.assert_any_call('url %s has already been processed', url)

        # cleanup
        spider._cleanup()

    def test_should_read_file_content_when_giving_a_file_url(self, tmp_path):
        parse_args = []
        hello_file = tmp_path / 'hello.txt'
        hello_file.write_text('Hello world!')
        file_url = hello_file.resolve().as_uri()

        def parse(sel_spider, response):
            parse_args.extend([sel_spider, response])

        spider = SeleniumSpider(urls=[file_url], parse=parse, config=Configuration(selenium_driver_log_file=None))
        spider._handle_url(file_url)

        assert parse_args[0] is spider
        sel_response = parse_args[1]
        assert isinstance(sel_response, SeleniumResponse)
        assert '<body><pre>Hello world!</pre></body>' in sel_response.driver.page_source
        assert {file_url} == spider.reachable_urls
        assert set() == spider.unreachable_urls
        assert 1 == spider.request_counter
        assert spider._total_fetch_time > 0

        # cleanup
        spider._cleanup()

    def test_should_not_call_parse_method_when_file_cannot_be_opened(self, mocker, tmp_path):
        logger_mock = mocker.patch('logging.Logger.exception')
        hello_file = tmp_path / 'hello.txt'
        file_url = hello_file.resolve().as_uri()
        parse_args = []

        def parse(sel_spider, response):
            parse_args.extend([sel_spider, response])

        spider = SeleniumSpider(urls=[file_url], parse=parse, config=Configuration(selenium_driver_log_file=None))
        spider._handle_url(file_url)

        assert [] == parse_args
        logger_mock.assert_any_call(f'unable to open file {file_url}')
        assert {file_url} == spider.unreachable_urls
        assert set() == spider.reachable_urls
        assert 0 == spider.request_counter == spider._total_fetch_time

        # cleanup
        spider._cleanup()

    @respx.mock
    def test_should_not_called_parse_method_if_url_is_forbidden_by_robots_txt(self, mocker):
        parse_args = []
        url = 'http://foo.com'

        def parse(sel_spider, response):
            parse_args.extend([sel_spider, response])

        respx.get(f'{url}/robots.txt') % 401
        logger_mock = mocker.patch('logging.Logger.info')
        config = Configuration(follow_robots_txt=True, selenium_driver_log_file=None)
        spider = SeleniumSpider(urls=[url], parse=parse, config=config)
        spider._handle_url(url)

        assert [] == parse_args
        assert {url} == spider.robots_excluded_urls
        logger_mock.assert_any_call(
            'robots.txt rule has forbidden the processing of url %s or the url is not reachable', url
        )

        # cleanup
        spider._cleanup()

    @respx.mock
    def test_should_not_called_parse_method_if_url_is_not_accessible(self, mocker):
        parse_args = []
        url = 'http://foo.com'

        def parse(sel_spider, response):
            parse_args.extend([sel_spider, response])

        respx.get(f'{url}/robots.txt') % 404
        mocker.patch('selenium.webdriver.remote.webdriver.WebDriver.get', side_effect=WebDriverException)
        config = Configuration(follow_robots_txt=True, selenium_driver_log_file=None)
        spider = SeleniumSpider(urls=[url], parse=parse, config=config)
        spider._handle_url(url)

        assert [] == parse_args
        assert {url} == spider.unreachable_urls
        assert set() == spider.reachable_urls
        assert 0 == spider.request_counter == spider._total_fetch_time

        # cleanup
        spider._cleanup()

    @respx.mock
    def test_should_fetch_content_when_giving_http_url(self, mocker):
        parse_args = []
        url = 'http://foo.com'

        def parse(sel_spider, response):
            parse_args.extend([sel_spider, response])

        respx.get(f'{url}/robots.txt') % 404
        mocker.patch('selenium.webdriver.remote.webdriver.WebDriver.get')
        mocker.patch('selenium.webdriver.remote.webdriver.WebDriver.current_window_handle', 'handle')
        config = Configuration(follow_robots_txt=True, selenium_driver_log_file=None)
        spider = SeleniumSpider(urls=[url], parse=parse, config=config)
        spider._handle_url(url)

        assert parse_args[0] is spider
        selenium_response = parse_args[1]
        assert isinstance(selenium_response, SeleniumResponse)
        assert selenium_response.driver is spider._driver
        assert 'handle' == selenium_response.handle
        assert {url} == spider.reachable_urls
        assert set() == spider.unreachable_urls
        assert 1 == spider.request_counter
        assert spider._total_fetch_time > 0

        # cleanup
        spider._cleanup()

    def test_should_raise_error_if_parse_function_raises_error_and_ignore_errors_is_false(self, mocker):
        def parse(*_):
            raise ValueError('simple error')

        url = 'http://foo.com'
        mocker.patch('selenium.webdriver.remote.webdriver.WebDriver.get')
        config = Configuration(selenium_driver_log_file=None)
        spider = SeleniumSpider(urls=[url], parse=parse, config=config, ignore_errors=False)

        with pytest.raises(ValueError) as exc_info:
            spider._handle_url(url)

        assert 'simple error' == str(exc_info.value)

        # cleanup
        spider._cleanup()

    def test_should_not_raise_error_if_parse_function_raises_error_and_ignore_errors_is_true(self, mocker):
        def parse(*_):
            raise ValueError('simple error')

        url = 'http://foo.com'
        mocker.patch('selenium.webdriver.remote.webdriver.WebDriver.get')
        config = Configuration(selenium_driver_log_file=None)
        spider = SeleniumSpider(urls=[url], parse=parse, config=config, ignore_errors=True)

        try:
            spider._handle_url(url)
        except ValueError:
            pytest.fail('unexpected ValueError raised when ignore_errors is set to true')

        # cleanup
        spider._cleanup()


class TestIntegrationSeleniumSpider:
    @staticmethod
    def processor(item: dict) -> dict:
        item['date'] = datetime.now()
        return item

    @staticmethod
    def parse(spider: SeleniumSpider, response: SeleniumResponse) -> None:
        quotes = [element.text for element in response.driver.find_elements_by_xpath('//blockquote/p')]
        authors = [element.text for element in response.driver.find_elements_by_xpath('//blockquote/footer')]
        for quote, author in zip(quotes, authors):
            spider.save_item({'quote': quote, 'author': author})

        link = None
        try:
            element = response.driver.find_element_by_xpath('//a[2][contains(@href, "page")]')
            link = element.get_attribute('href')
        except NoSuchElementException:
            pass

        if link is not None:
            response.follow(link)

    @pytest.mark.parametrize('browser', [Browser.FIREFOX, Browser.CHROME])
    def test_should_save_correct_output_when_giving_file_url(self, page_1_file_url, tmp_path, browser):
        backup_path = tmp_path / 'backup.mp'
        config = Configuration(
            item_processors=[self.processor],
            backup_filename=f'{backup_path}',
            selenium_driver_log_file=None,
            selenium_browser=browser,
        )
        spider = SeleniumSpider(urls=[page_1_file_url], parse=self.parse, config=config)
        spider.run()
        stats = spider.statistics()
        followed_urls = {page_1_file_url.replace('1', '2'), page_1_file_url.replace('1', '3')}

        assert followed_urls == stats.followed_urls
        assert {page_1_file_url} | followed_urls == stats.reachable_urls
        assert 3 == stats.request_counter
        assert stats.total_time > 0
        assert stats.average_fetch_time == spider._total_fetch_time / stats.request_counter
        assert set() == stats.unreachable_urls
        assert set() == stats.robot_excluded_urls
        assert stats.total_time > 0

        albert_count = 0
        for item in read_mp(backup_path, decoder=datetime_decoder):
            assert isinstance(item['date'], datetime)
            if item['author'] == 'Albert Einstein':
                print(item)
                albert_count += 1

        assert albert_count == 3
