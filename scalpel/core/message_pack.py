"""Helper datetime encoder and decoder for msgpack"""
from datetime import datetime
from typing import Any


def datetime_encoder(data: Any) -> dict:
    if isinstance(data, datetime):
        return {'__datetime__': True, 'as_str': data.strftime('%Y%m%dT%H:%M:%S.%f')}
    return data


def datetime_decoder(data: Any) -> Any:
    if '__datetime__' in data:
        data = datetime.strptime(data['as_str'], '%Y%m%dT%H:%M:%S.%f')
    return data
