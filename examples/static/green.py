"""Simple example to show how to use the green StaticSpider class"""
from datetime import datetime
from pathlib import Path

from scalpel import Configuration
from scalpel.green import StaticResponse, StaticSpider, read_mp


def parse(spider: StaticSpider, response: StaticResponse) -> None:
    for quote in response.xpath('//div[@class="quote"]'):
        data = {
            'message': quote.xpath('./span[@class="text"]/text()').get(),
            'author': quote.xpath('./span/small/text()').get(),
            'tags': quote.xpath('./div/a/text()').getall(),
        }
        spider.save_item(data)

    next_link = response.xpath('//nav/ul/li[@class="next"]/a').xpath('@href').get()
    if next_link is not None:
        response.follow(next_link)


def date_processor(item: dict) -> dict:
    item['date'] = datetime.now()
    return item


if __name__ == '__main__':
    backup = Path(__file__).parent / 'backup.mp'
    config = Configuration(backup_filename=f'{backup}', item_processors=[date_processor])
    spider = StaticSpider(urls=['http://quotes.toscrape.com'], parse=parse, config=config)
    spider.run()
    print(spider.statistics())
    # you can do whatever you want with the results
    for quote_data in read_mp(filename=backup, decoder=spider.config.msgpack_decoder):
        print(quote_data)
