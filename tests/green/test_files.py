import pytest

from scalpel.green import read_jl, write_jl


class TestReadJl:
    """Tests function read_jl"""

    def test_should_return_python_objects_when_reading_file(self, tmp_path, create_msgpack_file):
        given_data = [[1, 2], 'hello', {'fruit': 'apple'}]
        jl_file = tmp_path / 'data.jl'
        create_msgpack_file(jl_file, given_data)

        for file in [jl_file, str(jl_file)]:
            assert [item for item in read_jl(file)] == given_data


class TestWriteJl:
    """Tests function write_jl"""

    @pytest.mark.parametrize('mode', ['r', 'foo', 1])
    def test_should_raise_error_when_mode_is_not_correct(self, mode):
        with pytest.raises(TypeError) as exc_info:
            write_jl('foo', data=[], mode=mode)

        assert f'The only modes expected are "a" and "w" but you provided {mode}' == str(exc_info.value)

    def test_should_write_bytes_when_giving_content_in_write_mode(self, tmp_path):
        content = {'name': 'Kevin', 'fruit': 'water melon'}
        jl_file = tmp_path / 'data.jl'
        length = write_jl(jl_file, content, mode='w')

        assert length > 0
        assert [content] == [item for item in read_jl(jl_file)]

    def test_should_write_bytes_when_giving_content_in_append_mode(self, tmp_path):
        content = ['foo', 4, {'fruit': 'water melon'}, [1, 4]]
        jl_file = tmp_path / 'data.jl'

        for item in content:
            length = write_jl(jl_file, item, mode='a')
            assert length > 0

        assert content == [item for item in read_jl(jl_file)]
