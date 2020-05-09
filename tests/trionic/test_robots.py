import collections
from urllib.robotparser import RobotFileParser

import httpx
import pytest
import trio
from asyncmock import AsyncMock

from scalpel.trionic.robots import RobotsAnalyzer
from tests.helpers import assert_dicts


@pytest.fixture()
def trio_analyzer(trio_tmp_path):
    return RobotsAnalyzer(user_agent='Mozilla/5.0', robots_cache=trio_tmp_path)


class TestRobotsAnalyzerInitialization:
    """Tests __init__ method"""

    def test_should_correctly_instantiate_class_without_giving_httpx_response(self, trio_tmp_path):
        analyzer = RobotsAnalyzer(user_agent='Mozilla/5.0', robots_cache=trio_tmp_path)

        assert 'Mozilla/5.0' == analyzer._user_agent
        assert trio_tmp_path == analyzer._robots_cache
        assert isinstance(analyzer._http_client, httpx.AsyncClient)
        assert 'Mozilla/5.0' == analyzer._http_client.headers['User-Agent']
        assert isinstance(analyzer._robots_parser, RobotFileParser)
        assert_dicts(analyzer._robots_mapping, {})
        assert_dicts(analyzer._delay_mapping, {})

    def test_should_correctly_instantiate_class_with_httpx_response_passed_as_argument(self, trio_tmp_path):
        http_client = httpx.AsyncClient(headers={'User-Agent': 'python-httpx'})
        analyzer = RobotsAnalyzer(
            user_agent='Mozilla/5.0',
            robots_cache=trio_tmp_path,
            http_client=http_client
        )

        assert 'Mozilla/5.0' == analyzer._user_agent
        assert trio_tmp_path == analyzer._robots_cache
        assert isinstance(analyzer._http_client, httpx.AsyncClient)
        assert 'python-httpx' == analyzer._http_client.headers['User-Agent']
        assert isinstance(analyzer._robots_parser, RobotFileParser)
        assert_dicts(analyzer._robots_mapping, {})
        assert_dicts(analyzer._delay_mapping, {})


class TestCreateRobotsFile:
    """Tests method _create_robots_file"""

    async def test_should_create_robots_file_given_host_and_content(self, trio_analyzer, robots_content):
        robots_path = trio_analyzer._robots_cache / 'foo.com'
        await trio_analyzer._create_robots_file(robots_path, robots_content)

        assert await robots_path.read_text() == robots_content


class TestGetRobotsLines:
    """Tests method _get_robots_lines"""

    async def test_should_return_robots_lines_when_giving_robots_path(self, trio_analyzer, robots_content):
        lines = ['Hello word\n', 'Just a good day']
        robots_path = trio_analyzer._robots_cache / 'foo.com'
        await robots_path.write_text(''.join(lines))

        assert await trio_analyzer._get_robots_lines(robots_path) == lines


class TestCanFetch:
    """Tests method can_fetch"""

    async def test_should_return_false_when_host_does_not_exist(self, trio_analyzer):
        trio_analyzer._http_client.get = AsyncMock(side_effect=httpx.ConnectTimeout)

        assert await trio_analyzer.can_fetch('http://example.com/path') is False

    @pytest.mark.parametrize('status_code', [401, 403])
    async def test_should_return_false_when_robots_is_unauthorized_or_forbidden(self, trio_analyzer, get_response,
                                                                                status_code):
        trio_analyzer._http_client.get = get_response(status_code=status_code)

        assert await trio_analyzer.can_fetch('http://example.com/path') is False

    @pytest.mark.parametrize('status_code', [404, 500])
    async def test_should_return_true_when_other_http_errors_occurred(self, trio_analyzer, get_response, status_code):
        trio_analyzer._http_client.get = get_response(status_code=status_code)

        assert await trio_analyzer.can_fetch('http://example.com/path') is True

    @pytest.mark.parametrize('url_path', ['photos', 'videos'])
    async def test_should_return_false_when_requesting_forbidden_url(self, trio_analyzer, get_response, trio_tmp_path,
                                                                     robots_content, url_path):
        analyzer = RobotsAnalyzer(user_agent='Googlebot', robots_cache=trio_tmp_path)
        analyzer._http_client.get = get_response(content=robots_content)

        assert await analyzer.can_fetch(f'http://example.com/{url_path}/1') is False

    @pytest.mark.parametrize('url_path', ['admin/', 'ajax/'])
    async def test_should_return_true_when_requesting_allowed_url(self, trio_analyzer, get_response, trio_tmp_path,
                                                                  robots_content, url_path):
        analyzer = RobotsAnalyzer(user_agent='Googlebot', robots_cache=trio_tmp_path)
        analyzer._http_client.get = get_response(content=robots_content)

        assert await analyzer.can_fetch(f'http://example.com/{url_path}') is True

    async def test_should_not_enter_if_block_if_robots_content_is_already_cached(self, trio_analyzer, trio_tmp_path,
                                                                                 robots_content, get_response):
        robots_path = trio_tmp_path / 'example.com'
        await robots_path.write_text(robots_content)
        trio_analyzer._robots_mapping['example.com'] = robots_path
        get_mock = get_response()
        trio_analyzer._http_client.get = get_mock

        assert await trio_analyzer.can_fetch(f'http://example.com/path') is True
        get_mock.assert_not_called()


