import random
from typing import List, Callable

import attr
from fake_useragent import UserAgent, FakeUserAgentError


def check_value_greater_or_equal_than_0(_, attribute: attr.Attribute, value: int) -> None:
    if value < 0:
        raise ValueError(f'{attribute.name} must be a positive integer')


def check_max_delay_greater_or_equal_than_min_delay(instance: 'Configuration', attribute: attr.Attribute,
                                                    value: int) -> None:
    if instance.min_request_delay > value:
        raise ValueError(f'{attribute.name} must be greater or equal than min_request_delay')


positive_int_validators = [attr.validators.instance_of(int), check_value_greater_or_equal_than_0]
max_delay_validators = [*positive_int_validators, check_max_delay_greater_or_equal_than_min_delay]
positive_float_validators = [attr.validators.instance_of(float), check_value_greater_or_equal_than_0]
middleware_validator = attr.validators.deep_iterable(
    member_validator=attr.validators.is_callable(),
    iterable_validator=attr.validators.instance_of((list, tuple))
)


@attr.s(frozen=True)
class Configuration:
    min_request_delay: int = attr.ib(default=0, validator=positive_int_validators)
    max_request_delay: int = attr.ib(default=0, validator=max_delay_validators)
    fetch_timeout: float = attr.ib(default=5.0, validator=positive_float_validators)
    selenium_find_timeout: float = attr.ib(default=10.0, validator=positive_float_validators)
    user_agent: str = attr.ib(validator=attr.validators.instance_of(str))
    follow_robots_txt: bool = attr.ib(default=False, validator=attr.validators.instance_of(bool))
    response_middlewares: List[Callable] = attr.ib(repr=False, factory=list, validator=middleware_validator)
    process_item_middlewares: List[Callable] = attr.ib(repr=False, factory=list, validator=middleware_validator)

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
