import sys
import tempfile
from importlib import import_module
from pathlib import Path

import pytest
from configuror import DecodeError
from fake_useragent import FakeUserAgentError

from scalpel.core.config import Configuration, bool_converter, callable_list_converter
from scalpel.core.message_pack import datetime_decoder, datetime_encoder
from tests.helpers import assert_dicts


@pytest.fixture(scope='module')
def default_config():
    config = Configuration()
    path = Path(config.robots_cache_folder)
    yield config
    if path.exists():
        path.rmdir()


@pytest.fixture
def math_module(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'path', [*sys.path, f'{tmp_path}'])
    python_file = tmp_path / 'custom_math.py'
    lines = """
def add(a, b):
    return a + b

def minus(a, b):
    return a - b
    """
    python_file.write_text(lines)
    return import_module(python_file.stem)


class TestBoolConverter:
    """Tests helper function bool_converter"""

    @pytest.mark.parametrize('value', [b'1', 1, 1.0])
    def test_should_return_given_value_if_it_is_not_a_string(self, value):
        assert value == bool_converter(value)

    @pytest.mark.parametrize('value', ['y', 'yes', '1', 'True', 'TRUE'])
    def test_should_return_true_when_value_represent_truthy(self, value):
        assert bool_converter(value) is True

    @pytest.mark.parametrize('value', ['n', 'no', '0', 'FALSE', 'false'])
    def test_should_return_false_when_value_does_not_represent_truthy(self, value):
        assert bool_converter(value) is False

    @pytest.mark.parametrize('value', ['fal', 'hello'])
    def test_should_raise_error_when_value_does_not_represent_true_or_false(self, value):
        with pytest.raises(ValueError) as exc_info:
            bool_converter(value)

        assert f'{value} does not represent a boolean' == str(exc_info.value)


class TestCallableListConverter:
    """Tests helper function callable_list_converter"""

    @pytest.mark.parametrize('value', [{}, set(), b'foo', ['foo', 2]])
    def test_should_return_given_value_if_it_is_not_a_string_or_list_of_strings(self, value):
        assert value == callable_list_converter(value)

    def test_should_raise_error_when_module_does_not_exist(self):
        with pytest.raises(ModuleNotFoundError):
            callable_list_converter('foo.bar')

    def test_should_raise_error_when_module_is_badly_formatted(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, 'path', [*sys.path, f'{tmp_path}'])
        dummy_file = tmp_path / 'foo.py'
        dummy_file.write_text('hello world')

        with pytest.raises(SyntaxError):
            callable_list_converter('foo.callable')

    def test_should_raise_error_when_callable_does_not_exist(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, 'path', [*sys.path, f'{tmp_path}'])
        dummy_file = tmp_path / 'foo.py'
        dummy_file.write_text('hello = "world"')

        with pytest.raises(AttributeError):
            callable_list_converter('foo.bar')

    @pytest.mark.parametrize('callable_string', [
        'custom_math.add:custom_math.minus',
        'custom_math.add, custom_math.minus',
        'custom_math.add;  custom_math.minus',
        'custom_math.add custom_math.minus'
    ])
    def test_should_return_correct_list_of_callable_when_given_correct_string_input(self, math_module, callable_string):
        assert [math_module.add, math_module.minus] == callable_list_converter(callable_string)

    def test_should_return_correct_list_of_callable_when_given_correct_list_input(self, math_module):
        assert [math_module.minus, math_module.add] == callable_list_converter(['custom_math.minus', 'custom_math.add'])


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
    """
    Checks min_delay_request and max_delay_request attributes.
    Checks request_delay property
    """

    @pytest.mark.parametrize('parameter', [
        {'min_request_delay': 'foo'},
        {'max_request_delay': 'foo'}
    ])
    def test_should_raise_error_when_value_does_not_represent_integer(self, parameter):
        with pytest.raises(ValueError):
            Configuration(**parameter)

    # noinspection PyTypeChecker
    @pytest.mark.parametrize(('min_delay', 'max_delay'), [
        ('1', '2'),
        (1.5, 2.1)
    ])
    def test_should_convert_string_or_float_to_integer(self, min_delay, max_delay):
        config = Configuration(min_request_delay=min_delay, max_request_delay=max_delay)
        assert 1 == config.min_request_delay
        assert 2 == config.max_request_delay

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

    @pytest.mark.parametrize(('min_delay', 'max_delay'), [
        (1, 1),
        (2, 5),
    ])
    def test_request_property_is_between_min_and_max_delay(self, min_delay, max_delay):
        config = Configuration(min_request_delay=min_delay, max_request_delay=max_delay)

        assert config.min_request_delay <= config.request_delay
        assert config.request_delay <= config.max_request_delay


