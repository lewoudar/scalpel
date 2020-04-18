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
        raise ValueError(error_message)


def check_max_delay_greater_or_equal_than_min_delay(instance: 'Configuration', attribute: attr.Attribute,
                                                    value: int) -> None:
    if instance.min_request_delay > value:
        raise ValueError(f'{attribute.name} must be greater or equal than min_request_delay')


# I could just use return type "Any" but I want to insist on the fact that the function must
# first return a boolean and in the other cases, the value given at input
def bool_converter(value: Any) -> Union[bool, Any]:
    if not isinstance(value, str):
        return value

    if value.lower() in ['1', 'true', 'yes', 'y']:
        return True
    elif value.lower() in ['0', 'false', 'no', 'n']:
        return False
    else:
        raise ValueError(f'{value} does not represent a boolean')


# The same logic as above converter applies to the type of return
def callable_list_converter(value: Any) -> Union[List[Callable], Any]:
    if not isinstance(value, str):
        return value

    callables = []
    str_callable_list = re.split(r',\s*|;\s*|:\s*|\s+', value)
    for str_callable in str_callable_list:
        parts = str_callable.split('.')
        module_name = '.'.join(parts[:-1])
        module = import_module(module_name)
        callables.append(getattr(module, parts[-1]))

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
            return ua.random
        except FakeUserAgentError:
            # for the fallback, I use a recent version found on http://useragentstring.com/
            # not sure if this is the best strategy but we will stick with it for now
            return 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                   'Chrome/41.0.2225.0 Safari/537.36'

    @property
    def request_delay(self) -> int:
        return random.randint(self.min_request_delay, self.max_request_delay)

    @staticmethod
    def _get_dict_with_lower_keys(data: Dict[str, Any]) -> Dict[str, Any]:
        for key in data.keys():
            value = data.pop(key)
            data[key.lower()] = value
        return data

    @classmethod
    def _scalpel_attributes(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        data_key = 'scalpel'
        attributes = {}

        if data_key not in data:
            return attributes

        data = cls._get_dict_with_lower_keys(data[data_key])
        for attribute in attr.fields(cls):
            if attribute.name != '_config' and attribute.name in data:
                attributes[attribute.name] = data[attribute.name]
        return attributes

    @staticmethod
    def _check_file(config_file: Union[Path, str], file_type: str) -> None:
        if not isinstance(config_file, (Path, str)):
            raise TypeError(f'{file_type} file must be of type Path or str but you provided {type(config_file)}')

        config_file = Path(config_file)
        if not config_file.is_file():
            raise FileNotFoundError(f'file {config_file} does not exist')

    @classmethod
    def load_from_yaml(cls, yaml_file: Union[Path, str]) -> 'Configuration':
        cls._check_file(yaml_file, 'yaml')

        configuror = Config(mapping_files={'yaml': [f'{yaml_file}']})
        return cls(**cls._scalpel_attributes(configuror))

    @classmethod
    def load_from_toml(cls, toml_file: Union[Path, str]) -> 'Configuration':
        cls._check_file(toml_file, 'toml')

        configuror = Config(mapping_files={'toml': [f'{toml_file}']})
        return cls(**cls._scalpel_attributes(configuror))

    @classmethod
    def load_from_dotenv(cls, env_file: Union[Path, str]) -> 'Configuration':
        cls._check_file(env_file, 'env')

        configuror = Config(mapping_files={'env': [f'{env_file}']})
        data = configuror.get_dict_from_namespace('SCALPEL_')
        data = {'scalpel': data}  # little trick to search attributes using _scalpel_attributes class method
        return cls(**cls._scalpel_attributes(data))
