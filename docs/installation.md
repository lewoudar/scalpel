# Installation

To install pyscalpel, you will need to have python and pip installed. For python the minimal version supported is **3.7**.
After you can just enter the following command:

```bash
pip install pyscalpel # to only use the asyncio backend
pip install pyscalpel[gevent] # to install the gevent backend
pip install pyscalpel[trio] # to install the trio backend
pip install pyscalpel[full] # to install all the backends
```

You can also have a look at the [poetry](https://python-poetry.org/docs/) project to manage your dependencies.

```bash
poetry add pyscalpel # to only use the asyncio backend
poetry add pyscalpel[gevent] # to install the gevent backend
poetry add pyscalpel[trio] # to install the trio backend
poetry add pyscalpel[full] # to install all the backends
```

This project relies on robust packages:

- [configuror](https://configuror.readthedocs.io/en/latest/): A configuration toolkit.
- [httpx](https://www.python-httpx.org/): A modern http client.
- [selenium](https://pypi.org/project/selenium/): A library for controlling a browser.
- [gevent](http://www.gevent.org/): An asynchronous framework using the synchronous way. (optional)
- [trio](https://trio.readthedocs.io/en/stable/): A modern asynchronous framework using `async/await` syntax. (optional)
- [anyio](https://anyio.readthedocs.io/): An asynchronous networking and concurrency library that works on top of
either asyncio or trio.
- [parsel](https://parsel.readthedocs.io/): A library elements in HTML/XML documents.
- [attrs](https://www.attrs.org/en/stable/): A library helping to write classes without pain.
- [fake-useragent](https://pypi.org/project/fake-useragent/): A simple library to fake a user agent.
- [rfc3986](https://rfc3986.readthedocs.io/en/latest/): A library for url parsing and validation.
- [msgpack](https://pypi.org/project/msgpack/): A library allowing for fast serialization/deserialization of data
structures.
