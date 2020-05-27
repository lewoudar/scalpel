import logging
from typing import Dict, Union
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)


class RobotsMixin:

    # noinspection PyTypeChecker
    @staticmethod
    def _get_request_delay(
            host: str,
            url: str,
            robots_parser: RobotFileParser,
            delay_mapping: Dict[str, Union[int, float]],
            default_delay: Union[int, float]
    ) -> Union[int, float]:
        pass

        crawl_delay = robots_parser.crawl_delay('*')
        if crawl_delay is not None:
            delay_mapping[host] = crawl_delay
            logger.debug('returning crawl delay value "%s" from robots.txt for url %s', crawl_delay, url)
            return crawl_delay

        request_rate = robots_parser.request_rate('*')
        if request_rate is not None:
            request_delay = request_rate.seconds / request_rate.requests
            delay_mapping[host] = request_delay
            logger.debug(
                'computing value "%s" from request delay info (%s/%s) from robots.txt for url %s',
                request_delay, request_rate.requests, request_rate.seconds, url
            )
            return request_delay

        delay_mapping[host] = default_delay
        logger.debug('returning default delay value "%s" for url %s', default_delay, url)
        return default_delay
