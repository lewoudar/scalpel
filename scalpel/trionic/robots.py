import logging
from typing import Dict, Union, List
from urllib.robotparser import RobotFileParser

import attr
import httpx
import trio

from scalpel.core.robots import RobotsMixin

logger = logging.getLogger('scalpel')


@attr.s
class RobotsAnalyzer(RobotsMixin):
    # order is important, _http_client can use the _user_agent info to instantiate itself
    _user_agent: str = attr.ib()
    _robots_cache: trio.Path = attr.ib()
    _robots_mapping: Dict[str, trio.Path] = attr.ib(factory=dict)
    _http_client: httpx.AsyncClient = attr.ib()
    _robots_parser: RobotFileParser = attr.ib(init=False, factory=RobotFileParser)
    _delay_mapping: Dict[str, Union[int, float]] = attr.ib(init=False, factory=dict)

    @_http_client.default
    def _get_default_client(self) -> httpx.AsyncClient:
        logger.debug('returning default http client with user agent: %s', self._user_agent)
        headers = {'User-Agent': self._user_agent}
        return httpx.AsyncClient(headers=headers)

    @staticmethod
    async def _create_robots_file(robots_path: trio.Path, content: str) -> None:
        logger.debug('creating robots file at path: %s', robots_path)
        await robots_path.write_text(content)

    @staticmethod
    async def _get_robots_lines(path: trio.Path) -> List[str]:
        logger.debug('getting robots file lines at path: %s', path)
        async with await path.open() as f:
            return await f.readlines()

    async def can_fetch(self, url: str) -> bool:
        httpx_url = httpx.URL(url)
        host = httpx_url.host
        robots_url = httpx_url.copy_with(path='/robots.txt')

        if host not in self._robots_mapping:
            try:
                response = await self._http_client.get(f'{robots_url}')
            except httpx.ConnectTimeout:
                logger.info('cannot connect to host % to get robots.txt file, returning False', robots_url.host)
                return False
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
                await self._create_robots_file(robot_path, response.text)
                self._robots_mapping[host] = await robot_path.absolute()

        robot_lines = await self._get_robots_lines(self._robots_mapping[host])
        self._robots_parser.parse(robot_lines)
        is_fetchable = self._robots_parser.can_fetch(self._user_agent, url)
        logger.info('after analyzing %s file, returning value is %s', f'{robots_url}', is_fetchable)
        return is_fetchable

    async def get_request_delay(self, url: str, delay: Union[int, float]) -> Union[int, float]:
        host = httpx.URL(url).host

        if host in self._delay_mapping:
            logger.debug('returning caching value %s', self._delay_mapping[host])
            return self._delay_mapping[host]

        if host not in self._robots_mapping:
            is_fetchable = await self.can_fetch(url)
            if not is_fetchable:
                self._delay_mapping[host] = -1
                logger.debug('url %s is not fetchable, returning negative value', url)
                return -1

        return self._get_request_delay(host, url, self._robots_parser, self._delay_mapping, delay)

    async def close(self) -> None:
        await self._http_client.aclose()
