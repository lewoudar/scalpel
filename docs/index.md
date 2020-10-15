# Scalpel documentation

Everything you need to know about scalpel.

## Why scalpel?

I already known [scrapy](https://docs.scrapy.org/en/latest/) which is the reference in python for web scraping. But
two things bothered me.
- I feel like scrapy cannot integrate into an existing project, you need to treat your web scraping stuff like a project
on its own.
- Usage of [Twisted](https://twistedmatrix.com/trac/) who is a veteran in asynchronous programming, but I think
 that there are better asynchronous frameworks today. Note that this second point is not true anymore as I'm writing
 the document since scrapy adds support for [asyncio](https://docs.scrapy.org/en/latest/topics/asyncio.html)
 
 After having made this observation I decided to create scalpel. And let's be honest, I also want to have my own web
 scraping library, and it is fun to write one ;)
 
## Features
 
- Ability to parse documents using `gevent` or `trio` asynchronous frameworks.
- Ability to parse SPA (Single Page Applications) using `selenium`.
- Fast serialization for scrapped items with `msgpack`.
- Ability to follow *robots.txt* rules.
- Ability to filter or updated scrapped items.
- Middleware system to modify responses (only for static responses).
 
## Contents
 
- [Installation](installation.md)
- [Configuration](configuration.md)
- [Static spider](static_spider.md)
- [API](api.md)