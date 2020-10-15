"""Implementation of a trio queue"""
import logging
from typing import Union, List, Any

import attr
import trio

logger = logging.getLogger('scalpel')


@attr.s
class Queue:
    """
    An implementation of a trio queue with the capacity to tell of a task is done.

    **Parameters:**

    * **size:** The size of the queue, defaults to 1 (this is the minimum value).
    * **items:** A list of values used to initialize the queue.

    **N.B:** If you set `items`, be sure that the size of the queue is greater than `items` length, otherwise you will
    have a `trio.WouldBlock` exception.

    Usage:

    ```
    import math
    import random

    import trio
    from scalpel.trionic import Queue

    async def worker(name: str, queue: Queue) -> None:
        while True:
            # Get a "work item" out of the queue.
            time_to_sleep = await queue.get()

            await trio.sleep(time_to_sleep)
            # Notify the queue that the "work item" has been processed.
            queue.task_done()
            print(f'{name} has slept for {time_to_sleep:.2f} seconds')


    async def main():
        async with Queue(math.inf) as queue:
            # Generate random timings and put them into the queue.
            total_sleep_time = 0
            for _ in range(20):
                sleep_for = random.uniform(0.05, 1.0)
                total_sleep_time += sleep_for
                queue.put_nowait(sleep_for)

            # Create three worker tasks to process the queue concurrently.
            async with trio.open_nursery() as nursery:
                for i in range(3):
                    nursery.start_soon(worker, f'worker-{i}', queue)

                # Wait until the queue is fully processed.
                before = trio.current_time()
                await queue.join()
                total_slept_for = trio.current_time() - before
                print('====')
                print(f'3 workers slept in parallel for {total_slept_for:.2f} seconds')
                print(f'total expected sleep time: {total_sleep_time:.2f} seconds')

                # We can end the nursery which will in turn end the tasks.
                nursery.cancel_scope.cancel()


    trio.run(main)
    ```
    """
    _size: Union[int, float] = attr.ib(default=1, validator=attr.validators.instance_of((int, float)))
    _items: List[Any] = attr.ib(factory=list, validator=attr.validators.instance_of((list, set, tuple)))
    _send_channel: trio.MemorySendChannel = attr.ib(init=False)
    _receive_channel: trio.MemoryReceiveChannel = attr.ib(init=False)
    _tasks_in_progress: int = attr.ib(default=0, init=False)
    _finished: trio.Event = attr.ib(factory=trio.Event, init=False)

    def __attrs_post_init__(self):
        logger.debug('initializing queue send and receive channels with a size of %s', self._size)
        self._send_channel, self._receive_channel = trio.open_memory_channel(self._size)
        if self._items:
            logger.debug('trying to add items coming from list %s', self._items)
            for item in self._items:
                self._tasks_in_progress += 1
                self._send_channel.send_nowait(item)

    @_size.validator
    def _validate_size(self, _, value: int) -> None:
        if value < 1:
            message = f'size must not be less than 1 but you provide: {value}'
            logger.error(message)
            raise ValueError(message)

    @property
    def length(self) -> int:
        """Tne number of items currently present in the queue."""
        value = self._send_channel.statistics().current_buffer_used
        logger.debug('returning queue length: %s', value)
        return value

    @property
    def maxsize(self) -> Union[int, float]:
        """The number of items allowed in the queue."""
        logger.debug('returning queue max size: %s', self._size)
        return self._size

    async def put(self, item: Any) -> None:
        logger.debug('adding item %s to queue', item)
        await self._send_channel.send(item)
        self._tasks_in_progress += 1
        logger.debug('number of tasks in progress is now: %s', self._tasks_in_progress)
        if self._finished.is_set():
            self._finished = trio.Event()

    def put_nowait(self, item: Any) -> None:
        logger.debug('trying to add %s to queue', item)
        self._send_channel.send_nowait(item)
        self._tasks_in_progress += 1
        logger.debug('number of tasks in progress is now: %s', self._tasks_in_progress)
        if self._finished.is_set():
            self._finished = trio.Event()

    async def get(self) -> Any:
        item = await self._receive_channel.receive()
        logger.debug('returning item %s from queue', item)
        return item

    def get_nowait(self) -> Any:
        logger.debug('trying to get item from queue')
        return self._receive_channel.receive_nowait()

    def task_done(self) -> None:
        if self._tasks_in_progress <= 0:
            raise ValueError('task_done method was calling too many times without adding items in queue')
        self._tasks_in_progress -= 1
        logger.debug('decrementing tasks in progress, now the new value is: %s', self._tasks_in_progress)
        if self._tasks_in_progress == 0:
            self._finished.set()

    async def close(self) -> None:
        logger.debug('closing send and receive channels')
        await self._send_channel.aclose()
        await self._receive_channel.aclose()

    async def join(self) -> None:
        logger.debug('waiting self._tasks_in_progress to be equal to 0')
        await self._finished.wait()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
