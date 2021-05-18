import logging
from datetime import datetime
from typing import Union, Set, List, Tuple, Callable

import attr
from rfc3986 import iri_reference, validators, exceptions

from .config import Configuration

logger = logging.getLogger('scalpel')

URLS = Union[List[str], Tuple[str], Set[str]]


def url_validator(_, attribute: attr.Attribute, urls: URLS):
    if not isinstance(urls, (set, list, tuple)):
        message = f'{attribute.name} is not a set, list or tuple instance: {urls}'
        logger.exception(message)
        raise TypeError(message)

    if not all(isinstance(url, str) for url in urls):
        message = f'not all items in urls are a string: {urls}'
        logger.exception(message)
        raise TypeError(message)

    validator = validators.Validator()
    allowed_schemes = ['https', 'http', 'file']
    validator.allow_schemes(*allowed_schemes)
    validator.check_validity_of('scheme', 'host', 'path', 'query', 'fragment')

    for url in urls:
        uri = iri_reference(url).encode()
        try:
            validator.validate(uri)
        except exceptions.UnpermittedComponentError:
            message = f'{url} does not have a scheme in {allowed_schemes}'
            logger.exception(message)
            raise ValueError(message)
        except exceptions.InvalidComponentsError:
            # not sure this error can happen if we use uri_reference with a string, but let's be careful
            message = f'{url} is not a valid url'
            logger.exception(message)
            raise ValueError(message)

        if uri.scheme in ('http', 'https') and uri.host is None:
            message = f'url {url} must provide a host part'
            logger.exception(message)
            raise ValueError(message)

        if uri.scheme == 'file' and uri.path is None:
            message = f'url {url} must provide a path to a local file'
            logger.exception(message)
            raise ValueError(message)


@attr.s
class State:
    """An empty class used to store arbitrary data."""
    pass


@attr.s(frozen=True)
class SpiderStatistics:
    """
    Provides some statistics about a ran spider.

    **Parameters:**

    * **reachable_urls:** `set` of urls that were fetched (or read in case of file urls) and parsed.
    * **unreachable_urls:** `set` that were impossible to fetch (or read in case of file urls).
    * **robot_excluded_urls:** `set` of urls that were excluded to fetch because of *robots.txt* file rules.
    * **followed_urls:** `set` of urls that were followed during the process of parsing url content. You will find these
    urls scattered in the first three sets.
    * **request_counter:** The number of urls fetched or read (in case of file urls).
    * **average_fetch_time:** The average time to fetch an url (or read a file in case of file urls).
    * **total_time:** The total execution time of the spider.
    """
    reachable_urls: Set[str] = attr.ib()
    unreachable_urls: Set[str] = attr.ib()
    robot_excluded_urls: Set[str] = attr.ib()
    followed_urls: Set[str] = attr.ib()
    request_counter: int = attr.ib()
    average_fetch_time: float = attr.ib()
    total_time: float = attr.ib()


@attr.s(slots=True)
class Spider:
    urls: URLS = attr.ib(validator=url_validator)
    parse: Callable = attr.ib(validator=attr.validators.is_callable())
    _name: str = attr.ib(validator=attr.validators.instance_of(str))
    _config: Configuration = attr.ib(
        factory=Configuration, validator=attr.validators.instance_of(Configuration), repr=False
    )
    _ignore_errors: bool = attr.ib(default=False, validator=attr.validators.instance_of(bool))
    reachable_urls: Set[str] = attr.ib(factory=set, init=False, repr=False)
    unreachable_urls: Set[str] = attr.ib(factory=set, init=False, repr=False)
    followed_urls: Set[str] = attr.ib(factory=set, init=False, repr=False)
    robots_excluded_urls: Set[str] = attr.ib(factory=set, init=False, repr=False)
    request_counter: int = attr.ib(default=0, init=False, repr=False)
    _duration: float = attr.ib(init=False, default=0.0, repr=False)
    _total_fetch_time: float = attr.ib(init=False, default=0.0)
    _state: State = attr.ib(factory=State, init=False, repr=False)

    @_name.default
    def _get_name(self) -> str:
        now = datetime.now()
        name = f'spider-{now.strftime("%Y-%m-%d@%H:%M:%S.%f")}'
        logger.debug('getting a default spider name: %s', name)
        return name

    @property
    def name(self) -> str:
        """Returns the name given to the spider."""
        logger.debug('returning name property: %s', self._name)
        return self._name

    @property
    def config(self) -> Configuration:
        """Returns the `Configuration` related to the spider."""
        logger.debug('returning config property: %s', self._config)
        return self._config

    @property
    def state(self) -> State:
        """Returns the `State` related to the spider. You can add custom information on this object."""
        logger.debug('returning state property: %s', self._state)
        return self._state

    def statistics(self) -> SpiderStatistics:
        """
        Provides some statistics related to the ran spider.

        **Returns:** `SpiderStatistics`
        """
        return SpiderStatistics(
            reachable_urls=self.reachable_urls,
            unreachable_urls=self.unreachable_urls,
            robot_excluded_urls=self.robots_excluded_urls,
            followed_urls=self.followed_urls,
            request_counter=self.request_counter,
            average_fetch_time=self._total_fetch_time / self.request_counter if self.request_counter else 0.0,
            total_time=self._duration
        )
