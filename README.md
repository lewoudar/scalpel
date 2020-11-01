# Pyscalpel

[![Pypi version](https://img.shields.io/pypi/v/pyscalpel.svg)](https://pypi.org/project/pyscalpel/)
![](https://github.com/lewoudar/actions-tutorial/workflows/CI/badge.svg)
[![Coverage Status](https://codecov.io/gh/lewoudar/scalpel/branch/master/graphs/badge.svg?branch=master)](https://codecov.io/gh/lewoudar/scalpel)
[![Documentation Status](https://readthedocs.org/projects/scalpel/badge/?version=latest)](https://scalpel.readthedocs.io/en/latest/?badge=latest)
[![License Apache 2](https://img.shields.io/hexpm/l/plug.svg)](http://www.apache.org/licenses/LICENSE-2.0)

Your easy-to-use, fast and powerful web scraping library.

## Why?

I already known [scrapy](https://docs.scrapy.org/en/latest/) which is the reference in python for web scraping. But
two things bothered me.
- I feel like scrapy cannot integrate into an existing project, you need to treat your web scraping stuff like a project
on its own.
- Usage of [Twisted](https://twistedmatrix.com/trac/) who is a veteran in asynchronous programming, but I think
 that there are better asynchronous frameworks today. Note that this second point is not true anymore as I'm writing
 the document since scrapy adds support for [asyncio](https://docs.scrapy.org/en/latest/topics/asyncio.html)
 
 After having made this observation I decided to create pyscalpel. And let's be honest, I also want to have my own web
 scraping library, and it is fun to write one ;)
 

## Installation
 
```bash
pip install pyscalpel[gevent] # to install the gevent backend
pip install pyscalpel[trio] # to installl the trio backend
pip install pyscalpel[full] # to install all the backends
```

If you know about [poetry](https://python-poetry.org/) you can use it instead of pip.

```bash
poetry add pyscalpel[gevent] # to install the gevent backend
poetry add pyscalpel[trio] # to install the trio backend
poetry add pyscalpel[full] # to install all the backends
```

pyscalpel works starting from **python 3.6**, it relies on robust packages:
- [configuror](https://configuror.readthedocs.io/en/latest/): A configuration toolkit. 
- [httpx](https://www.python-httpx.org/): A modern http client.
- [selenium](https://pypi.org/project/selenium/): A library for controlling a browser.
- [gevent](http://www.gevent.org/): An asynchronous framework using the synchronous way. (optional)
- [trio](https://trio.readthedocs.io/en/stable/): A modern asynchronous framework using `async/await` syntax. (optional)
- [parsel](https://parsel.readthedocs.io/): A library elements in HTML/XML documents.
- [attrs](https://www.attrs.org/en/stable/): A library helping to write classes without pain.
- [fake-useragent](https://pypi.org/project/fake-useragent/): A simple library to fake a user agent.
- [rfc3986](https://rfc3986.readthedocs.io/en/latest/): A library for url parsing and validation.
- [msgpack](https://pypi.org/project/msgpack/): A library allowing for fast serialization/deserialization of data
structures.

## Documentation

The documentation is in progress.


## Usage

To give you an overview of what can be done, this is a simple example of quote scraping. Don't hesitate to look at the
examples folder for more snippets to look at.

with gevent

```python
from pathlib import Path

from scalpel import Configuration
from scalpel.green import StaticSpider, StaticResponse, read_mp

def parse(spider: StaticSpider, response: StaticResponse) -> None:
    for quote in response.xpath('//div[@class="quote"]'):
        data = {
            'message': quote.xpath('./span[@class="text"]/text()').get(),
            'author': quote.xpath('./span/small/text()').get(),
            'tags': quote.xpath('./div/a/text()').getall()
        }
        spider.save_item(data)

    next_link = response.xpath('//nav/ul/li[@class="next"]/a').xpath('@href').get()
    if next_link is not None:
        response.follow(next_link)

if __name__ == '__main__':
    backup = Path(__file__).parent / 'backup.mp'
    config = Configuration(backup_filename=f'{backup}')
    spider = StaticSpider(urls=['http://quotes.toscrape.com'], parse=parse, config=config)
    spider.run()
    print(spider.statistics())
    # you can do whatever you want with the results
    for quote_data in read_mp(filename=backup, decoder=spider.config.msgpack_decoder):
        print(quote_data)
```

with trio

```python
from pathlib import Path

import trio
from scalpel import Configuration
from scalpel.trionic import StaticResponse, StaticSpider, read_mp


async def parse(spider: StaticSpider, response: StaticResponse) -> None:
    for quote in response.xpath('//div[@class="quote"]'):
        data = {
            'message': quote.xpath('./span[@class="text"]/text()').get(),
            'author': quote.xpath('./span/small/text()').get(),
            'tags': quote.xpath('./div/a/text()').getall()
        }
        await spider.save_item(data)

    next_link = response.xpath('//nav/ul/li[@class="next"]/a').xpath('@href').get()
    if next_link is not None:
        await response.follow(next_link)

async def main():
    backup = Path(__file__).parent / 'backup.mp'
    config = Configuration(backup_filename=f'{backup}')
    spider = StaticSpider(urls=['http://quotes.toscrape.com'], parse=parse, config=config)
    await spider.run()
    print(spider.statistics())
    # you can do whatever you want with the results
    async for item in read_mp(backup, decoder=spider.config.msgpack_decoder):
        print(item)

if __name__ == '__main__':
    trio.run(main)
```

## Known limitations

pyscalpel aims to handle SPA (single page application) through the use of selenium. However due to the synchronous nature
of selenium, it is hard to leverage trio and gevent asynchronous feature. You will notice that the *selenium spider* is
slower than the *static spider*. For more information look at the documentation.

## Warning

pyscalpel is a young project so it is expected to have breaking changes in the api without respecting the 
[semver](https://semver.org/) principle. It is recommended to pin the version you are using for now.