import logging
import platform
from time import time
from typing import Callable, Optional, Any

import attr
import gevent
import httpx
from gevent.lock import RLock
from gevent.pool import Pool
from gevent.queue import JoinableQueue
from rfc3986 import uri_reference

from scalpel.core.spider import Spider
from .files import write_mp
from .response import StaticResponse
from .robots import RobotsAnalyzer
from .utils.io import open_file

logger = logging.getLogger('scalpel')


@attr.s(slots=True)
class StaticSpider(Spider):
    """
    A spider suitable to parse files or static HTML files.

    **Parameters:**

    * **urls:** Urls to parse. Allowed schemes are `http`, `https` and `file`. It can be a `list`, a `tuple` or a `set`.
    * **parse:** A callable used to parse url content. It takes two arguments: the current spider and a
    `StaticResponse` object.
    * **reachable_urls:** `set` of urls that are already fetched or read.
    * **unreachable_urls:** `set` of urls that were impossible to fetch or read.
    * **robot_excluded_urls:** `set` of urls that were excluded to fetch because of *robots.txt* file rules.
    * **followed_urls:** `set` of urls that were followed during the process of parsing url content. You will find these
    urls scattered in the first three sets.
    * **request_counter:** The number of urls already fetched or read.

    Usage:

    ```
    from scalpel.green import StaticSpider, StaticResponse

    def parse(spider: StaticSpider, response: StaticResponse) -> None:
        ...

    spider = StaticSpider(urls=['http://example.com'], parse=parse)
    spider.run()
    ```
    """
    # order is important here, http_client must come before robots_analyzer since the latter used the former
    _start_time: float = attr.ib(init=False, factory=time, repr=False)
    _http_client: httpx.Client = attr.ib(init=False, repr=False)
    _robots_analyser: RobotsAnalyzer = attr.ib(init=False, repr=False)
    _fetch: Callable = attr.ib(init=False, repr=False)
    _lock: RLock = attr.ib(factory=RLock, init=False, repr=False)
    _pool: Pool = attr.ib(factory=Pool, init=False, repr=False)
    _queue: JoinableQueue = attr.ib(init=False, repr=False)

    def __attrs_post_init__(self):
        def _get_fetch(url: str) -> httpx.Response:
            return self._http_client.get(url)

        self._fetch = _get_fetch
        for middleware in self.config.response_middlewares:
            self._fetch = middleware(self._fetch)

    @_http_client.default
    def _get_http_client(self) -> httpx.Client:
        headers = {'User-Agent': self.config.user_agent}
        logger.debug('getting a default httpx client with user agent: %s', self.config.user_agent)
        return httpx.Client(headers=headers, timeout=self.config.fetch_timeout)

    @_robots_analyser.default
    def _get_robots_analyzer(self) -> RobotsAnalyzer:
        logger.debug('getting a default robots analyzer')
        return RobotsAnalyzer(
            http_client=self._http_client,
            robots_cache=self.config.robots_cache_folder,
            user_agent=self.config.user_agent
        )

    @_queue.default
    def _get_joinable_queue(self) -> JoinableQueue:
        logger.debug('getting a default joinable queue')
        return JoinableQueue(items=self.urls)

    def _get_static_response(
            self, url: str = '', text: str = '', httpx_response: httpx.Response = None
    ) -> StaticResponse:
        logger.debug(
            'returning StaticResponse object with url: %s, text: %s and httpx_response: %s', url, text, httpx_response
        )
        return StaticResponse(
            self.reachable_urls, self.followed_urls, self._queue, url=url, text=text, httpx_response=httpx_response
        )

    def _is_url_already_processed(self, url: str) -> bool:
        processed = False
        if url in [*self.reachable_urls, *self.unreachable_urls, *self.robots_excluded_urls]:
            logger.debug('url %s has already been processed', url)
            processed = True
        return processed

    def _is_url_excluded_for_spider(self, url: str) -> bool:
        excluded = False
        if self.config.follow_robots_txt:
            if not self._robots_analyser.can_fetch(url):
                logger.info('robots.txt rule has forbidden the processing of url %s or the url is not reachable', url)
                self.robots_excluded_urls.add(url)
                excluded = True
        return excluded

    # noinspection PyBroadException
    def _handle_url(self, url: str) -> None:
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
                before = time()
                with open_file(file_path) as f:
                    text = f.read()
                fetch_time = time() - before
            except OSError:
                logger.exception('unable to open file %s', url)
                self.unreachable_urls.add(url)
                return
        else:
            if self._is_url_excluded_for_spider(url):
                return

            response: httpx.Response = self._fetch(url)
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
            self.parse(self, self._get_static_response(static_url, text, response))
        except Exception:
            logger.exception('something unexpected happened while parsing the content at url %s', url)
            if not self._ignore_errors:
                raise
        logger.info('content at url %s has been processed', url)

    def save_item(self, item: Any) -> None:
        """Saves a scrapped item in the backup filename specified in `Configuration.backup_filename` attribute."""
        item_rejected = False
        original_item = item
        for processor in self.config.item_processors:
            item = processor(item)
            if item is None:
                item_rejected = True
                break
        if item_rejected:
            logger.debug('item %s was rejected', original_item)
            return

        logger.debug('writing item %s to file %s', item, self.config.backup_filename)
        with self._lock:
            write_mp(self.config.backup_filename, item, mode='a', encoder=self.config.msgpack_encoder)

    @staticmethod
    def _error_callback(task: gevent.Greenlet) -> None:
        if task.name == 'worker':
            logger.error('an unexpected error happened on the worker task', exc_info=task.exc_info)
        raise task.exception

    # NOTE: it is not possible to monkeypatch task_done method with pytest since JoinableQueue is a c-extension
    # this is why you will not see direct test of this method
    def _done_callback(self, *_) -> None:
        logger.debug('running greenlet done callback')
        self._queue.task_done()

    def _worker(self) -> None:
        # TODO: I had a weird LoopExit issue (while testing) when I tried to get the delay between requests
        #  and skipped some urls in the while loop, so to avoid it, I don't relay on robots.txt delay but on the one
        #  provided by config object.
        while True:
            task = self._pool.spawn(self._handle_url, self._queue.get())
            task.link_exception(self._error_callback)
            task.link(self._done_callback)
            gevent.sleep(self.config.request_delay)

    def _cleanup(self) -> None:
        """This method helps to cleanup resources. It should be override by SeleniumSpider."""
        self._http_client.close()

    def run(self) -> None:
        """Runs the spider."""
        worker_task = self._pool.spawn(self._worker)
        worker_task.name = 'worker'
        worker_task.link_exception(self._error_callback)
        self._queue.join()
        # at this point all urls were handled, so the only remaining task in the pool is the worker
        self._pool.killone(worker_task)
        self._cleanup()
        self._duration = time() - self._start_time
