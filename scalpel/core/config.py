import random
import re
import logging
from importlib import import_module
from pathlib import Path
from typing import List, Callable, Any, Dict, Union

import attr
from configuror import Config
from fake_useragent import UserAgent, FakeUserAgentError

logger = logging.getLogger('scalpel')


def check_value_greater_or_equal_than_0(_, attribute: attr.Attribute, value: int) -> None:
    if value < 0:
        error_message = f'{attribute.name} must be a positive integer'
        logger.exception(error_message)
        raise ValueError(error_message)


def check_max_delay_greater_or_equal_than_min_delay(instance: 'Configuration', attribute: attr.Attribute,
                                                    value: int) -> None:
    if instance.min_request_delay > value:
        error_message = f'{attribute.name} must be greater or equal than min_request_delay'
        logger.exception(error_message)
        raise ValueError(error_message)


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
        error_message = f'{value} does not represent a boolean'
        logger.exception(error_message)
        raise ValueError(error_message)


# The same logic as above converter applies to the type of return
def callable_list_converter(value: Any) -> Union[List[Callable], Any]:
    if isinstance(value, list):
        if not all(isinstance(item, str) for item in value):
            logger.debug('not all items in %s are a string, returned it as it', value)
            return value
        str_callable_list = value
    elif isinstance(value, str):
        str_callable_list = re.split(r',\s*|;\s*|:\s*|\s+', value)
    else:
        logger.debug('%s is not a string or a list of strings, returned it as it is', value)
        return value

    callables = []
    for str_callable in str_callable_list:
        parts = str_callable.split('.')
        module_name = '.'.join(parts[:-1])
        module = import_module(module_name)
        callables.append(getattr(module, parts[-1]))

    logger.debug('returning callables: %s', callables)
    return callables


positive_int_validators = [attr.validators.instance_of(int), check_value_greater_or_equal_than_0]
max_delay_validators = [*positive_int_validators, check_max_delay_greater_or_equal_than_min_delay]
positive_float_validators = [attr.validators.instance_of(float), check_value_greater_or_equal_than_0]
middleware_validator = attr.validators.deep_iterable(
    member_validator=attr.validators.is_callable(),
    iterable_validator=attr.validators.instance_of((list, tuple))
)


@attr.s(frozen=True)
class Configuration:
    min_request_delay: int = attr.ib(default=0, converter=int, validator=positive_int_validators)
    max_request_delay: int = attr.ib(default=0, converter=int, validator=max_delay_validators)
    fetch_timeout: float = attr.ib(default=5.0, converter=float, validator=positive_float_validators)
    selenium_find_timeout: float = attr.ib(default=10.0, converter=float, validator=positive_float_validators)
    user_agent: str = attr.ib(validator=attr.validators.instance_of(str))
    follow_robots_txt: bool = attr.ib(default=False, converter=bool_converter,
                                      validator=attr.validators.instance_of(bool))
    response_middlewares: List[Callable] = attr.ib(repr=False, converter=callable_list_converter, factory=list,
                                                   validator=middleware_validator)
    process_item_middlewares: List[Callable] = attr.ib(repr=False, converter=callable_list_converter, factory=list,
                                                       validator=middleware_validator)

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

    @property
    def request_delay(self) -> int:
        delay = random.randint(self.min_request_delay, self.max_request_delay)
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
