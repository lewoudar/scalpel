from datetime import datetime

import pytest

from scalpel.green import read_mp, write_mp


class TestReadMp:
    """Tests function read_mp"""

    # noinspection PyTypeChecker
    @pytest.mark.parametrize('decoder', ['foo', 4])
    def test_should_raise_error_when_decoder_is_not_callable(self, decoder):
        with pytest.raises(TypeError) as exc_info:
            next(read_mp('foo.mp', decoder=decoder))

        assert f'{decoder} is not callable' == str(exc_info.value)

    def test_should_return_python_objects_when_reading_file_without_custom_decoder(self, tmp_path, create_msgpack_file):
        given_data = [[1, 2], 'hello', {'fruit': 'apple'}]
        mp_file = tmp_path / 'data.mp'
        create_msgpack_file(mp_file, given_data)

        for file in [mp_file, f'{mp_file}']:
            assert list(read_mp(file)) == given_data

    def test_should_return_python_object_when_reading_file_with_custom_decoder(
        self, tmp_path, create_msgpack_file, decode_datetime
    ):
        given_data = ['hello', datetime.now()]
        mp_file = tmp_path / 'data.mp'
        create_msgpack_file(mp_file, given_data)

        assert list(read_mp(mp_file, decoder=decode_datetime)) == given_data


class TestWriteMp:
    """Tests function write_mp"""

    @pytest.mark.parametrize('mode', ['r', 'foo', 1])
    def test_should_raise_error_when_mode_is_not_correct(self, mode):
        with pytest.raises(TypeError) as exc_info:
            write_mp('foo', data=[], mode=mode)

        assert f'The only modes expected are "a" and "w" but you provided {mode}' == str(exc_info.value)

    # noinspection PyTypeChecker
    @pytest.mark.parametrize('encoder', ['foo', 4])
    def test_should_raise_error_when_encoder_is_not_callable(self, encoder):
        with pytest.raises(TypeError) as exc_info:
            write_mp('foo', data=[], encoder=encoder)

        assert f'{encoder} is not callable' == str(exc_info.value)

    def test_should_write_bytes_when_giving_content_in_write_mode_without_custom_encoder(self, tmp_path):
        content = {'name': 'Kevin', 'fruit': 'water melon'}
        mp_file = tmp_path / 'data.mp'
        length = write_mp(mp_file, content, mode='w')

        assert length > 0
        assert [content] == list(read_mp(mp_file))

    def test_should_write_bytes_when_giving_content_in_write_mode_with_custom_encoder(
        self, tmp_path, encode_datetime, decode_datetime
    ):
        content = {'name': 'Kevin', 'date': datetime.now()}
        mp_file = tmp_path / 'data.mp'
        length = write_mp(f'{mp_file}', content, mode='w', encoder=encode_datetime)

        assert length > 0
        assert [content] == list(read_mp(mp_file, decoder=decode_datetime))

    def test_should_write_bytes_when_giving_content_in_append_mode_without_custom_encoder(self, tmp_path):
        content = ['foo', 4, {'fruit': 'water melon'}, [1, 4]]
        mp_file = tmp_path / 'data.mp'

        for item in content:
            length = write_mp(mp_file, item, mode='a')
            assert length > 0

        assert content == list(read_mp(mp_file))

    def test_should_write_bytes_when_giving_content_in_append_mode_with_custom_encoder(
        self, tmp_path, encode_datetime, decode_datetime
    ):
        content = ['foo', datetime.now()]
        mp_file = tmp_path / 'data.mp'

        for item in content:
            length = write_mp(f'{mp_file}', item, mode='a', encoder=encode_datetime)
            assert length > 0

        assert content == list(read_mp(mp_file, decoder=decode_datetime))
