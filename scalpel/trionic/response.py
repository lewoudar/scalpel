import logging
from typing import Set

import attr
import trio

from scalpel.core.response import BaseStaticResponse

logger = logging.getLogger('scalpel')


@attr.s(slots=True)
class StaticResponse(BaseStaticResponse):
    _reachable_urls: Set[str] = attr.ib(validator=attr.validators.instance_of(set))
    _followed_urls: Set[str] = attr.ib(validator=attr.validators.instance_of(set))
    _send_channel: trio.MemorySendChannel = attr.ib(validator=attr.validators.instance_of(trio.MemorySendChannel))

    async def follow(self, url: str) -> None:
        """
        Follows given url if it hasn't be fetched yet.
        :param url: the url to follow.
        """
        if url in self._followed_urls or url in self._reachable_urls:
            logger.debug('url %s has already been processed, nothing to do here', url)
            return

        logger.debug('adding url %s to spider followed_urls attribute and put in the channel to be processed', url)
        url = self._get_absolute_url(url)
        self._followed_urls.add(url)
        await self._send_channel.send(url)
