import logging
from typing import Set

import attr
from gevent.queue import JoinableQueue

from scalpel.core.response import BaseStaticResponse

logger = logging.getLogger('scalpel')


@attr.s(slots=True)
class StaticResponse(BaseStaticResponse):
    _reachable_urls: Set[str] = attr.ib(validator=attr.validators.instance_of(set))
    _followed_urls: Set[str] = attr.ib(validator=attr.validators.instance_of(set))
    _queue: JoinableQueue = attr.ib(validator=attr.validators.instance_of(JoinableQueue))

    def follow(self, url: str) -> None:
        """
        Follows given url if it hasn't be fetched yet.
        :param url: the url to follow.
        """
        if url in self._followed_urls or url in self._reachable_urls:
            logger.debug('url %s has already been processed, nothing to do here', url)
            return

        logger.debug('adding url %s to spider reachable_urls and '
                     'followed_urls attributes and put in the queue to be processed', url)
        url = self._get_absolute_url(url)
        self._followed_urls.add(url)
        self._queue.put_nowait(url)
