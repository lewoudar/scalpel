from urllib.robotparser import RobotFileParser

import pytest

from scalpel.core.robots import RobotsMixin


@pytest.fixture()
def get_robots_parser(robots_content):
    def _get_robots_parser(additional_content: str = '') -> RobotFileParser:
        new_content = robots_content + additional_content
        robots = RobotFileParser()
        robots.parse(new_content.split('\n'))
        return robots

    return _get_robots_parser


class TestGetRequestDelay:
    """Tests method get_request_delay"""

    url = 'example.com/foo'
    host = 'example.com'

    def test_should_return_crawl_delay_value_if_robots_txt_specified_it(self, get_robots_parser):
        robots_parser = get_robots_parser('\nCrawl-delay: 2')
        delay_mapping = {}

        assert 2 == RobotsMixin._get_request_delay(self.host, self.url, robots_parser, delay_mapping, 1)
        assert {self.host: 2} == delay_mapping

    def test_should_return_request_rate_if_robots_txt_specified_it(self, get_robots_parser):
        robots_parser = get_robots_parser('\nRequest-rate: 2/5')
        delay_mapping = {}

        assert 2.5 == RobotsMixin._get_request_delay(self.host, self.url, robots_parser, delay_mapping, 1)
        assert {self.host: 2.5} == delay_mapping

    def test_should_return_default_delay_if_no_crawl_delay_or_request_rate_are_given(self, get_robots_parser):
        robots_parser = get_robots_parser()
        delay_mapping = {}

        assert 1 == RobotsMixin._get_request_delay(self.host, self.url, robots_parser, delay_mapping, 1)
        assert {self.host: 1} == delay_mapping
