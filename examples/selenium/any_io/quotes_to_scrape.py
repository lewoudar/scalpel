"""Simple example to show usage of anyio SeleniumSpider class"""
from datetime import datetime
from pathlib import Path

import anyio
from selenium.common.exceptions import NoSuchElementException

from scalpel import Configuration, datetime_decoder
from scalpel.any_io import SeleniumSpider, SeleniumResponse, read_mp


async def parse(spider: SeleniumSpider, response: SeleniumResponse) -> None:
    for quote_tag in response.driver.find_elements_by_xpath('//div[@class="quote"]'):
        await spider.save_item({
            'quote': quote_tag.find_element_by_xpath('./span[@class="text"]').text,
            'author': quote_tag.find_element_by_xpath('./span/small').text,
            'tags': [item.text for item in quote_tag.find_elements_by_xpath('./div/a')]
        })

    next_link = None
    try:
        element = response.driver.find_element_by_xpath('//nav/ul/li[@class="next"]/a')
        next_link = element.get_attribute('href')
    except NoSuchElementException:
        pass

    if next_link is not None:
        await response.follow(next_link)


def date_processor(item: dict) -> dict:
    item['date'] = datetime.now()
    return item


async def main() -> None:
    backup = Path(__file__).parent / 'backup.mp'
    config = Configuration(selenium_driver_log_file=None, backup_filename=f'{backup}', item_processors=[date_processor])
    spider = SeleniumSpider(urls=['http://quotes.toscrape.com'], parse=parse, config=config)
    await spider.run()
    print(spider.statistics())
    # you can do whatever you want with the results
    async for quote in read_mp(filename=backup, decoder=datetime_decoder):
        print(quote)


if __name__ == '__main__':
    anyio.run(main)
