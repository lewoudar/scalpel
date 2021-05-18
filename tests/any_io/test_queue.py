import math

import anyio
import pytest
from anyio.streams.memory import MemoryObjectSendStream, MemoryObjectReceiveStream

from scalpel.any_io.queue import Queue

pytestmark = pytest.mark.anyio


# since in the __init__ method we call anyio.create_event function which tries to guess
# the async library, we must use async test functions even if we don't have async call in them
class TestQueueInitialization:

    async def test_should_work_with_default_initialization(self):
        queue = Queue()
        assert 1 == queue.maxsize
        assert 0 == queue.length
        assert [] == queue._items
        assert 0 == queue._tasks_in_progress
        assert isinstance(queue._send_channel, MemoryObjectSendStream)
        assert isinstance(queue._receive_channel, MemoryObjectReceiveStream)
        assert isinstance(queue._finished, anyio.Event)

    async def test_should_work_when_initializing_buffer_size(self):
        queue = Queue(size=3)
        assert 3 == queue.maxsize
        assert 0 == queue.length

    async def test_should_work_when_initializing_items(self):
        items = [2, 'foo']
        queue = Queue(3, items=items)
        assert 3 == queue.maxsize
        assert items == queue._items
        assert len(items) == queue.length == queue._tasks_in_progress

    async def test_length_property_works_with_infinity_size(self):
        queue = Queue(size=math.inf)
        assert 0 == queue.length
        assert queue.maxsize is math.inf

    async def test_should_work_when_initializing_with_size_and_items(self):
        items = [2, 'foo']
        queue = Queue(size=3, items=items)
        assert 3 == queue.maxsize
        assert 2 == queue.length
        assert items == queue._items

    async def test_should_raise_error_when_size_is_negative(self):
        with pytest.raises(ValueError) as exc_info:
            Queue(size=-1)

        assert 'size must not be less than 1 but you provide: -1' == str(exc_info.value)

    async def test_should_raise_error_when_size_is_less_than_items_length(self):
        with pytest.raises(anyio.WouldBlock):
            Queue(size=1, items=[2, 'foo'])


class TestPutMethods:
    """Tests methods put and put_nowait"""

    async def test_should_work_when_adding_item_with_put_method(self):
        queue = Queue(size=3)
        await queue.put(2)
        await queue.put('foo')

        assert 2 == queue.length
        assert 2 == queue._tasks_in_progress

    async def test_should_work_when_adding_item_with_put_nowait_method(self):
        queue = Queue(size=3)
        queue.put_nowait(2)

        assert 1 == queue.length
        assert 1 == queue._tasks_in_progress

    async def test_should_raise_would_block_error_when_buffer_is_full_and_put_nowait_is_used(self):
        queue = Queue()
        queue.put_nowait(1)

        with pytest.raises(anyio.WouldBlock):
            queue.put_nowait(2)

    # noinspection PyAsyncCall
    async def test_should_reset_event_when_event_is_set_and_put_method_is_called(self):
        queue = Queue()
        queue._finished.set()
        await queue.put(2)

        assert not queue._finished.is_set()

    # noinspection PyAsyncCall
    async def test_should_reset_event_when_event_is_set_and_put_nowait_is_called(self):
        queue = Queue()
        queue._finished.set()
        queue.put_nowait(2)

        assert not queue._finished.is_set()


class TestGetMethods:
    """Tests methods get and get_nowait"""

    async def test_should_work_when_using_get_method(self):
        queue = Queue(3, items=[2, 'foo'])

        assert 2 == await queue.get()
        assert 'foo' == await queue.get()

    async def test_should_work_when_using_get_nowait_method(self):
        queue = Queue(3, items=[2, 'foo'])

        assert 2 == queue.get_nowait()
        assert 'foo' == queue.get_nowait()

    async def test_should_raise_would_block_error_when_using_get_nowait_on_empty_buffer(self):
        queue = Queue()

        with pytest.raises(anyio.WouldBlock):
            queue.get_nowait()


class TestCloseMethod:
    """Tests method close"""

    async def test_should_work_when_calling_close_method(self):
        queue = Queue()
        await queue.close()

        with pytest.raises(anyio.ClosedResourceError):
            await queue.put(2)

        with pytest.raises(anyio.ClosedResourceError):
            await queue.get()

    async def test_should_work_when_using_context_manager(self):
        async with Queue(size=1) as queue:
            queue.put_nowait(2)

        with pytest.raises(anyio.ClosedResourceError):
            queue.put_nowait(3)

        with pytest.raises(anyio.ClosedResourceError):
            queue.get_nowait()


class TestTaskDoneAndJoinMethods:
    """Tests methods task_done and join"""

    async def test_should_raise_error_when_task_done_is_called_without_adding_items_in_queue(self):
        async with Queue(size=1) as queue:
            with pytest.raises(ValueError) as exc_info:
                queue.task_done()

            assert 'task_done method was calling too many times without adding items in queue' == str(exc_info.value)

    async def test_should_work_when_using_task_done_and_join_methods(self):
        async with Queue(size=1) as queue:
            await queue.put(2)
            await queue.get()
            assert 1 == queue._tasks_in_progress

            with anyio.move_on_after(1) as cancel_scope:
                await queue.join()

            assert cancel_scope.cancel_called
            queue.task_done()
            assert 0 == queue._tasks_in_progress

            with anyio.move_on_after(1) as cancel_scope:
                await queue.join()

            assert not cancel_scope.cancel_called
