import logging
import random
import re
import tempfile
from importlib import import_module
from pathlib import Path
from typing import List, Callable, Any, Dict, Union, Optional

import attr
from configuror import Config
from fake_useragent import UserAgent, FakeUserAgentError

from .message_pack import datetime_encoder, datetime_decoder

logger = logging.getLogger('scalpel')


def check_value_greater_or_equal_than_0(_, attribute: attr.Attribute, value: int) -> None:
    if value < 0:
        message = f'{attribute.name} must be a positive integer'
        logger.exception(message)
        raise ValueError(message)


def check_max_delay_greater_or_equal_than_min_delay(instance: 'Configuration', attribute: attr.Attribute,
                                                    value: int) -> None:
    if instance.min_request_delay > value:
        message = f'{attribute.name} must be greater or equal than min_request_delay'
        logger.exception(message)
        raise ValueError(message)


def validate_robots_folder(_, attribute: attr.Attribute, path: Path) -> None:
    if not path.exists():
        message = f'{attribute.name} does not exist'
        logger.exception(message)
        raise FileNotFoundError(message)

    dummy_file = path / 'dummy_file'
    try:
        dummy_file.write_text('hello')
    except PermissionError:
        logger.exception(f'Cannot write file in {path}')
        raise
    try:
        dummy_file.read_text()
    except PermissionError:
        logger.exception(f'Cannot read file in {path}')
        raise
    dummy_file.unlink()


def check_backup_file_can_be_created(_, _attribute: attr.Attribute, value: str) -> None:
    if value is not None:
        p = Path(value)
        # touch helps to see if a file can be created with the given path
        p.touch()
        # we don't want to have a created file if other attributes validation failed
        p.unlink()


# I could just use return type "Any" but I want to insist on the fact that the function must
# first return a boolean and in the other cases, the value given at input
def bool_converter(value: Any) -> Union[bool, Any]:
    if not isinstance(value, str):
        logger.debug('%s is not a string, returned it as it is', value)
        return value

    if value.lower() in ['1', 'true', 'yes', 'y']:
        logger.debug('converts %s to True', value)
        return True
    elif value.lower() in ['0', 'false', 'no', 'n']:
        logger.debug('converts %s to False', value)
        return False
    else:
        message = f'{value} does not represent a boolean'
        logger.exception(message)
        raise ValueError(message)


def get_callable_from_string(callable_string: str) -> Callable:
    parts = callable_string.split('.')
    module_name = '.'.join(parts[:-1])
    module = import_module(module_name)
    return getattr(module, parts[-1])


# The same logic as the bool converter applies to the type of return
def callable_list_converter(value: Any) -> Union[List[Callable], Any]:
    if isinstance(value, list):
        if not all(isinstance(item, str) for item in value):
            logger.debug('not all items in the list are a string, returned it as it: %s', value)
            return value
        str_callable_list = value
    elif isinstance(value, str):
        str_callable_list = re.split(r',\s*|;\s*|:\s*|\s+', value)
    else:
        logger.debug('%s is not a string or a list of strings, returned it as it is', value)
        return value

    callables = []
    for str_callable in str_callable_list:
        callables.append(get_callable_from_string(str_callable))

    logger.debug('returning callables: %s', callables)
    return callables


def msgpack_converter(value: Any) -> Union[Callable, Any]:
    if not isinstance(value, str):
        logger.debug(f'{value} is not a string, returning it as it')
        return value
    return get_callable_from_string(value)


positive_int_validators = [attr.validators.instance_of(int), check_value_greater_or_equal_than_0]
max_delay_validators = [*positive_int_validators, check_max_delay_greater_or_equal_than_min_delay]
positive_float_validators = [attr.validators.instance_of(float), check_value_greater_or_equal_than_0]
middleware_validator = attr.validators.deep_iterable(
    member_validator=attr.validators.is_callable(),
    iterable_validator=attr.validators.instance_of((list, tuple))
)
backup_filename_validators = [attr.validators.optional(attr.validators.instance_of(str)),
                              check_backup_file_can_be_created]


