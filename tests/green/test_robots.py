import collections
from urllib.robotparser import RobotFileParser

import httpx
import pytest
import respx
from gevent.lock import RLock

from scalpel.green.robots import RobotsAnalyzer
from tests.helpers import assert_dicts


@pytest.fixture()
def robots_mapping_lock_mock(mocker):
    return mocker.patch('gevent.lock.RLock')


@pytest.fixture()
def delay_mapping_lock_mock(mocker):
    return mocker.patch('gevent.lock.RLock')


@pytest.fixture()
def default_analyzer(tmp_path, robots_mapping_lock_mock, delay_mapping_lock_mock):
    return RobotsAnalyzer(
        user_agent='Mozilla/5.0',
        robots_cache=tmp_path,
        robots_mapping_lock=robots_mapping_lock_mock,
        delay_mapping_lock=delay_mapping_lock_mock
    )


class TestRobotsAnalyzerInstantiation:
    """Tests __init__ method"""

    def test_should_correctly_instantiate_class_without_giving_httpx_response(self, tmp_path):
        analyzer = RobotsAnalyzer(user_agent='Mozilla/5.0', robots_cache=tmp_path)

        assert 'Mozilla/5.0' == analyzer._user_agent
        assert tmp_path == analyzer._robots_cache
        assert isinstance(analyzer._http_client, httpx.Client)
        assert 'Mozilla/5.0' == analyzer._http_client.headers['User-Agent']
        assert isinstance(analyzer._robots_parser, RobotFileParser)
        assert isinstance(analyzer._robots_mapping_lock, RLock)
        assert isinstance(analyzer._delay_mapping_lock, RLock)
        assert_dicts(analyzer._robots_mapping, {})
        assert_dicts(analyzer._delay_mapping, {})

    def test_should_correctly_instantiate_class_with_httpx_response_passed_as_argument(self, tmp_path):
        http_client = httpx.Client(headers={'User-Agent': 'python-httpx'})
        analyzer = RobotsAnalyzer(
            user_agent='Mozilla/5.0',
            robots_cache=tmp_path,
            http_client=http_client
        )

        assert 'Mozilla/5.0' == analyzer._user_agent
        assert tmp_path == analyzer._robots_cache
        assert isinstance(analyzer._http_client, httpx.Client)
        assert 'python-httpx' == analyzer._http_client.headers['User-Agent']
        assert isinstance(analyzer._robots_parser, RobotFileParser)
        assert isinstance(analyzer._robots_mapping_lock, RLock)
        assert isinstance(analyzer._delay_mapping_lock, RLock)
        assert_dicts(analyzer._robots_mapping, {})
        assert_dicts(analyzer._delay_mapping, {})


class TestCreateRobotsFile:
    """Tests method _create_robots_file"""

    def test_should_create_robots_file_given_host_and_content(self, default_analyzer, robots_content):
        robots_path = default_analyzer._robots_cache / 'foo.com'
        default_analyzer._create_robots_file(robots_path, robots_content)

        assert robots_path.read_text() == robots_content


class TestGetRobotsLine:
    """Tests method _get_robots_lines"""

    def test_should_return_robots_lines_when_giving_robots_path(self, default_analyzer, robots_content):
        lines = ['Hello word\n', 'Just a good day']
        robots_path = default_analyzer._robots_cache / 'foo.com'
        robots_path.write_text(''.join(lines))

        assert lines == default_analyzer._get_robots_lines(robots_path)


