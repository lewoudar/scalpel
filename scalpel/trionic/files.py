"""Utility async functions to read and write jl files"""
import logging
from typing import Union, AsyncIterator, Any

import msgpack
import trio

logger = logging.getLogger('scalpel')


async def read_jl(filename: Union[str, trio.Path]) -> AsyncIterator[Any]:
    async with await trio.open_file(filename, 'rb') as f:
        content = await f.read()
        unpacker = msgpack.Unpacker(None, max_buffer_size=len(content))
        unpacker.feed(content)
        logger.debug('reading data from file %s', filename)
        for data in unpacker:
            yield data


async def write_jl(filename: Union[str, trio.Path], data: Any, mode: str = 'w') -> int:
    if mode not in ['a', 'w']:
        message = f'The only modes expected are "a" and "w" but you provided {mode}'
        logger.exception(message)
        raise TypeError(message)

    async with await trio.open_file(filename, f'{mode}b') as f:
        data_length = await f.write(msgpack.packb(data))
        logger.debug('writing %s bytes in file %s', data_length, filename)
        return data_length
