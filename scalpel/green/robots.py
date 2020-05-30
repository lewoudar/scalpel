import logging
from pathlib import Path
from typing import Dict, List, Union
from urllib.robotparser import RobotFileParser

import attr
import httpx

from scalpel.core.robots import RobotsMixin
from .utils.io import open_file

logger = logging.getLogger('scalpel')


@attr.s
class RobotsAnalyzer(RobotsMixin):
    # order is important, _http_client can use the _user_agent info to instantiate itself
    _user_agent: str = attr.ib()
    _robots_cache: Path = attr.ib()
    _robots_mapping: Dict[str, Path] = attr.ib(factory=dict)
    _http_client: httpx.Client = attr.ib()
    _robots_parser: RobotFileParser = attr.ib(init=False, factory=RobotFileParser)
    _delay_mapping: Dict[str, Union[int, float]] = attr.ib(init=False, factory=dict)

    @_http_client.default
    def _get_http_client(self) -> httpx.Client:
        logger.debug('returning default http client with user agent: %s', self._user_agent)
        headers = {'User-Agent': self._user_agent}
        return httpx.Client(headers=headers)

    @staticmethod
    def _create_robots_file(robots_path: Path, content: str) -> None:
        logger.debug('creating robots file at path: %s', robots_path)
        with open_file(robots_path, 'w') as f:
            f.write(content)

    @staticmethod
    def _get_robots_lines(path: Path) -> List[str]:
        logger.debug('getting robots file lines at path: %s', path)
        with open_file(path) as f:
            return f.readlines()

    def can_fetch(self, url: str) -> bool:
        httpx_url = httpx.URL(url)
        host = httpx_url.host
        robots_url = httpx_url.copy_with(path='/robots.txt')

        if host not in self._robots_mapping:
            try:
                response = self._http_client.get(f'{robots_url}')
            except httpx.ConnectTimeout:
                logger.info('cannot connect to host % to get robots.txt file, returning False', robots_url.host)
                return False
            # this is the behaviour of the implementation of CPython RobotFileParser read and can_fetch methods
            # https://github.com/python/cpython/blob/master/Lib/urllib/robotparser.py
            if response.status_code in (401, 403):
                logger.info(
                    'access to %s is %s, returning False', f'{robots_url}',
                    httpx.codes.get_reason_phrase(response.status_code)
                )
                return False
            elif httpx.codes.is_error(response.status_code):
                logger.info(
                    'trying to access %s returns a %s error status code, returning True', f'{robots_url}',
                    response.status_code
                )
                return True
            else:
                robot_path = self._robots_cache / host
                self._create_robots_file(robot_path, response.text)
                self._robots_mapping[host] = robot_path.absolute()

        self._robots_parser.parse(self._get_robots_lines(self._robots_mapping[host]))
        is_fetchable = self._robots_parser.can_fetch(self._user_agent, url)
        logger.info('after analyzing %s file, returning value is %s', f'{robots_url}', is_fetchable)
        return is_fetchable

    def get_request_delay(self, url: str, delay: Union[int, float]) -> Union[int, float]:
        host = httpx.URL(url).host

        if host in self._delay_mapping:
            logger.debug('returning caching value %s', self._delay_mapping[host])
            return self._delay_mapping[host]

        if host not in self._robots_mapping:
            is_fetchable = self.can_fetch(url)
            if not is_fetchable:
                self._delay_mapping[host] = -1
                logger.debug('url %s is not fetchable, returning negative value', url)
                return -1

        return self._get_request_delay(host, url, self._robots_parser, self._delay_mapping, delay)

    def close(self):
        self._http_client.close()
