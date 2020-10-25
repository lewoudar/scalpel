# Item processing

A cool feature about scalpel is that it lets you decouple item scraping from its analyzing through the *item processors*.
Note that this require that you **save** your item using the `save_item` method of a response object. It can help
you to reduce the amount of logic in your parse function.

## Configuration

Item processors are just functions that are run one after the other on a scrapped item. The idea is that you can modify
an item to add or update some information or you can simply discard the item if it does not meet certain criteria.
To register item processors, this is what you can do.

```python
from scalpel import Configuration

def processor_1(item):
    ...

async def processor_2(item):
   ...

config = Configuration(item_processors=[processor_1, processor_2])
```

As you will have noticed in the example, item processors can be synchronous or asynchronous. Obviously the asynchronous
version is only valid if you are dealing with a `trio` spider. If you use an asynchronous function inside a green spider,
you can be sure your application will crash.

!!! note
    The processors are run in the order there are listed when instantiating configuration. So put the most important
    ones at the beginning.
    
## example

If we come back to our quotes example in the [static spider](static-spider.md) we have done something like that in the
parse function:

```python
data = {
    'message': quote.xpath('./span[@class="text"]/text()').get(),
    'author': quote.xpath('./span/small/text()').get(),
    'tags': quote.xpath('./div/a/text()').getall()
}
spider.save_item(data)
```

So we save an item with three properties `message`,`author` and `tags`. Now lets add a date. And let's say we don't like
Marylin Monroe, so we want to remove her quotes from the result 😆

I will show an example with gevent, but you should now know how to use trio at this point of the documentation.

```python
from datetime import datetime
from scalpel import Configuration
from scalpel.green import StaticSpider

def datetime_processor(item: dict) -> dict:
    item['date'] = datetime.utcnow()
    return item

def marylin_processor(item: dict) -> None:
    if item['author'] == 'Marilyn Monroe':
        return

def parse(static_spider, response):
    ...

config = Configuration(item_processors=[marylin_processor, datetime_processor])
spider = StaticSpider(urls=['https://quotes.toscrape.com/'], parse=parse, config=config)
```

So that is it! For the case you want to drop an item you just need to return `None` from the processor function. Worth
to mention that if a processor returns `None` the following processors are not called.

## Note on custom object serialization / deserialization

If you know [msgpack](https://pypi.org/project/msgpack/), you know that it cannot serialize `datetime` objects by
default. So if you called the `read_mp` function like we did in the static spider guide, it will raise an error.
So how can we read `datetime` objects? Well, if you look at the scalpel [msgpack api](api.md#msgpack) you will noticed
a `datetime_decoder` which is a helper to deserialize `datetime` objects. Also the [Configuration](api.md#configuration)
object has a `msgpack_decoder` attribute which default value is `datetime_decoder`. So here is how you can read
`datetime` objects.

With gevent:

```python
from scalpel import Configuration
from scalpel.green import read_mp, StaticSpider

def parse(spider, response):
    ...


config = Configuration(backup_filename='toto.mp')
spider = StaticSpider(urls=['http//foo.com'], parse=parse, config=config)
spider.run()

# read_mp accepts a callback where we can specify how to deserialize custom objects in msgpack
for data in read_mp('toto.mp', decoder=config.msgpack_decoder):
    print(data)
```

With trio:

```python
import trio
from scalpel import Configuration
from scalpel.trionic import StaticSpider, read_mp

async def parse(spider, response):
    ...

async def main():
    config = Configuration(backup_filename='toto.mp')
    spider = StaticSpider(urls=['http//foo.com'], parse=parse, config=config)
    await spider.run()

    # read_mp accepts a callback where we can specify how to deserialize custom objects in msgpack
    async for data in read_mp('toto.mp', decoder=config.msgpack_decoder):
        print(data)

trio.run(main)
```