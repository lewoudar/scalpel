import attr
import pytest
from selenium.webdriver.remote.webdriver import WebDriver

from scalpel.core.config import Browser, Configuration
from scalpel.core.mixins import SeleniumDriverMixin
from scalpel.core.spider import Spider


class TestSeleniumDriverMixin:
    """Tests SeleniumDriverMixin _driver attribute"""

    @attr.s
    class CustomSpider(Spider, SeleniumDriverMixin):
        @property
        def driver(self):
            return self._driver

    @pytest.mark.parametrize(('browser', 'name'), [
        (Browser.CHROME, 'chrome'),
        (Browser.FIREFOX, 'firefox')
    ])
    def test_should_instantiate_correctly_driver_attribute(self, browser, name):
        config = Configuration(selenium_browser=browser, selenium_driver_log_file=None)
        spider = self.CustomSpider(urls=['http://foo.com'], parse=lambda x, y: None, config=config)

        assert isinstance(spider.driver, WebDriver)
        assert name == spider.driver.name

        # cleanup
        spider.driver.quit()
