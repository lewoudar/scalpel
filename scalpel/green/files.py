"""Utility functions to read and write mp files."""
import logging
from pathlib import Path
from typing import Union, Iterator, Any, Callable

import msgpack

from .utils.io import open_file

logger = logging.getLogger('scalpel')


def read_mp(filename: Union[str, Path], decoder: Callable = None) -> Iterator[Any]:
    """
    Reads a `msgpack` file generated by the spider when calling the `save_item` method.

    **Parameters:**

    * **filename:** The name of the file to read. It can be a string or a `pathlib.Path`.
    * **decoder:** An optional function used to decode data types not handled by default by `msgpack`.

    Usage:

    ```
    from scalpel import datetime_decoder
    from scalpel.green import read_mp

    for item in read_mp('file.mp', datetime_decoder):
        print(item)
    ```
    """
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
    """
    Writes a `msgpack` file.

    **Parameters:**

    * **filename:** The name of the file where data will be written. It can be a string or a `pathlib.Path`.
    * **data:** Arbitrary data to serialize. Note that if you want to serialize data types not supported by the `json`
    module, you will need to provide a custom encoder function.
    * **mode:** The mode in which the file is opened. Valid values are "a" (append) and "w" (write). Defaults to "a".
    * **encoder:** An optional function used to encode data types not handled by default by `msgpack`.

    **Returns:** The number of written bytes.

    Usage:

    ```
    from datetime import datetime
    from scalpel import datetime_encoder
    from scalpel.green import write_mp

    data = {'fruit': 'apple', 'date': datetime.utcnow()}
    length = write_mp('file.mp', data, 'w', datetime_encoder)
    print(length)  # 65
    ```
    """
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
