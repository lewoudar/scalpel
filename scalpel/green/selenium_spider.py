import logging

import attr
from rfc3986 import uri_reference

from scalpel.core.selenium import SeleniumDriverMixin
from .mixins import SeleniumGetMixin
from .response import SeleniumResponse
from .static_spider import StaticSpider

logger = logging.getLogger('scalpel')


# usually mixins are put are the beginning but in the case of SeleniumDriverMixin
# it depends on _config property defined in StaticSpider, so it has to be put at the end
@attr.s(slots=True)
class SeleniumSpider(SeleniumGetMixin, StaticSpider, SeleniumDriverMixin):
    """
    A spider suitable to parse dynamic websites i.e where Javascript is heavily used. You will sometimes encounter the
    term Single-Page Application (SPA) for this type of website. It relies on `selenium` package and a browser.

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
    from scalpel.green import SeleniumSpider, SeleniumResponse

    def parse(spider: SeleniumSpider, response: SeleniumResponse) -> None:
        ...

    spider = SeleniumSpider(urls=['http://example.com'], parse=parse)
    spider.run()
    ```
    """

    def __attrs_post_init__(self):
        # this erases the content of StaticSpider.__attrs_post_init__ which is not useful here
        pass

    def _get_selenium_response(self, handle: str) -> SeleniumResponse:
        return SeleniumResponse(
            self.reachable_urls, self.followed_urls, self._queue, driver=self._driver, handle=handle
        )

    def _cleanup(self) -> None:
        self._http_client.close()
        self._driver.quit()

    # noinspection PyBroadException
    def _handle_url(self, url: str) -> None:
        if self._is_url_already_processed(url):
            return

        ur = uri_reference(url)
        error_message = ''
        if ur.scheme == 'file':
            error_message = f'unable to open file {url}'
        else:
            if self._is_url_excluded_for_spider(url):
                return
        unreachable, fetch_time = self._get_resource(url, error_message)
        if unreachable:
            self.unreachable_urls.add(url)
            return
        # we update some stats
        self.request_counter += 1
        self._total_fetch_time += fetch_time
        self.reachable_urls.add(url)

        handle = self._driver.current_window_handle
        try:
            self.parse(self, self._get_selenium_response(handle))
        except Exception:
            logger.exception('something unexpected happened while parsing the content at url %s', url)
            if not self._ignore_errors:
                raise
        logger.info('content at url %s has been processed', url)
