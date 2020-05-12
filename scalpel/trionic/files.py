"""Utility async functions to read and write jl files"""
import logging
from typing import Union, AsyncIterator, Any, Callable

import msgpack
import trio

logger = logging.getLogger('scalpel')


async def read_mp(filename: Union[str, trio.Path], decoder: Callable = None) -> AsyncIterator[Any]:
    if decoder is not None and not callable(decoder):
        message = f'{decoder} is not callable'
        logger.exception(message)
        raise TypeError(message)

    async with await trio.open_file(filename, 'rb') as f:
        content = await f.read()
        unpacker = msgpack.Unpacker(None, max_buffer_size=len(content), object_hook=decoder)
        unpacker.feed(content)
        logger.debug('reading data from file %s', filename)
        for data in unpacker:
            yield data


async def write_mp(filename: Union[str, trio.Path], data: Any, mode: str = 'w', encoder: Callable = None) -> int:
    if mode not in ['a', 'w']:
        message = f'The only modes expected are "a" and "w" but you provided {mode}'
        logger.exception(message)
        raise TypeError(message)

    if encoder is not None and not callable(encoder):
        message = f'{encoder} is not callable'
        logger.exception(message)
        raise TypeError(message)

    async with await trio.open_file(filename, f'{mode}b') as f:
        data_length = await f.write(msgpack.packb(data, default=encoder))
        logger.debug('writing %s bytes in file %s', data_length, filename)
        return data_length