class TestTimeoutAttributes:

    @pytest.mark.parametrize('parameter', [
        {'fetch_timeout': 'foo'},
        {'selenium_find_timeout': 'foo'},
    ])
    def test_should_raise_error_when_timeout_is_not_float(self, parameter):
        with pytest.raises(ValueError):
            Configuration(**parameter)

    @pytest.mark.parametrize(('fetch_timeout', 'selenium_find_timeout'), [
        ('1.0', '1'),
        (1, 2)
    ])
    def test_should_convert_string_or_int_to_float(self, fetch_timeout, selenium_find_timeout):
        config = Configuration(fetch_timeout=fetch_timeout, selenium_find_timeout=selenium_find_timeout)
        assert float(fetch_timeout) == config.fetch_timeout
        assert float(selenium_find_timeout) == config.selenium_find_timeout

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

    @pytest.mark.parametrize('value', [1, 1.0])
    def test_should_raise_type_error_when_value_is_neither_a_string_nor_a_boolean(self, value):
        with pytest.raises(TypeError):
            Configuration(follow_robots_txt=value)

    def test_should_raise_value_error_when_value_is_not_a_string_representing_a_boolean(self):
        with pytest.raises(ValueError):
            Configuration(follow_robots_txt='foo')

    @pytest.mark.parametrize(('given_value', 'expected_value'), [
        ('1', True),
        ('no', False)
    ])
    def test_should_convert_string_to_correct_boolean_value(self, given_value, expected_value):
        config = Configuration(follow_robots_txt=given_value)
        assert config.follow_robots_txt is expected_value

    def test_default_value_is_false(self, default_config):
        assert default_config.follow_robots_txt is False


class TestBackupFilename:
    """Checks attribute backup_filename"""

    # noinspection PyTypeChecker
    @pytest.mark.parametrize('value', [b'file', 4])
    def test_should_raise_type_error_when_value_is_not_a_string(self, value):
        with pytest.raises(TypeError):
            Configuration(backup_filename=value)

    def test_should_raise_error_when_provided_path_is_not_writable(self, mocker):
        mocker.patch('pathlib.Path.touch', side_effect=RuntimeError)
        with pytest.raises(RuntimeError):
            Configuration(backup_filename='foo.txt')

    def test_should_not_raise_error_when_value_is_a_string(self):
        try:
            Configuration(backup_filename='hello.mp')
        except TypeError as e:
            pytest.fail(f'unexpected error when configuring backup_filename: {e}')


