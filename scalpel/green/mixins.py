import logging
import time
from typing import Tuple

from selenium.common.exceptions import WebDriverException

logger = logging.getLogger('scalpel')


class SeleniumGetMixin:

    def _get_resource(self, url: str, error_message: str = '') -> Tuple[bool, float]:
        fetch_time = 0
        unreachable = False
        if not error_message:
            error_message = f'unable to get resource at {url}'
        try:
            before = time.time()
            self._driver.get(url)
            fetch_time = time.time() - before
        except WebDriverException:
            logger.exception(error_message)
            unreachable = True

        return unreachable, fetch_time
