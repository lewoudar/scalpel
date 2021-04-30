# FAQ

## How do I run my spider using gevent in asyncio code?

**Don't do that!** pyscalpel instructs gevent to monkeypatch various standard library modules and some like socket are
exploited by asyncio. This will probably result to weird errors. The only solution for you to integrate your spider in
asyncio code is to use `trio` and follow the above procedure.