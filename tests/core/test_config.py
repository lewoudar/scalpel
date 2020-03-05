import pytest
from fake_useragent import FakeUserAgentError

from scalpel.core.config import Configuration


@pytest.fixture(scope='module')
def default_config():
    return Configuration()


@pytest.mark.parametrize(('attribute', 'value'), [
    ('min_request_delay', -1),
    ('max_request_delay', -1),
    ('fetch_timeout', -1.0),
    ('selenium_find_timeout', -1.0)
])
def test_should_raise_error_when_value_is_less_than_0(attribute, value):
    with pytest.raises(ValueError) as exc_info:
        Configuration(**{attribute: value})

    assert f'{attribute} must be a positive integer' == str(exc_info.value)


class TestRequestDelayAttributes:
    """Checks min_delay_request and max_delay_request attributes"""

    @pytest.mark.parametrize('parameter', [
        {'min_request_delay': '1'},
        {'max_request_delay': '1'},
        {'min_request_delay': 1.5},
        {'max_request_delay': 1.5},
    ])
    def test_should_raise_error_when_value_is_not_an_integer(self, parameter):
        with pytest.raises(TypeError):
            Configuration(**parameter)

    def test_default_value_is_0(self, default_config):
        assert 0 == default_config.min_request_delay
        assert 0 == default_config.max_request_delay

    def test_config_fails_when_min_delay_greater_than_max_delay(self):
        with pytest.raises(ValueError) as exc_info:
            Configuration(min_request_delay=1, max_request_delay=0)

        assert 'max_request_delay must be greater or equal than min_request_delay' == str(exc_info.value)

    def test_config_does_not_fail_when_min_delay_equals_max_delay(self):
        try:
            Configuration(min_request_delay=1, max_request_delay=1)
        except ValueError:
            pytest.fail('unexpected error when min delay and max delay equal to 1')


class TestTimeoutAttributes:

    @pytest.mark.parametrize('parameter', [
        {'fetch_timeout': '1.0'},
        {'fetch_timeout': 1},
        {'selenium_find_timeout': '1.0'},
        {'selenium_find_timeout': 1}
    ])
    def test_should_raise_error_when_timeout_is_not_float(self, parameter):
        with pytest.raises(TypeError):
            Configuration(**parameter)

    def test_fetch_timeout_default_value_is_5(self, default_config):
        assert 5.0 == default_config.fetch_timeout

    def test_selenium_find_timeout_default_value_is_10(self, default_config):
        assert 10.0 == default_config.selenium_find_timeout


# noinspection PyTypeChecker
class TestUserAgentAttribute:
    """Checks attribute user_agent"""

    @pytest.mark.parametrize('value', [1, 1.0])
    def test_should_raise_error_when_value_is_not_a_string(self, value):
        with pytest.raises(TypeError):
            Configuration(user_agent=value)

    # todo: may be I should mock UserAgent to prevent failures when the sources
    #  can't be downloaded. Or skipped test if it is not run on CI?
    def test_default_value_is_a_string_when_fake_user_agent_does_not_fail(self, default_config):
        assert isinstance(default_config.user_agent, str)

    def test_default_value_is_a_string_when_fake_user_agent_fails(self, mocker):
        class FailUserAgent:
            def __init__(self):
                raise FakeUserAgentError

        mocker.patch('scalpel.core.config.UserAgent', new=FailUserAgent)

        config = Configuration()
        assert config.user_agent.startswith('Mozilla/5.0')


# noinspection PyTypeChecker
class TestFollowRobotsTxt:
    """Checks attribute follow_robots_txt"""

    @pytest.mark.parametrize('value', [1, 'true', 1.0])
    def test_should_raise_error_when_value_is_not_a_boolean(self, value):
        with pytest.raises(TypeError):
            Configuration(follow_robots_txt=value)

    def test_default_value_is_false(self, default_config):
        assert default_config.follow_robots_txt is False


class TestMiddlewareAttributes:
    """Checks attributes response_middlewares and process_item_middlewares"""

    @pytest.mark.parametrize('parameter', [
        {'response_middlewares': {}},
        {'response_middlewares': set()},
        {'process_item_middlewares': {}},
        {'process_item_middlewares': set()}
    ])
    def test_should_raise_error_when_value_is_not_a_sequence(self, parameter):
        with pytest.raises(TypeError):
            Configuration(**parameter)

    @pytest.mark.parametrize('parameter', [
        {'response_middlewares': [lambda x: x, 'foo']},
        {'process_item_middlewares': (lambda x: x, 'bar')}
    ])
    def test_should_raise_error_when_item_in_iterable_is_not_a_callable(self, parameter):
        with pytest.raises(TypeError):
            Configuration(**parameter)

    @pytest.mark.parametrize('parameter', [
        {'response_middlewares': [lambda x: x]},
        {'response_middlewares': (lambda x: x,)},
        {'process_item_middlewares': [lambda x: x]},
        {'process_item_middlewares': (lambda x: x,)}
    ])
    def test_should_not_raise_error_when_giving_correct_sequence(self, parameter):
        try:
            Configuration(**parameter)
        except TypeError as e:
            pytest.fail(f'unexpected error: {e}')

    def test_default_middleware_value_is_an_empty_list(self, default_config):
        assert [] == default_config.response_middlewares
        assert [] == default_config.process_item_middlewares
