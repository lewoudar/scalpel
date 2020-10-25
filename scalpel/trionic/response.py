import logging
from typing import Set

import attr

from scalpel.core.response import BaseStaticResponse, BaseSeleniumResponse
from .utils.queue import Queue

logger = logging.getLogger('scalpel')


class FollowMixin:

    async def follow(self, url: str) -> None:
        """
        Follows given url if it hasn't be fetched yet.

        **Parameters:**

        * **url:** The url to follow.
        """
        if url in self._followed_urls or url in self._reachable_urls:
            logger.debug('url %s has already been processed, nothing to do here', url)
            return

        logger.debug('adding url %s to spider followed_urls attribute and put in the channel to be processed', url)
        url = self._get_absolute_url(url)
        self._followed_urls.add(url)
        await self._queue.put(url)


@attr.s
class CommonAttributes:
    _reachable_urls: Set[str] = attr.ib(validator=attr.validators.instance_of(set))
    _followed_urls: Set[str] = attr.ib(validator=attr.validators.instance_of(set))
    _queue: Queue = attr.ib(validator=attr.validators.instance_of(Queue))


@attr.s(slots=True)
class StaticResponse(CommonAttributes, FollowMixin, BaseStaticResponse):
    """
    A response class used in combination with a `StaticSpider` object in the `parse` async callable of a spider.

    **N.B:** You probably don't need to instantiate this class directly unless for some kind of testing. It is mainly
    exposed for annotation purpose.

    **Parameters:**

    * **reachable_urls:** A `set` of urls already fetched.
    * **followed_urls:** A `set` of urls already followed by other `StaticResponse` objects.
    * **queue:** The `scalpel.trionic.Queue` used by the spider to handle incoming urls.
    * **url:** An optional keyword parameter representing the current url where content was fetched.
    * **text:** An optional keyword parameter representing the content of the resource fetched. Note that if you set
    the `url` parameter, you **must** set this one.
    * **httpx_response:** An optional keyword parameter representing an `httpx.Response` of the resource fetched.
    For HTTP urls, this is the one used in favour of `url` and `text` parameters.

    Usage:

    ```python
    from scalpel.trionic import StaticResponse

    response = StaticResponse(..., url='http://foo.com', text='<p>Hello world!</p>')
    print(response.css('p::text').get())  # 'Hello world!'
    print(response.xpath('//p/text()').get())  # 'Hello world!'
    ```
    """
    pass


@attr.s(slots=True)
class SeleniumResponse(CommonAttributes, FollowMixin, BaseSeleniumResponse):
    """
    A response class used in combination with a `SeleniumSpider` object in the `parse` async callable of a spider.

    **N.B:** You probably don't need to instantiate this class directly unless for some kind of testing. It is mainly
    exposed for annotation purpose.

    **Parameters:**

    * **reachable_urls:** A `set` of urls already fetched.
    * **followed_urls:** A `set` of urls already followed by other `StaticResponse` objects.
    * **queue:** The `gevent.queue.JoinableQueue` used by the spider to handle incoming urls.
    * **driver:** The `selenium.WebDriver` object that will be use to control the running browser.
    * **handle:** A string that identifies the current window handled by `selenium`.

    Usage:

    ```
    from scalpel.trionic import SeleniumResponse

    response = SeleniumResponse(...)
    # We assume we have a page source like '<p>Hello world!</p>'
    print(response.driver.find_element_by_xpath('//p').text)  # Hello world!
    ```
    """
    pass
