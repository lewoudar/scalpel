from datetime import datetime

import pytest
import trio

from scalpel.trionic import read_mp, write_mp


class TestReadMp:
    """Tests function read_mp"""

    # noinspection PyTypeChecker
    @pytest.mark.parametrize('decoder', ['foo', 4])
    async def test_should_raise_error_when_decoder_is_not_callable(self, decoder):
        with pytest.raises(TypeError) as exc_info:
            async for item in read_mp('foo', decoder=decoder):
                print(item)

        assert f'{decoder} is not callable' == str(exc_info.value)

    async def test_should_return_python_objects_when_reading_file_without_custom_decoder(self, tmp_path,
                                                                                         create_msgpack_file):
        given_data = [[1, 2], 'hello', {'fruit': 'apple'}]
        mp_file = tmp_path / 'data.mp'
        create_msgpack_file(mp_file, given_data)

        for file in [f'{mp_file}', trio.Path(mp_file)]:
            assert [item async for item in read_mp(file)] == given_data

    async def test_should_return_python_objects_when_reading_file_with_custom_decoder(self, tmp_path, decode_datetime,
                                                                                      create_msgpack_file):
        given_data = ['hello', datetime.now()]
        mp_file = tmp_path / 'data.mp'
        create_msgpack_file(mp_file, given_data)

        for file in [str(mp_file), trio.Path(mp_file)]:
            assert [item async for item in read_mp(file, decoder=decode_datetime)] == given_data


class TestWriteMp:
    """Tests function write_mp"""

    @pytest.mark.parametrize('mode', ['r', 'foo', 4])
    async def test_should_raise_error_when_mode_is_not_correct(self, mode):
        with pytest.raises(TypeError) as exc_info:
            await write_mp('foo', [], mode=mode)

        assert f'The only modes expected are "a" and "w" but you provided {mode}' == str(exc_info.value)

    # noinspection PyTypeChecker
    @pytest.mark.parametrize('encoder', ['foo', 4])
    async def test_should_raise_error_when_encoder_is_not_callable(self, encoder):
        with pytest.raises(TypeError) as exc_info:
            await write_mp('foo', [], mode='w', encoder=encoder)

        assert f'{encoder} is not callable' == str(exc_info.value)

    async def test_should_write_bytes_when_giving_content_in_write_mode_without_custom_encoder(self, trio_tmp_path):
        content = {'name': 'Kevin', 'fruit': 'water melon'}
        mp_file = trio_tmp_path / 'data.mp'
        length = await write_mp(mp_file, content, mode='w')

        assert length > 0
        assert [content] == [item async for item in read_mp(mp_file)]

    async def test_should_write_bytes_when_giving_content_in_write_mode_with_custom_encoder(self, trio_tmp_path,
                                                                                            encode_datetime,
                                                                                            decode_datetime):
        content = {'name': 'Kevin', 'date': datetime.now()}
        mp_file = trio_tmp_path / 'data.mp'
        length = await write_mp(f'{mp_file}', content, mode='w', encoder=encode_datetime)

        assert length > 0
        assert [content] == [item async for item in read_mp(mp_file, decoder=decode_datetime)]

    async def test_should_write_bytes_when_giving_content_in_append_mode_without_custom_encoder(self, trio_tmp_path):
        content = ['foo', 4, {'fruit': 'water melon'}, [1, 4]]
        mp_file = trio_tmp_path / 'data.mp'

        for item in content:
            length = await write_mp(mp_file, item, mode='a')
            assert length > 0

        assert content == [item async for item in read_mp(mp_file)]

    async def test_should_write_bytes_when_giving_content_in_append_mode_with_custom_encoder(self, trio_tmp_path,
                                                                                             encode_datetime,
                                                                                             decode_datetime):
        content = ['foo', datetime.now()]
        mp_file = trio_tmp_path / 'data.mp'

        for item in content:
            length = await write_mp(f'{mp_file}', item, mode='a', encoder=encode_datetime)
            assert length > 0

        assert content == [item async for item in read_mp(mp_file, decoder=decode_datetime)]
