# FAQ

## How do I run my spider using trio in asyncio code?

Here is a code snippet to show how to run trio code in asyncio.

```python
import asyncio

import trio
import sniffio
from scalpel.trionic import StaticSpider


async def parse(*_):
    pass


async def scrape(url):
    print(f'parsing {url} from {sniffio.current_async_library()}')
    spider = StaticSpider(urls=[url], parse=parse)
    await spider.run()


def run_trio():
    trio.run(scrape, 'http://foo.com')


async def main():
    loop = asyncio.get_event_loop()
    print(f'running main function from {sniffio.current_async_library()}')
    await loop.run_in_executor(None, run_trio)


# if you are using python3.7 upwards, you can replace the following lines with
# asyncio.run(main())
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

By the way, do you here about [anyio](https://anyio.readthedocs.io/en/stable/)? (yes I do a bit of advertising). It can
help you write beautiful code as with trio for asyncio :)

## How do I run my spider using gevent in asyncio code?

**Don't do that!** pyscalpel instructs gevent to monkeypatch various standard library modules and some like socket are
exploited by asyncio. This will probably result to weird errors. The only solution for you to integrate your spider in
asyncio code is to use `trio` and follow the above procedure.