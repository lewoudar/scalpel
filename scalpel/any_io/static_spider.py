import logging
import math
import platform
from asyncio import iscoroutinefunction
from pathlib import Path
from typing import Callable, Optional, Any, Union

import anyio
import attr
import httpx
from anyio.abc import TaskGroup
from rfc3986 import uri_reference

from scalpel.core.spider import Spider
from .files import write_mp
from .response import StaticResponse
from .robots import RobotsAnalyzer
from .queue import Queue

logger = logging.getLogger('scalpel')


@attr.s(slots=True)
class StaticSpider(Spider):
    """
    A spider suitable to parse files or static HTML files.

    **Parameters:**

    * **urls:** Urls to parse. Allowed schemes are `http`, `https` and `file`. It can be a `list`, a `tuple` or a `set`.
    * **parse:** An async callable used to parse url content. It takes two arguments: the current spider and a
    `StaticResponse` object.
    * **reachable_urls:** `set` of urls that are already fetched or read.
    * **unreachable_urls:** `set` of urls that were impossible to fetch or read.
    * **robot_excluded_urls:** `set` of urls that were excluded to fetch because of *robots.txt* file rules.
    * **followed_urls:** `set` of urls that were followed during the process of parsing url content. You will find these
    urls scattered in the first three sets.
    * **request_counter:** The number of urls already fetched or read.

    Usage:

    ```
    from scalpel.any_io import StaticSpider, StaticResponse

    async def parse(spider: StaticSpider, response: StaticResponse) -> None:
        ...

    spider = StaticSpider(urls=['https://example.com'], parse=parse)
    await spider.run()
    ```
    """
    # order is important here, http_client must come before robots_analyzer since the latter used the former
    _start_time: float = attr.ib(init=False, repr=False, factory=anyio.current_time)
    _http_client: httpx.AsyncClient = attr.ib(init=False, repr=False)
    _robots_analyser: RobotsAnalyzer = attr.ib(init=False, repr=False)
    _fetch: Callable = attr.ib(init=False, repr=False)
    _lock: anyio.Lock = attr.ib(init=False, repr=False, factory=anyio.Lock)
    _queue: Queue = attr.ib(init=False, repr=False)

    def __attrs_post_init__(self):

        async def _get_fetch(url: str) -> httpx.Response:
            return await self._http_client.get(url)

        self._fetch = _get_fetch
        for middleware in self.config.response_middlewares:
            self._fetch = middleware(self._fetch)

    @_http_client.default
    def _get_http_client(self) -> httpx.AsyncClient:
        headers = {'User-Agent': self.config.user_agent}
        logger.debug('getting a default httpx client with user agent: %s', self.config.user_agent)
        return httpx.AsyncClient(headers=headers, timeout=self.config.fetch_timeout)

    @_robots_analyser.default
    def _get_robots_analyzer(self) -> RobotsAnalyzer:
        logger.debug('getting a default robots analyzer')
        return RobotsAnalyzer(
            http_client=self._http_client,
            robots_cache=Path(self.config.robots_cache_folder),
            user_agent=self.config.user_agent
        )

    @_queue.default
    def _get_queue(self) -> Queue:
        logger.debug('getting a default queue')
        return Queue(size=math.inf, items=self.urls)

    def _get_static_response(
            self, url: str = '', text: str = '', httpx_response: httpx.Response = None
    ) -> StaticResponse:
        logger.debug(
            'returning StaticResponse object with url: %s, text: %s and httpx_response: %s', url, text, httpx_response
        )
        return StaticResponse(
            self.reachable_urls, self.followed_urls, self._queue, url=url, text=text,
            httpx_response=httpx_response
        )

    def _is_url_already_processed(self, url: str) -> False:
        processed = False
        if url in [*self.reachable_urls, *self.unreachable_urls, *self.robots_excluded_urls]:
            logger.debug('url %s has already been processed', url)
            self._queue.task_done()
            processed = True
        return processed

    # noinspection PyBroadException
    async def _handle_url(self, url: str) -> None:
        if self._is_url_already_processed(url):
            return

        static_url = text = ''
        response: Optional[httpx.Response] = None
        ur = uri_reference(url)
        if ur.scheme == 'file':
            static_url = url
            logger.debug('url %s is a file url so we attempt to read its content')
            file_path = ur.path[1:] if platform.system() == 'Windows' else ur.path
            try:
                before = anyio.current_time()
                async with await anyio.open_file(file_path) as f:
                    text = await f.read()
                fetch_time = anyio.current_time() - before
            except OSError:
                logger.exception('unable to open file %s', url)
                self.unreachable_urls.add(url)
                return
        else:
            response: httpx.Response = await self._fetch(url)
            if response.is_error:
                logger.info('fetching url %s returns an error with status code %s', url, response.status_code)
                self.unreachable_urls.add(url)
                return
            fetch_time = response.elapsed.total_seconds()

        # we update some variables for statistics
        self.request_counter += 1
        self.reachable_urls.add(url)
        self._total_fetch_time += fetch_time

        try:
            await self.parse(self, self._get_static_response(static_url, text, response))
        except Exception:
            logger.exception('something unexpected happened while parsing the content at url %s', url)
            if not self._ignore_errors:
                self._queue.task_done()
                raise
        self._queue.task_done()
        logger.info('content at url %s has been processed', url)

    async def save_item(self, item: Any) -> None:
        item_rejected = False
        original_item = item
        for processor in self.config.item_processors:
            if iscoroutinefunction(processor):
                item = await processor(item)
            else:
                item = processor(item)
            if item is None:
                item_rejected = True
                break
        if item_rejected:
            logger.debug('item %s was rejected', original_item)
            return

        logger.debug('writing item %s to file %s', item, self.config.backup_filename)
        async with self._lock:
            await write_mp(self.config.backup_filename, item, mode='a', encoder=self.config.msgpack_encoder)

    async def _get_request_delay(self, url: str) -> Union[int, float]:
        if self.config.follow_robots_txt:
            return await self._robots_analyser.get_request_delay(url, self.config.request_delay)
        await anyio.sleep(0)  # checkpoint to ensure an async function in every case
        return self.config.request_delay

    async def worker(self, task_group: TaskGroup) -> None:
        while True:
            url = await self._queue.get()
            request_delay = await self._get_request_delay(url)
            if request_delay == -1:  # url is not accessible
                self.robots_excluded_urls.add(url)
                self._queue.task_done()
                continue

            task_group.start_soon(self._handle_url, url)
            await anyio.sleep(request_delay)

    async def _cleanup(self) -> None:
        await self._http_client.aclose()
        await self._queue.close()

    # noinspection PyAsyncCall
    async def run(self) -> None:
        """Runs the spider."""
        async with anyio.create_task_group() as tg:
            tg.start_soon(self.worker, tg)
            await self._queue.join()
            # at this point, all the urls were handled, so the only remaining task is the worker
            tg.cancel_scope.cancel()

        await self._cleanup()
        self._duration = anyio.current_time() - self._start_time
