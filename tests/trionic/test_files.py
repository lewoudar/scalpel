import pytest
import trio

from scalpel.trionic import read_jl, write_jl


class TestReadJl:
    """Tests function read_mp"""

    async def test_should_return_python_objects_when_reading_file(self, tmp_path, create_msgpack_file):
        given_data = [[1, 2], 'hello', {'fruit': 'apple'}]
        jl_file = tmp_path / 'data.jl'
        create_msgpack_file(jl_file, given_data)

        for file in [str(jl_file), trio.Path(jl_file)]:
            assert [item async for item in read_jl(file)] == given_data


class TestWriteJl:
    """Tests function write_mp"""

    @pytest.mark.parametrize('mode', ['r', 'foo', 4])
    async def test_should_raise_error_when_mode_is_not_correct(self, mode):
        with pytest.raises(TypeError) as exc_info:
            await write_jl('foo', [], mode=mode)

        assert f'The only modes expected are "a" and "w" but you provided {mode}' == str(exc_info.value)

    async def test_should_write_bytes_when_giving_content_in_write_mode(self, trio_tmp_path):
        content = {'name': 'Kevin', 'fruit': 'water melon'}
        jl_file = trio_tmp_path / 'data.jl'
        length = await write_jl(jl_file, content, mode='w')

        assert length > 0
        assert [content] == [item async for item in read_jl(jl_file)]

    async def test_should_write_bytes_when_giving_content_in_append_mode(self, trio_tmp_path):
        content = ['foo', 4, {'fruit': 'water melon'}, [1, 4]]
        jl_file = trio_tmp_path / 'data.jl'

        for item in content:
            length = await write_jl(jl_file, item, mode='a')
            assert length > 0

        assert content == [item async for item in read_jl(jl_file)]