class TestGetRequestDelay:
    """Tests method get_request_delay"""

    async def test_should_return_delay_if_it_is_in_internal_delay_mapping(self, mocker, trio_tmp_path):
        crawl_delay_mock = mocker.patch('urllib.robotparser.RobotFileParser.crawl_delay')
        can_fetch_mock = mocker.patch('scalpel.trionic.robots.RobotsAnalyzer.can_fetch')
        delay = 2
        analyzer = RobotsAnalyzer(robots_cache=trio_tmp_path, user_agent='Mozilla/5.0')
        analyzer._delay_mapping['example.com'] = delay

        assert await analyzer.get_request_delay('http://example.com/page/1', 0) == delay
        can_fetch_mock.assert_not_called()
        crawl_delay_mock.assert_not_called()

    async def test_should_return_negative_value_when_url_is_not_fetchable(self, trio_analyzer, get_response):
        trio_analyzer._http_client.get = get_response(status_code=401)

        assert await trio_analyzer.get_request_delay('http://example.com/page/1', 0) == -1

    async def test_should_call_can_fetch_only_one_time(self, monkeypatch, trio_tmp_path):
        url = 'http://example.com/page/1'
        count = 0

        async def fake_can_fetch(*_):
            await trio.sleep(0)
            nonlocal count
            count += 1

        monkeypatch.setattr(RobotsAnalyzer, 'can_fetch', fake_can_fetch)
        analyzer = RobotsAnalyzer(robots_cache=trio_tmp_path, user_agent='Mozilla/5.0')

        assert await analyzer.get_request_delay(url, 0) == -1
        assert await analyzer.get_request_delay(url, 0) == -1
        assert count == 1

    async def test_should_return_crawl_delay_value_if_robots_txt_specified_it(self, trio_analyzer, robots_content,
                                                                              get_response):
        new_content = robots_content + '\nCrawl-delay: 2'
        trio_analyzer._http_client.get = get_response(content=new_content)

        assert await trio_analyzer.get_request_delay('http://example.com/page/1', 0) == 2

    async def test_should_call_crawl_delay_method_only_one_time(self, mocker, trio_analyzer, robots_content):
        crawl_delay_mock = mocker.patch('urllib.robotparser.RobotFileParser.crawl_delay', return_value=2)

        assert await trio_analyzer.get_request_delay('http://example.com/page/1', 0) == 2
        assert await trio_analyzer.get_request_delay('http://example.com/page/1', 0) == 2
        crawl_delay_mock.assert_called_once_with('*')

    async def test_should_return_request_rate_if_robots_txt_specified_it(self, robots_content, trio_analyzer,
                                                                         get_response):
        new_content = robots_content + '\nRequest-rate: 2/5'
        trio_analyzer._http_client.get = get_response(content=new_content)

        assert await trio_analyzer.get_request_delay('http://example.com/page/1', 0) == 2.5

    async def test_should_call_request_rate_method_only_one_time(self, mocker, robots_content, trio_analyzer,
                                                                 get_response):
        trio_analyzer._http_client.get = get_response(content=robots_content)
        RequestRate = collections.namedtuple('RequestRate', 'requests seconds')
        request_rate = RequestRate(2, 5)
        request_rate_mock = mocker.patch('urllib.robotparser.RobotFileParser.request_rate', return_value=request_rate)

        assert await trio_analyzer.get_request_delay('http://example.com/page/1', 0) == 2.5
        assert await trio_analyzer.get_request_delay('http://example.com/page/1', 0) == 2.5
        request_rate_mock.assert_called_once_with('*')

    async def test_should_return_given_delay_if_no_crawl_delay_or_request_rate_are_given(self, trio_analyzer,
                                                                                         get_response, robots_content):
        trio_analyzer._http_client.get = get_response(content=robots_content)

        assert await trio_analyzer.get_request_delay('http://example.com/page/1', 3) == 3

    async def test_should_return_cache_given_delay_if_compatible_url_is_called_twice(self, mocker, get_response,
                                                                                     robots_content, trio_analyzer):
        crawl_delay_mock = mocker.patch('urllib.robotparser.RobotFileParser.crawl_delay', return_value=None)
        trio_analyzer._http_client.get = get_response(content=robots_content)

        assert await trio_analyzer.get_request_delay('http://example.com/page/1', 3) == 3
        assert await trio_analyzer.get_request_delay('http://example.com/page/1', 3) == 3
        crawl_delay_mock.assert_called_once_with('*')


class TestClose:
    """Tests method close"""

    async def test_should_call_http_client_aclose_method(self, monkeypatch, trio_tmp_path):
        called = False

        async def aclose(*_):
            await trio.sleep(0)
            nonlocal called
            called = True

        monkeypatch.setattr(httpx.AsyncClient, 'aclose', aclose)
        analyzer = RobotsAnalyzer(user_agent='Mozilla/5.0', robots_cache=trio_tmp_path)
        await analyzer.close()

        assert called