@attr.s(frozen=True)
class Configuration:
    min_request_delay: int = attr.ib(default=0, converter=int, validator=positive_int_validators)
    max_request_delay: int = attr.ib(default=0, converter=int, validator=max_delay_validators)
    fetch_timeout: float = attr.ib(default=5.0, converter=float, validator=positive_float_validators)
    selenium_find_timeout: float = attr.ib(default=10.0, converter=float, validator=positive_float_validators)
    user_agent: str = attr.ib(validator=attr.validators.instance_of(str))
    follow_robots_txt: bool = attr.ib(default=False, converter=bool_converter,
                                      validator=attr.validators.instance_of(bool))
    robots_cache_folder: Path = attr.ib(converter=Path, validator=validate_robots_folder)
    backup_filename: Optional[str] = attr.ib(default=None, validator=backup_filename_validators)
    response_middlewares: List[Callable] = attr.ib(repr=False, converter=callable_list_converter, factory=list,
                                                   validator=middleware_validator)
    item_processors: List[Callable] = attr.ib(repr=False, converter=callable_list_converter, factory=list,
                                              validator=middleware_validator)
    msgpack_encoder: Callable = attr.ib(repr=False, converter=msgpack_converter, default=datetime_encoder,
                                        validator=attr.validators.is_callable())
    msgpack_decoder: Callable = attr.ib(repr=False, converter=msgpack_converter, default=datetime_decoder,
                                        validator=attr.validators.is_callable())

    @user_agent.default
    def get_default_user_agent(self) -> str:
        try:
            ua = UserAgent()
            user_agent = ua.random
            logger.debug('returning a random user agent: %s', user_agent)
            return user_agent
        except FakeUserAgentError:
            # for the fallback, I use a recent version found on http://useragentstring.com/
            # not sure if this is the best strategy but we will stick with it for now
            fallback = 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                       'Chrome/41.0.2225.0 Safari/537.36'
            logger.debug('returning fallback value for user agent: %s', fallback)
            return fallback

    @robots_cache_folder.default
    def get_robots_cache_folder(self) -> Path:
        temp_dir = Path(tempfile.mkdtemp(prefix='robots_'))
        logger.debug('returning default created temporary directory: %s', temp_dir)
        return temp_dir

    @property
    def request_delay(self) -> int:
        # for bandit, using random module to generate pseudo-random values is not a good
        # idea for cryptography / security purposes, but since we are not in this case, we just
        # ignore this warning.
        # More about the warning: https://bandit.readthedocs.io/en/latest/blacklists/blacklist_calls.html#b311-random
        delay = random.randint(self.min_request_delay, self.max_request_delay)  # nosec
        logger.debug('returning computed request delay: %s s', delay)
        return delay

    @staticmethod
    def _get_dict_with_lower_keys(data: Dict[str, Any]) -> Dict[str, Any]:
        data = {key.lower(): value for key, value in data.items()}
        logger.debug('returning dict with lower keys: %s', data)
        return data

    @classmethod
    def _scalpel_attributes(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        data_key = 'scalpel'
        attributes = {}

        if data_key not in data:
            logger.debug('no namespace "scalpel" in %s, returning empty attributes', data)
            return attributes

        data = cls._get_dict_with_lower_keys(data[data_key])
        for attribute in attr.fields(cls):
            if attribute.name != '_config' and attribute.name in data:
                attributes[attribute.name] = data[attribute.name]
        logger.debug('returning scalpel attributes: %s', attributes)
        return attributes

    @staticmethod
    def _check_file(config_file: Union[Path, str], file_type: str) -> None:
        if not isinstance(config_file, (Path, str)):
            error_message = f'{file_type} file must be of type Path or str but you provided {type(config_file)}'
            logger.exception(error_message)
            raise TypeError(error_message)

        config_file = Path(config_file)
        if not config_file.is_file():
            error_message = f'file {config_file} does not exist'
            logger.exception(error_message)
            raise FileNotFoundError(error_message)

    @classmethod
    def load_from_yaml(cls, yaml_file: Union[Path, str]) -> 'Configuration':
        cls._check_file(yaml_file, 'yaml')

        configuror = Config(mapping_files={'yaml': [f'{yaml_file}']})
        logger.debug('loading configuration from yaml file: %s', f'{yaml_file}')
        return cls(**cls._scalpel_attributes(configuror))

    @classmethod
    def load_from_toml(cls, toml_file: Union[Path, str]) -> 'Configuration':
        cls._check_file(toml_file, 'toml')

        configuror = Config(mapping_files={'toml': [f'{toml_file}']})
        logger.debug('loading configuration from toml file: %s', f'{toml_file}')
        return cls(**cls._scalpel_attributes(configuror))

    @classmethod
    def load_from_dotenv(cls, env_file: Union[Path, str]) -> 'Configuration':
        cls._check_file(env_file, 'env')

        configuror = Config(mapping_files={'env': [f'{env_file}']})
        data = configuror.get_dict_from_namespace('SCALPEL_')
        data = {'scalpel': data}  # little trick to search attributes using _scalpel_attributes class method
        logger.debug('loading configuration from .env file: %s', f'{env_file}')
        return cls(**cls._scalpel_attributes(data))