# noinspection PyTypeChecker
class TestRobotsCacheFolder:
    """Checks attribute robots_cache_folder"""

    @pytest.mark.parametrize('value', [4, b'foo'])
    def test_should_raise_error_when_value_is_not_a_string(self, value):
        with pytest.raises(TypeError):
            Configuration(robots_cache_folder=value)

    def test_should_raise_error_when_path_is_does_not_exist(self):
        with pytest.raises(FileNotFoundError) as exc_info:
            Configuration(robots_cache_folder='/path/to/file')

        assert 'robots_cache_folder does not exist' == str(exc_info.value)

    def test_should_raise_error_when_path_is_not_writable(self, mocker, tmp_path):
        mocker.patch('pathlib.Path.write_text', side_effect=PermissionError())
        with pytest.raises(PermissionError):
            Configuration(robots_cache_folder=tmp_path)

    def test_should_raise_error_when_path_is_not_readable(self, mocker, tmp_path):
        mocker.patch('pathlib.Path.read_text', side_effect=PermissionError())
        with pytest.raises(PermissionError):
            Configuration(robots_cache_folder=tmp_path)

    def test_should_not_raise_error_when_giving_correct_path(self, tmp_path):
        try:
            Configuration(robots_cache_folder=tmp_path)
        except (FileNotFoundError, PermissionError) as e:
            pytest.fail(f'unexpected error when instantiating Configuration with robots_cache_folder: {e}')

        p = tmp_path / 'dummy_file'
        assert not p.exists()

    def test_default_value_is_a_temporary_directory_starting_with_prefix_robots(self, default_config):
        temp_dir = tempfile.gettempdir()
        robots_cache_folder = default_config.robots_cache_folder
        prefix_path = Path(temp_dir) / 'robots_'

        assert f'{robots_cache_folder}'.startswith(f'{prefix_path}')
        robots_cache_folder.rmdir()


class TestMiddlewareAttributes:
    """Checks attributes response_middlewares and item_processors"""

    @pytest.mark.parametrize('parameter', [
        {'response_middlewares': {}},
        {'response_middlewares': set()},
        {'item_processors': {}},
        {'item_processors': set()}
    ])
    def test_should_raise_error_when_value_is_not_a_sequence(self, parameter):
        with pytest.raises(TypeError):
            Configuration(**parameter)

    @pytest.mark.parametrize('parameter', [
        {'response_middlewares': [lambda x: x, 'foo']},
        {'item_processors': (lambda x: x, 'bar')}
    ])
    def test_should_raise_error_when_item_in_iterable_is_not_a_callable(self, parameter):
        with pytest.raises(TypeError):
            Configuration(**parameter)

    @pytest.mark.parametrize('parameter', [
        {'response_middlewares': 'custom_math.add hello'},
        {'item_processors': 'custom_math.add hello'}
    ])
    @pytest.mark.usefixtures('math_module')
    def test_should_raise_error_when_string_path_does_not_represent_a_callable(self, parameter):
        with pytest.raises(ValueError):
            Configuration(**parameter)

    @pytest.mark.parametrize('parameter', [
        {'response_middlewares': [lambda x: x]},
        {'response_middlewares': (lambda x: x,)},
        {'item_processors': [lambda x: x]},
        {'item_processors': (lambda x: x,)}
    ])
    def test_should_not_raise_error_when_giving_correct_sequence(self, parameter):
        try:
            Configuration(**parameter)
        except TypeError as e:
            pytest.fail(f'unexpected error: {e}')

    # noinspection PyTypeChecker
    def test_should_convert_string_to_callable_list(self, math_module):
        config = Configuration(
            item_processors='custom_math.add, custom_math.minus',
            response_middlewares='custom_math.add:custom_math.minus'
        )

        assert [math_module.add, math_module.minus] == config.response_middlewares
        assert [math_module.add, math_module.minus] == config.item_processors

    def test_default_middleware_value_is_an_empty_list(self, default_config):
        assert [] == default_config.response_middlewares
        assert [] == default_config.item_processors


