"""Utility functions to read and write jl files"""
import logging
from pathlib import Path
from typing import Union, Iterator, Any, Callable

import msgpack

from .utils.io import open_file

logger = logging.getLogger('scalpel')


def read_mp(filename: Union[str, Path], decoder: Callable = None) -> Iterator[Any]:
    if decoder is not None and not callable(decoder):
        message = f'{decoder} is not callable'
        logger.exception(message)
        raise TypeError(message)

    with open_file(filename, 'rb') as f:
        unpacker = msgpack.Unpacker(f, object_hook=decoder)
        logger.debug('reading data from file %s', filename)
        for data in unpacker:
            yield data


def write_mp(filename: Union[str, Path], data: Any, mode: str = 'a', encoder: Callable = None) -> int:
    if mode not in ['a', 'w']:
        message = f'The only modes expected are "a" and "w" but you provided {mode}'
        logger.exception(message)
        raise TypeError(message)

    if encoder is not None and not callable(encoder):
        message = f'{encoder} is not callable'
        logger.exception(message)
        raise TypeError(message)

    with open_file(filename, f'{mode}b') as f:
        data_length = f.write(msgpack.packb(data, default=encoder))
        logger.debug('writing %s bytes in file %s', data_length, filename)
        return data_length
