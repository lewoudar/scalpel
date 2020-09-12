import logging
from typing import Set

import attr
from gevent.queue import JoinableQueue

from scalpel.core.response import BaseStaticResponse, BaseSeleniumResponse

logger = logging.getLogger('scalpel')


class FollowMixin:
    def follow(self, url: str) -> None:
        """
        Follows given url if it hasn't be fetched yet.
        :param url: the url to follow.
        """
        if url in self._followed_urls or url in self._reachable_urls:
            logger.debug('url %s has already been processed, nothing to do here', url)
            return

        logger.debug('adding url %s to spider followed_urls attribute and put in the queue to be processed', url)
        url = self._get_absolute_url(url)
        self._followed_urls.add(url)
        self._queue.put_nowait(url)


@attr.s
class CommonAttributes:
    _reachable_urls: Set[str] = attr.ib(validator=attr.validators.instance_of(set))
    _followed_urls: Set[str] = attr.ib(validator=attr.validators.instance_of(set))
    _queue: JoinableQueue = attr.ib(validator=attr.validators.instance_of(JoinableQueue))


@attr.s(slots=True)
class StaticResponse(CommonAttributes, FollowMixin, BaseStaticResponse):
    pass


@attr.s(slots=True)
class SeleniumResponse(CommonAttributes, FollowMixin, BaseSeleniumResponse):
    pass