class TestMsgPackAttributes:
    """Tests msgpack_encoder and msgpack decoder attributes"""

    @pytest.mark.parametrize('parameter', [
        {'msgpack_encoder': 4},
        {'msgpack_decoder': 4}
    ])
    def test_should_raise_error_when_msgpack_encoder_or_decoder_is_not_a_callable(self, parameter):
        with pytest.raises(TypeError):
            Configuration(**parameter)

    @pytest.mark.parametrize('parameter', [
        {'msgpack_decoder': 'hello'},
        {'msgpack_encoder': 'hello'}
    ])
    def test_should_raise_error_when_msgpack_encoder_or_decoder_is_not_a_string_representing_a_callable(
            self, parameter
    ):
        with pytest.raises(ValueError):
            Configuration(**parameter)

    @pytest.mark.parametrize('parameter', [
        {'msgpack_encoder': lambda x: x},
        {'msgpack_decoder': lambda x: x}
    ])
    def test_should_not_raise_error_when_msgpack_encoder_or_decoder_is_a_callable(self, parameter):
        try:
            Configuration(**parameter)
        except Exception as e:
            pytest.fail(f'unexpected error when instantiating msgpack encoder or decoder: {e}')

    # noinspection PyTypeChecker
    def test_should_not_raise_error_when_msgpack_encoder_or_decoder_is_a_string_representing_a_callable(
            self, math_module
    ):
        config = None
        try:
            # ok, the functions don't look as normal msgpack encoder or decoder, but it is just to test that the feature
            # works as expected
            config = Configuration(
                msgpack_encoder='custom_math.add',
                msgpack_decoder='custom_math.minus'
            )
        except Exception as e:
            pytest.fail(f'unexpected error when instantiating msgpack encoder or decoder: {e}')

        assert math_module.add is config.msgpack_encoder
        assert math_module.minus is config.msgpack_decoder

    def test_should_match_default_msgpack_encoder_and_decoder(self, default_config):
        assert datetime_decoder is default_config.msgpack_decoder
        assert datetime_encoder is default_config.msgpack_encoder


class TestMethodGetDictWithLowerKeys:
    """tests method _get_dict_with_lower_keys"""

    @pytest.mark.parametrize(('given_dict', 'expected_dict'), [
        ({'foo': 'bar', 'fruit': 'pineapple'}, {'foo': 'bar', 'fruit': 'pineapple'}),
        ({'FOO': 2, 'Fruit': 'TOMATO'}, {'foo': 2, 'fruit': 'TOMATO'})
    ])
    def test_should_return_correct_dict_given_correct_input(self, given_dict, expected_dict):
        assert_dicts(expected_dict, Configuration._get_dict_with_lower_keys(given_dict))


class TestMethodScalpelAttributes:
    """Tests method _scalpel_attributes"""

    def test_should_return_empty_dict_when_no_scalpel_attribute_found(self):
        data = {'foo': 'bar', 'timeout': 2}
        assert {} == Configuration._scalpel_attributes(data)

    def test_should_return_non_empty_dict_when_scalpel_attributes_found(self):
        data = {
            'name': 'paul',
            'scalpel': {
                'min_request_delay': 1,
                'foo': 'bar',
                'USER_AGENT': 'Mozilla/5.0',
                'fruit': 'pineapple',
                '_config': 'foobar'
            }
        }
        expected = {'min_request_delay': 1, 'user_agent': 'Mozilla/5.0'}

        assert_dicts(expected, Configuration._scalpel_attributes(data))


class TestCheckFile:
    """Test method _check_file"""

    # noinspection PyTypeChecker
    @pytest.mark.parametrize('test_file', [2, b'fe', 5.0])
    def test_should_raise_error_when_file_has_not_correct_type(self, test_file):
        with pytest.raises(TypeError) as exc_info:
            Configuration._check_file(test_file, 'txt')

        assert f'txt file must be of type Path or str but you provided {type(test_file)}' == str(exc_info.value)

    @pytest.mark.parametrize('test_file', ['foo.txt', Path('foo.txt')])
    def test_should_raise_error_when_file_does_not_exist(self, test_file):
        with pytest.raises(FileNotFoundError) as exc_info:
            Configuration._check_file(test_file, 'txt')

        assert f'file {test_file} does not exist' == str(exc_info.value)


