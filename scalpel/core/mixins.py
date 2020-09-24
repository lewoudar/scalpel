import logging

import attr
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver

from .config import Browser

logger = logging.getLogger('scalpel')


@attr.s
class SeleniumDriverMixin:
    _driver: WebDriver = attr.ib(init=False, repr=False)

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
