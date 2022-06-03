import io
from io import BytesIO, StringIO
from unittest.mock import call

import pytest

# noinspection PyProtectedMember
from scalpel.green.utils.io import AsyncFile, _has, open_file, wrap_file


# noinspection PyMethodMayBeStatic
class DummyIO:
    """A file-like class to help in tests"""

    writelines_called = False
    flush_called = False
    close_called = False

    @property
    def isatty(self):
        return False

    def read(self, size=-1):
        return 'hello'

    def read1(self, size=-1):
        return 'hello'

    def readline(self, size=-1):
        return 'hello\n'

    def readlines(self, hint=-1):
        return ['hello\n', 'world\n']

    def readinto(self, b):
        return len(b)

    def readinto1(self, b):
        return len(b)

    def seek(self, offset, whence=0):
        return offset - whence

    def tell(self):
        return 2

    def write(self, s):
        return len(s)

    def writelines(self, lines):
        self.writelines_called = True

    def truncate(self, size=None):
        return size

    def peek(self, size=None):
        return b'hello'

    def flush(self):
        self.flush_called = True

    def close(self):
        self.close_called = True


# noinspection PyTypeChecker
class TestAsyncFile:
    """Tests class AsyncFile"""

    _io = DummyIO()

    @pytest.mark.parametrize(
        ('method', 'args'),
        [
            ('read', (2,)),
            ('read1', (2,)),
            ('readline', (2,)),
            ('readlines', (2,)),
            ('readinto', (bytearray(10),)),
            ('readinto1', (bytearray(10),)),
            ('seek', (0, 0)),
            ('tell', ()),
            ('write', ('hello',)),
            ('writelines', ([],)),
            ('truncate', (None,)),
            ('peek', (None,)),
            ('flush', ()),
            ('close', ()),
        ],
    )
    def test_should_call_underlying_io_methods_wrapped_in_threadpool(self, mocker, method, args):
        mocker.patch('scalpel.green.utils.io.get_hub')
        async_file = AsyncFile(self._io)
        getattr(async_file, method)(*args)

        async_file._pool.spawn.assert_called_once_with(getattr(self._io, method), *args)

    @pytest.mark.parametrize(
        ('method', 'args', 'result'),
        [
            ('read', (), 'hello'),
            ('read1', (), 'hello'),
            ('readline', (), 'hello\n'),
            ('readinto', (bytearray(10),), 10),
            ('readinto1', (bytearray(10),), 10),
            ('seek', (6, 0), 6),
            ('tell', (), 2),
            ('write', ('hello',), 5),
            ('truncate', (10,), 10),
            ('peek', (5,), b'hello'),
        ],
    )
    def test_should_return_io_method_value_when_appropriate(self, method, args, result):
        async_file = AsyncFile(self._io)
        assert result == getattr(async_file, method)(*args)

    @pytest.mark.parametrize(
        ('method', 'args', 'flag'),
        [
            ('writelines', ['hello\n'], 'writelines_called'),
            ('flush', (), 'flush_called'),
            ('close', (), 'close_called'),
        ],
    )
    def test_should_call_correctly_io_methods(self, method, args, flag):
        async_file = AsyncFile(self._io)
        getattr(async_file, method)(*args)

        assert getattr(async_file, flag)

    def test_context_manager_works(self):
        with AsyncFile(self._io) as async_file:
            assert isinstance(async_file, AsyncFile)

        assert async_file.close_called

    def test_iter_method_is_implemented(self, mocker):
        mocker.patch('scalpel.green.utils.io.AsyncFile.readline', return_value='')
        async_file = AsyncFile(self._io)

        assert [] == [line for line in async_file]

    def test_should_return_custom_io_property_not_defined_in_async_file_class(self):
        async_file = AsyncFile(self._io)
        assert not async_file.isatty

    def test_should_raise_error_when_io_attribute_does_not_exist(self):
        async_file = AsyncFile(self._io)

        with pytest.raises(AttributeError):
            getattr(async_file, 'foo')


# noinspection PyTypeChecker
class TestHas:
    """Tests function _has"""

    @pytest.mark.parametrize('attribute', ['close', 'read'])
    def test_should_return_false_if_attribute_is_not_found(self, attribute):
        class Foo:
            pass

        assert not _has(Foo(), attribute)

    @pytest.mark.parametrize('attribute', ['close', 'read'])
    def test_should_return_false_when_attribute_is_not_callable(self, attribute):
        class Foo:
            pass

        f = Foo()
        setattr(f, attribute, 1)

        assert not _has(f, attribute)

    @pytest.mark.parametrize('attribute', ['close', 'read'])
    def test_should_return_true_when_attribute_exists_and_is_callable(self, attribute):
        assert _has(DummyIO(), attribute)


# noinspection PyTypeChecker
class TestWrapFile:
    """Tests function wrap_file"""

    def test_should_raise_error_when_close_method_is_not_implemented(self):
        class Foo:
            pass

        f = Foo()
        with pytest.raises(TypeError) as exc_info:
            wrap_file(f)

        assert f'{f} does not implement close method which is' f' mandatory for a file-like object' == str(
            exc_info.value
        )

    def test_should_raise_error_if_read_or_write_is_not_implemented(self):
        class Foo:
            def close(self):
                pass

        f = Foo()
        with pytest.raises(TypeError) as exc_info:
            wrap_file(f)

        assert f'{f} does not implement read or write method' f' which is mandatory for a file-like object' == str(
            exc_info.value
        )

    def test_should_return_async_file_when_giving_object_with_correct_interface(self):
        async_file = wrap_file(DummyIO())
        assert isinstance(async_file, AsyncFile)

    def test_bytes_io_object_correctly_works_after_being_wrapped(self):
        b = BytesIO()
        async_b = wrap_file(b)

        assert 5 == async_b.write(b'hello')
        assert b'hello' == async_b.getvalue()
        async_b.close()
        assert async_b.closed

    def test_string_io_object_correctly_works_after_being_wrapped(self):
        s = StringIO()
        async_s = wrap_file(s)

        assert 5 == async_s.write('hello')
        assert 'hello' == async_s.getvalue()
        async_s.close()
        assert async_s.closed


class TestOpenFile:
    """Tests function open_file"""

    def test_should_call_appropriate_function_and_method(self, mocker):
        hub_mock = mocker.patch('scalpel.green.utils.io.get_hub')
        wrap_file_mock = mocker.patch('scalpel.green.utils.io.wrap_file')
        dummy_io = DummyIO()
        open_file(dummy_io)

        hub_mock.assert_called()
        assert call().threadpool.spawn(io.open, dummy_io, 'r', -1, None, None, None, True, None) in hub_mock.mock_calls
        wrap_file_mock.assert_called_once()

    def test_open_file_works_as_expected(self, tmp_path):
        dummy_file = tmp_path / 'dummy.txt'
        dummy_file.touch()

        input_data = ['Hello\n', 'world\n', 'kevin\n']
        with open_file(dummy_file, 'w') as f:
            f.writelines(input_data)

        assert f.closed

        result = []
        with open_file(dummy_file) as f:
            for line in f:
                result.append(line)

        assert f.closed
        assert input_data == result
