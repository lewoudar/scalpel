# Installation

To install scalpel, you will need to have python and pip installed. After you can just enter the following command:

```bash
pip install scalpel
```

You can also have a look at the [poetry](https://python-poetry.org/docs/) project to manage your dependencies.

```bash
poetry add scalpel
```

This project works starting from **python3.6** and relies on robust packages:

- [configuror](https://configuror.readthedocs.io/en/latest/): A configuration toolkit. 
- [httpx](https://www.python-httpx.org/): A modern http client.
- [selenium](https://pypi.org/project/selenium/): A library for controlling a browser.
- [gevent](http://www.gevent.org/): An asynchronous framework using the synchronous way.
- [trio](https://trio.readthedocs.io/en/stable/): A modern asynchronous framework using `async/await` syntax.
- [parsel](https://parsel.readthedocs.io/): A library elements in HTML/XML documents.
- [attrs](https://www.attrs.org/en/stable/): A library helping to write classes without pain.
- [fake-useragent](https://pypi.org/project/fake-useragent/): A simple library to fake a user agent.
- [rfc3986](https://rfc3986.readthedocs.io/en/latest/): A library for url parsing and validation.
- [msgpack](https://pypi.org/project/msgpack/): A library allowing for fast serialization/deserialization of data
structures.