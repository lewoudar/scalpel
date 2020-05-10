"""Utility functions to read and write jl files"""
import logging
from pathlib import Path
from typing import Union, Iterator, Any

import msgpack

logger = logging.getLogger('scalpel')


# Usage of gevent.fileobject.FileObjectThread gives a strange error
# so I just use a regular file object for these functions

def read_jl(filename: Union[str, Path]) -> Iterator[Any]:
    with open(filename, 'rb') as f:
        unpacker = msgpack.Unpacker(f)
        logger.debug('reading data from file %s', filename)
        for data in unpacker:
            yield data


def write_jl(filename: Union[str, Path], data: Any, mode: str = 'a') -> int:
    if mode not in ['a', 'w']:
        message = f'The only modes expected are "a" and "w" but you provided {mode}'
        logger.exception(message)
        raise TypeError(message)

    with open(filename, f'{mode}b') as f:
        data_length = f.write(msgpack.packb(data))
        logger.debug('writing %s bytes in file %s', data_length, filename)
        return data_length