class TestCanFetch:
    """Tests method can_fetch"""

    def test_should_return_false_when_host_does_not_exist(self, default_analyzer, httpx_mock):
        httpx_mock.get('/robots.txt', content=httpx.ConnectTimeout())

        assert default_analyzer.can_fetch('http://example.com/path') is False
        assert 1 == len(default_analyzer._robots_mapping_lock.__enter__.mock_calls)
        assert 1 == len(default_analyzer._robots_mapping_lock.__exit__.mock_calls)

    @pytest.mark.parametrize('code', [401, 403])
    def test_should_return_false_when_robots_is_unauthorized_or_forbidden(self, default_analyzer, httpx_mock, code):
        httpx_mock.get('/robots.txt', status_code=code)
        assert default_analyzer.can_fetch('http://example.com/') is False

    @pytest.mark.parametrize('code', [404, 500])
    def test_should_return_true_when_other_http_errors_occurred(self, default_analyzer, httpx_mock, code):
        httpx_mock.get('/robots.txt', status_code=code)
        assert default_analyzer.can_fetch('http://example.com/') is True

    @pytest.mark.parametrize('url_path', ['photos', 'videos'])
    def test_should_return_false_when_requesting_forbidden_url(self, httpx_mock, tmp_path, robots_content, url_path,
                                                               robots_mapping_lock_mock, delay_mapping_lock_mock):
        analyzer = RobotsAnalyzer(
            user_agent='Googlebot',
            robots_cache=tmp_path,
            robots_mapping_lock=robots_mapping_lock_mock,
            delay_mapping_lock=delay_mapping_lock_mock
        )
        httpx_mock.get('/robots.txt', content=robots_content)

        assert analyzer.can_fetch(f'http://example.com/{url_path}/1') is False
        assert 2 == len(analyzer._robots_mapping_lock.__enter__.mock_calls)
        assert 2 == len(analyzer._robots_mapping_lock.__exit__.mock_calls)

    @pytest.mark.parametrize('url_path', ['admin/', 'ajax/'])
    def test_should_return_true_when_requesting_allowed_url(self, httpx_mock, tmp_path, robots_content, url_path,
                                                            robots_mapping_lock_mock, delay_mapping_lock_mock):
        analyzer = RobotsAnalyzer(
            user_agent='Googlebot',
            robots_cache=tmp_path,
            robots_mapping_lock=robots_mapping_lock_mock,
            delay_mapping_lock=delay_mapping_lock_mock
        )
        httpx_mock.get('/robots.txt', content=robots_content)

        assert analyzer.can_fetch(f'http://example.com/{url_path}') is True
        assert 2 == len(analyzer._robots_mapping_lock.__enter__.mock_calls)
        assert 2 == len(analyzer._robots_mapping_lock.__exit__.mock_calls)

    @respx.mock
    def test_should_not_enter_if_block_if_robots_content_is_already_cached(self, default_analyzer, tmp_path,
                                                                           robots_content):
        request = respx.get('http://example.com/robots.txt')
        robots_path = tmp_path / 'example.com'
        robots_path.write_text(robots_content)
        default_analyzer._robots_mapping['example.com'] = tmp_path / 'example.com'

        assert default_analyzer.can_fetch('http://example.com/path') is True
        assert not request.called


