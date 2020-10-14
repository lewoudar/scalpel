"""Utilities to read / write files and manage different IO buffers"""
from io import BufferedReader, open
from typing import IO, AnyStr, Union, List, Optional, Iterator, Any, TypeVar, Callable

import attr
from gevent import get_hub
from gevent.threadpool import ThreadPool

File = TypeVar('File')


@attr.s
class AsyncFile:
    """
    A wrapper around builtins io objects like `io.StringIO` or `io.BufferedReader` running blocking operations like
    `read` or `write` in a threadpool to make it gevent cooperative.
    """
    _wrapper: Union[IO, BufferedReader] = attr.ib()
    _pool: ThreadPool = attr.ib(init=False)

    @_pool.default
    def _get_pool(self) -> ThreadPool:
        return get_hub().threadpool

    def read(self, size: int = -1) -> AnyStr:
        return self._pool.spawn(self._wrapper.read, size).get()

    def read1(self, size: int = -1) -> AnyStr:
        return self._pool.spawn(self._wrapper.read1, size).get()

    def readline(self, size: int = -1) -> AnyStr:
        return self._pool.spawn(self._wrapper.readline, size).get()

    def readlines(self, hint: int = -1) -> List[AnyStr]:
        return self._pool.spawn(self._wrapper.readlines, hint).get()

    def readinto(self, b: Union[bytes, bytearray, memoryview]) -> int:
        return self._pool.spawn(self._wrapper.readinto, b).get()

    def readinto1(self, b: Union[bytes, bytearray, memoryview]) -> int:
        return self._pool.spawn(self._wrapper.readinto1, b).get()

    def seek(self, offset: int, whence: int = 0) -> int:
        return self._pool.spawn(self._wrapper.seek, offset, whence).get()

    def tell(self) -> int:
        return self._pool.spawn(self._wrapper.tell).get()

    def write(self, s: AnyStr) -> int:
        return self._pool.spawn(self._wrapper.write, s).get()

    def writelines(self, lines: List[AnyStr]) -> None:
        return self._pool.spawn(self._wrapper.writelines, lines).get()

    def truncate(self, size: Optional[int] = None) -> int:
        return self._pool.spawn(self._wrapper.truncate, size).get()

    def peek(self, size: Optional[int] = None) -> bytes:
        return self._pool.spawn(self._wrapper.peek, size).get()

    def flush(self) -> None:
        return self._pool.spawn(self._wrapper.flush).get()

    def close(self) -> None:
        return self._pool.spawn(self._wrapper.close).get()

    def __enter__(self) -> 'AsyncFile':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return self.close()

    def __iter__(self) -> Iterator[AnyStr]:
        while True:
            line = self.readline()
            if not line:
                break
            yield line

    def __getattr__(self, item: str) -> Any:
        return getattr(self._wrapper, item)


def _has(file: Union[IO, BufferedReader], attribute: str) -> bool:
    return hasattr(file, attribute) and callable(getattr(file, attribute))


def wrap_file(file: Union[IO, BufferedReader]) -> AsyncFile:
    """
    This function wraps any file object in a wrapper that provides an asynchronous (or gevent cooperative)
    file object interface.

    **Parameters:**

    * **file:** A file-like object.

    **Returns:** An `AsyncFile` object.

    Usage:

    ```
    from io import StringIO
    from scalpel.green import wrap_file

    s = StringIO()
    async_s = wrap_file(s)
    assert 5 == async_s.write('hello')
    assert 'hello' == async_s.getvalue()
    ```
    """
    if not _has(file, 'close'):
        raise TypeError(f'{file} does not implement close method which is mandatory for a file-like object')

    if not _has(file, 'read') or not _has(file, 'write'):
        raise TypeError(f'{file} does not implement read or write method which is mandatory for a file-like object')

    return AsyncFile(file)


def open_file(
        file: File,
        mode: str = 'r',
        buffering: int = -1,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
        closefd: bool = True,
        opener: Callable = None
) -> AsyncFile:
    """
    An asynchronous version of the builtin `open` function running blocking operation in a threadpool.

    **Parameters:**
    The parameters are exactly the same as those passed to the builtin `open` function. You can check the official
    documentation to understand their meaning.

    **Returns:** An `AsyncFile` object.

    Usage:

    ```
    from scalpel.green import open_file

    with open_file('hello.txt', 'w') as f:
        f.write('hello world')

    with open_file('hello.txt') as f:
        print(f.read())  # 'hello world'
    ```
    """
    threadpool = get_hub().threadpool
    file = threadpool.spawn(open, file, mode, buffering, encoding, errors, newline, closefd, opener).get()
    return wrap_file(file)
