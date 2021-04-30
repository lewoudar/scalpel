# Response middlewares

pyscalpel comes with the ability to intercept responses produced by httpx when fetching urls. This is a feature only
available for **static spiders**. The reason is that for selenium we can't determine exactly when the request to fetch
url resource is done.

## Usage

It is really simple to use the middleware system. If you know how to use decorators in python, you already know how to
use middlewares in pyscalpel. Something important to mention, you **must** return the
[httpx response](https://www.python-httpx.org/api/#response) object since pyscalpel relies on it. You are only allowed to
perform operations before the response object is created, inspect the created object, not discard it or return another
object. Here is an example.

With gevent:

```python
from scalpel import Configuration
from scalpel.green import StaticSpider

def middleware(fetch):
    # here you can do some initialization
    print('initialization')

    def wrapper(url):
        # code to be executed before each request, here I just print information
        # but you can do whatever you want
        print('url processed in function middleware:', url)
        print('before processing')
        response = fetch(url)
        # code to executed after each request
        print('after processing')
        # important to return the response
        return response

    return wrapper

# we can do the same thing with a class middleware
class SimpleMiddleware:

    def __init__(self, fetch):
        self.fetch = fetch
        # you can do other initialization here
        print('class initialization')

    def __call__(self, url):
        print('url processed in class middleware:', url)
        print('before class processing')
        response = self.fetch(url)
        print('after class processing')
        return response

def parse(*_):
    pass

config = Configuration(response_middlewares=[middleware, SimpleMiddleware])
spider = StaticSpider(urls=['http://foo.com'], parse=parse, config=config)
spider.run()
```

With anyio:

```python
import anyio
from scalpel import Configuration
from scalpel.any_io import StaticSpider


def middleware(fetch):
    # here you can do some initialization
    print('initialization')

    async def wrapper(url):
        # code to be executed before each request, here I just print information
        # but you can do whatever you want
        print('url processed in function middleware:', url)
        print('before processing')
        response = await fetch(url)
        # code to executed after each request
        print('after processing')
        # important to return the response
        return response

    return wrapper


# we can do the same thing with class middleware
class SimpleMiddleware:
    def __init__(self, fetch):
        self.fetch = fetch
        # here you can do other initialization
        print('class initialization')

    async def __call__(self, url):
        print('url processed in class middleware:', url)
        print('before class processing')
        response = await self.fetch(url)
        print('after class processing')
        return response

async def parse(*_):
    pass


async def main():
    config = Configuration(response_middlewares=[middleware, SimpleMiddleware])
    spider = StaticSpider(urls=['http://foo.com'], parse=parse, config=config)
    await spider.run()

anyio.run(main)  # with trio: anyio.run(main, backend='trio')
```

Output:

```bash
initialization
class initialization
url processed in class middleware: http://foo.com
before class processing
url processed in function middleware: http://foo.com
before processing
after processing
after class processing
```

With the output, you can have an idea in what order the middleware code is executed.

!!! note
    Keep in mind that the more middlewares you add, the more slower your spider will be.