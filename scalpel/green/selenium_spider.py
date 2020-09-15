import logging

import attr
from rfc3986 import uri_reference
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver

from scalpel.core.config import Browser
from .mixins import SeleniumGetMixin
from .response import SeleniumResponse
from .static_spider import StaticSpider

logger = logging.getLogger('scalpel')


@attr.s(slots=True)
class SeleniumSpider(SeleniumGetMixin, StaticSpider):
    _driver: WebDriver = attr.ib(init=False, repr=False)

    def __attrs_post_init__(self):
        # this erases the content of StaticSpider.__attrs_post_init__ which is not useful here
        pass

    @_driver.default
    def _get_driver(self) -> WebDriver:
        if self.config.selenium_browser is Browser.FIREFOX:
            logger.debug('returning firefox driver')
            options = FirefoxOptions()
            options.headless = True
            driver = webdriver.Firefox(
                options=options, executable_path=self.config.selenium_driver_executable_path,
                service_log_path=self.config.selenium_driver_log_file
            )
        else:
            logger.debug('returning chrome driver')
            options = ChromeOptions()
            options.add_argument('--headless')
            driver = webdriver.Chrome(
                options=options, executable_path=self.config.selenium_driver_executable_path,
                service_log_path=self.config.selenium_driver_log_file
            )
        driver.implicitly_wait(self.config.selenium_find_timeout)
        return driver

    def _get_selenium_response(self, handle: str) -> SeleniumResponse:
        return SeleniumResponse(
            self.reachable_urls, self.followed_urls, self._queue, driver=self._driver, handle=handle
        )

    def _cleanup(self):
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
