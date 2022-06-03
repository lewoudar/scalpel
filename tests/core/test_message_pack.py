from datetime import datetime

import msgpack

from scalpel.core.message_pack import datetime_decoder, datetime_encoder


def test_should_encode_and_decode_datetimes():
    data = {'fruit': 'water melon', 'date': datetime.now()}
    packed_data = msgpack.packb(data, default=datetime_encoder)
    unpacked_data = msgpack.unpackb(packed_data, object_hook=datetime_decoder)

    assert data == unpacked_data
