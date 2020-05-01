import logging
from datetime import datetime
from typing import Union, Set, List, Tuple, Callable

import attr
from rfc3986 import iri_reference, validators, exceptions

from .config import Configuration

logger = logging.getLogger('scalpel')

URLS = Union[List[str], Tuple[str], Set[str]]


def url_validator(_, attribute: attr.Attribute, urls: URLS):
    if not isinstance(urls, (Set, list, tuple)):
        message = f'{attribute.name} is not a typing.Set, list or tuple instance: {urls}'
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


@attr.s(frozen=True)
class Spider:
    urls: URLS = attr.ib(validator=url_validator)
    parse: Callable = attr.ib(validator=attr.validators.is_callable())
    _name: str = attr.ib(validator=attr.validators.instance_of(str))
    _config: Configuration = attr.ib(factory=Configuration, validator=attr.validators.instance_of(Configuration))
    _fetched_urls: set = attr.ib(factory=set, init=False)

    @_name.default
    def get_name(self) -> str:
        now = datetime.now()
        name = f'spider-{now.strftime("%Y-%m-%d@%H:%M:%S.%f")}'
        logger.debug('getting a default spider name: %s', name)
        return name

    @property
    def name(self) -> str:
        logger.debug('returning name property: %s', self._name)
        return self._name

    @property
    def config(self) -> Configuration:
        logger.debug('returning config property: %s', self._config)
        return self._config
