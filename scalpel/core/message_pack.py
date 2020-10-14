"""Helper datetime encoder and decoder for msgpack"""
from datetime import datetime
from typing import Any


def datetime_encoder(data: Any) -> Any:
    """
    A datetime encoder for `msgpack`

    Usage:

    ```
    from datetime import datetime
    from scalpel import datetime_encoder
    import msgpack

    data = {'fruit': 'apple', 'date': datetime.utcnow()}
    packed_data = msgpack.packb(data, default=datetime_encoder)
    ```
    """
    if isinstance(data, datetime):
        return {'__datetime__': True, 'as_str': data.strftime('%Y%m%dT%H:%M:%S.%f')}
    return data  # pragma: no cover


def datetime_decoder(data: Any) -> Any:
    """
    A datetime decoder for `msgpack`.

    Usage:

    ```
    from datetime import datetime
    from scalpel import datetime_encoder, datetime_decoder
    import msgpack

    data = {'fruit': 'apple', 'date': datetime.utcnow()}
    packed_data = msgpack.packb(data, default=datetime_encoder)
    assert msgpack.unpackb(packed_data, object_hook=datetime_decoder) == data
    ```
    """
    if '__datetime__' in data:
        data = datetime.strptime(data['as_str'], '%Y%m%dT%H:%M:%S.%f')
    return data