class TestGetRequestDelay:
    """Tests method get_request_delay"""

    # tests get_request_delay

    def test_should_return_delay_if_it_is_in_internal_delay_mapping(self, mocker, tmp_path, delay_mapping_lock_mock):
        crawl_delay_mock = mocker.patch('urllib.robotparser.RobotFileParser.crawl_delay')
        can_fetch_mock = mocker.patch('scalpel.green.robots.RobotsAnalyzer.can_fetch')
        delay = 2
        analyzer = RobotsAnalyzer(
            robots_cache=tmp_path,
            user_agent='Mozilla/5.0',
            delay_mapping_lock=delay_mapping_lock_mock
        )
        analyzer._delay_mapping['example.com'] = delay

        assert delay == analyzer.get_request_delay('http://example.com/page/1', 0)
        can_fetch_mock.assert_not_called()
        crawl_delay_mock.assert_not_called()
        assert 1 == len(analyzer._delay_mapping_lock.__enter__.mock_calls)
        assert 1 == len(analyzer._delay_mapping_lock.__exit__.mock_calls)

    def test_should_return_negative_value_when_url_is_not_fetchable(self, default_analyzer, httpx_mock):
        httpx_mock.get('/robots.txt', status_code=401)

        assert -1 == default_analyzer.get_request_delay('http://example.com/page/1', 0)

        assert 2 == len(default_analyzer._robots_mapping_lock.__enter__.mock_calls)
        assert 2 == len(default_analyzer._robots_mapping_lock.__exit__.mock_calls)
        assert 2 == len(default_analyzer._delay_mapping_lock.__enter__.mock_calls)
        assert 2 == len(default_analyzer._delay_mapping_lock.__exit__.mock_calls)

    def test_should_call_can_fetch_only_one_time(self, mocker, tmp_path):
        url = 'http://example.com/page/1'
        can_fetch_mock = mocker.patch('scalpel.green.robots.RobotsAnalyzer.can_fetch', return_value=False)
        analyzer = RobotsAnalyzer(robots_cache=tmp_path, user_agent='Mozilla/5.0')

        assert -1 == analyzer.get_request_delay(url, 0)
        assert -1 == analyzer.get_request_delay(url, 0)
        can_fetch_mock.assert_called_once_with(url)

    def test_should_return_crawl_delay_value_if_robots_txt_specified_it(self, default_analyzer, httpx_mock,
                                                                        robots_content):
        new_content = robots_content + '\nCrawl-delay: 2'
        httpx_mock.get('/robots.txt', content=new_content)

        assert 2 == default_analyzer.get_request_delay('http://example.com/page/1', 0)

        assert 3 == len(default_analyzer._robots_mapping_lock.__enter__.mock_calls)
        assert 3 == len(default_analyzer._robots_mapping_lock.__exit__.mock_calls)
        assert 2 == len(default_analyzer._delay_mapping_lock.__enter__.mock_calls)
        assert 2 == len(default_analyzer._delay_mapping_lock.__exit__.mock_calls)

    def test_should_call_crawl_delay_method_only_one_time(self, mocker, default_analyzer, robots_content, httpx_mock):
        httpx_mock.get('/robots.txt', content=robots_content)
        crawl_delay_mock = mocker.patch('urllib.robotparser.RobotFileParser.crawl_delay', return_value=2)

        assert 2 == default_analyzer.get_request_delay('http://example.com/page/1', 0)
        assert 2 == default_analyzer.get_request_delay('http://example.com/page/1', 0)
        crawl_delay_mock.assert_called_once_with('*')

    def test_should_return_request_rate_if_robots_txt_specified_it(self, default_analyzer, httpx_mock, robots_content):
        new_content = robots_content + '\nRequest-rate: 2/5'
        httpx_mock.get('/robots.txt', content=new_content)

        assert 2.5 == default_analyzer.get_request_delay('http://example.com/page/1', 0)

        assert 3 == len(default_analyzer._robots_mapping_lock.__enter__.mock_calls)
        assert 3 == len(default_analyzer._robots_mapping_lock.__exit__.mock_calls)
        assert 2 == len(default_analyzer._delay_mapping_lock.__enter__.mock_calls)
        assert 2 == len(default_analyzer._delay_mapping_lock.__exit__.mock_calls)

    def test_should_call_request_rate_method_only_one_time(self, mocker, default_analyzer, httpx_mock, robots_content):
        httpx_mock.get('/robots.txt', content=robots_content)
        RequestRate = collections.namedtuple('RequestRate', 'requests seconds')
        request_rate = RequestRate(2, 5)
        request_rate_mock = mocker.patch('urllib.robotparser.RobotFileParser.request_rate', return_value=request_rate)

        assert 2.5 == default_analyzer.get_request_delay('http://example.com/page/1', 0)
        assert 2.5 == default_analyzer.get_request_delay('http://example.com/page/1', 0)
        request_rate_mock.assert_called_once_with('*')

    def test_should_return_given_delay_if_no_crawl_delay_or_request_rate_are_given(self, default_analyzer, httpx_mock,
                                                                                   robots_content):
        httpx_mock.get('/robots.txt', content=robots_content)

        assert 3 == default_analyzer.get_request_delay('http://example.com/page/1', 3)

        assert 3 == len(default_analyzer._robots_mapping_lock.__enter__.mock_calls)
        assert 3 == len(default_analyzer._robots_mapping_lock.__exit__.mock_calls)
        assert 2 == len(default_analyzer._delay_mapping_lock.__enter__.mock_calls)
        assert 2 == len(default_analyzer._delay_mapping_lock.__exit__.mock_calls)

    def test_should_return_cache_given_delay_if_compatible_url_is_called_twice(self, default_analyzer, httpx_mock,
                                                                               robots_content):
        httpx_mock.get('/robots.txt', content=robots_content)

        assert 3 == default_analyzer.get_request_delay('http://example.com/page/1', 3)
        assert 3 == default_analyzer.get_request_delay('http://example.com/page/1', 3)
        # we check that the _delay_mapping_lock is not called 2 * 2 times to ensure that
        # the cache value is returned
        assert 3 == len(default_analyzer._delay_mapping_lock.__enter__.mock_calls)
        assert 3 == len(default_analyzer._delay_mapping_lock.__exit__.mock_calls)

    @respx.mock
    def test_should_not_call_can_fetch_method_if_robots_content_is_already_cached(self, default_analyzer, tmp_path,
                                                                                  robots_content):
        request = respx.get('http://example.com/robots.txt')
        robots_path = tmp_path / 'example.com'
        robots_path.write_text(robots_content)
        default_analyzer._robots_mapping['example.com'] = tmp_path / 'example.com'

        assert 3 == default_analyzer.get_request_delay('http://example.com/page/1', 3)
        assert not request.called


class TestClose:
    """Tests method close"""

    def test_should_call_http_client_close_method(self, mocker, tmp_path, robots_content, robots_mapping_lock_mock,
                                                  delay_mapping_lock_mock):
        http_client_mock = mocker.MagicMock()
        analyzer = RobotsAnalyzer(
            robots_cache=tmp_path,
            user_agent='Mozilla/5.0',
            http_client=http_client_mock,
            delay_mapping_lock=delay_mapping_lock_mock,
            robots_mapping_lock=robots_mapping_lock_mock
        )
        analyzer.close()

        http_client_mock.close.assert_called_once()