class TestLoadFromYaml:
    """Tests method load_from_yaml"""

    # noinspection PyTypeChecker
    @pytest.mark.parametrize('yaml_file', [b'foo.txt', 4.0])
    def test_should_raise_error_when_file_is_not_path_or_string(self, yaml_file):
        with pytest.raises(TypeError) as exc_info:
            Configuration.load_from_yaml(yaml_file)

        assert f'yaml file must be of type Path or str but you provided {type(yaml_file)}' == str(exc_info.value)

    def test_should_return_correct_config_when_given_correct_yaml_file(self, tmp_path):
        lines = """---
        scalpel:
          fetch_timeout: 4.0
          user_agent: Mozilla/5.0
          follow_robots_txt: true
          foo: bar
        """
        yaml_file = tmp_path / 'settings.yml'
        yaml_file.write_text(lines)
        expected_config = Configuration(fetch_timeout=4.0, user_agent='Mozilla/5.0', follow_robots_txt=True)

        for item in [f'{yaml_file}', yaml_file]:
            config = Configuration.load_from_yaml(item)
            assert expected_config.fetch_timeout == config.fetch_timeout
            assert expected_config.user_agent == config.user_agent
            assert expected_config.follow_robots_txt == config.follow_robots_txt

    def test_should_raise_error_when_file_is_not_valid_yaml(self, tmp_path):
        yaml_file = tmp_path / 'foo.yaml'
        lines = """
        [scalpel]
        foo = bar
        """
        yaml_file.write_text(lines)

        with pytest.raises(DecodeError):
            Configuration.load_from_yaml(yaml_file)


class TestLoadFromToml:
    """Tests method load_from_toml"""

    # noinspection PyTypeChecker
    @pytest.mark.parametrize('toml_file', [b'foo.txt', 4.0])
    def test_should_raise_error_when_file_is_not_path_or_string(self, toml_file):
        with pytest.raises(TypeError) as exc_info:
            Configuration.load_from_toml(toml_file)

        assert f'toml file must be of type Path or str but you provided {type(toml_file)}' == str(exc_info.value)

    def test_should_return_correct_config_when_given_correct_toml_file(self, tmp_path):
        toml_file = tmp_path / 'settings.toml'
        lines = """
        [scalpel]
        foo = "bar"
        user_agent = "Mozilla/5.0"
        fetch_timeout = 4.0
        follow_robots_txt = true
        """
        toml_file.write_text(lines)
        expected_config = Configuration(fetch_timeout=4.0, user_agent='Mozilla/5.0', follow_robots_txt=True)

        for item in [f'{toml_file}', toml_file]:
            config = Configuration.load_from_toml(item)
            assert expected_config.fetch_timeout == config.fetch_timeout
            assert expected_config.user_agent == config.user_agent
            assert expected_config.follow_robots_txt == config.follow_robots_txt

    def test_should_raise_error_when_file_is_not_valid_toml(self, tmp_path):
        toml_file = tmp_path / 'settings.toml'
        toml_file.write_text('Hello!')

        with pytest.raises(DecodeError):
            Configuration.load_from_toml(toml_file)


class TestLoadFromDotEnv:
    """Tests method load_from_dotenv"""

    # noinspection PyTypeChecker
    @pytest.mark.parametrize('env_file', [b'foo.txt', 4])
    def test_should_raise_error_when_file_is_not_path_or_string(self, env_file):
        with pytest.raises(TypeError) as exc_info:
            Configuration.load_from_dotenv(env_file)

        assert f'env file must be of type Path or str but you provided {type(env_file)}' == str(exc_info.value)

    def test_should_return_correct_config_given_correct_env_file(self, tmp_path, math_module):
        env_file = tmp_path / '.env'
        lines = """
        FOO = BAR
        SCALPEL_FOLLOW_ROBOTS_TXT = yes
        SCALPEL_FETCH_TIMEOUT = 2.0
        SCALPEL_RESPONSE_MIDDLEWARES = custom_math.add:custom_math.minus
        """
        env_file.write_text(lines)

        config = Configuration.load_from_dotenv(env_file)
        assert config.follow_robots_txt is True
        assert 2.0 == config.fetch_timeout
        assert [math_module.add, math_module.minus] == config.response_middlewares
