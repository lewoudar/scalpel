import math

import pytest
import trio

from scalpel.trionic.utils.queue import Queue


class TestQueueInitialization:

    def test_should_work_with_default_initialization(self):
        queue = Queue()
        assert 0 == queue._size == queue.length
        assert [] == queue._items
        assert 0 == queue._tasks_in_progress
        assert isinstance(queue._send_channel, trio.MemorySendChannel)
        assert isinstance(queue._receive_channel, trio.MemoryReceiveChannel)

    def test_should_work_when_initializing_buffer_size(self):
        queue = Queue(size=3)
        assert 3 == queue._size
        assert 0 == queue.length

    def test_should_work_when_initializing_items(self):
        items = [2, 'foo']
        queue = Queue(items=items)
        assert 0 == queue._size
        assert items == queue._items
        assert len(items) == queue.length

    def test_length_property_works_with_infinity_size(self):
        queue = Queue(size=math.inf)
        assert 0 == queue.length
        assert queue._size is math.inf

    def test_should_work_when_initializing_with_size_and_items(self):
        items = [2, 'foo']
        queue = Queue(size=3, items=items)
        assert 3 == queue._size
        assert 2 == queue.length
        assert items == queue._items

    def test_should_raise_error_when_size_is_negative(self):
        with pytest.raises(ValueError) as exc_info:
            Queue(size=-1)

        assert 'size must not be less than 0 but you provide: -1' == str(exc_info.value)

    def test_should_raise_error_when_size_is_less_than_items_length(self):
        with pytest.raises(trio.WouldBlock):
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

        with pytest.raises(trio.WouldBlock):
            queue.put_nowait(2)


class TestGetMethods:
    """Tests methods get and get_nowait"""

    async def test_should_work_when_using_get_method(self):
        queue = Queue(items=[2, 'foo'])

        assert 2 == await queue.get()
        assert 'foo' == await queue.get()

    async def test_should_work_when_using_get_nowait_method(self):
        queue = Queue(items=[2, 'foo'])

        assert 2 == queue.get_nowait()
        assert 'foo' == queue.get_nowait()

    async def test_should_raise_would_block_error_when_using_get_nowait_on_empty_buffer(self):
        queue = Queue()

        with pytest.raises(trio.WouldBlock):
            queue.get_nowait()


class TestCloseMethod:
    """Tests method close"""

    async def test_should_work_when_calling_close_method(self):
        queue = Queue()
        await queue.close()

        with pytest.raises(trio.ClosedResourceError):
            await queue.put(2)

        with pytest.raises(trio.ClosedResourceError):
            await queue.get()

    async def test_should_work_when_using_context_manager(self):
        async with Queue(size=1) as queue:
            queue.put_nowait(2)

        with pytest.raises(trio.ClosedResourceError):
            queue.put_nowait(3)

        with pytest.raises(trio.ClosedResourceError):
            queue.get_nowait()


class TestTaskDoneAndJoinMethods:
    """Tests methods task_done and join"""

    async def test_should_work_when_using_task_done_and_join_methods(self):
        async with Queue(size=1) as queue:
            await queue.put(2)
            await queue.get()
            assert 1 == queue._tasks_in_progress

            with trio.move_on_after(1) as cancel_scope:
                await queue.join()

            assert cancel_scope.cancelled_caught
            queue.task_done()
            assert 0 == queue._tasks_in_progress

            with trio.move_on_after(1) as cancel_scope:
                await queue.join()

            assert not cancel_scope.cancelled_caught
