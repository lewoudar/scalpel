"""Implementation of a trio queue"""
import logging
from typing import Union, List, Any

import attr
import trio

logger = logging.getLogger('scalpel')


@attr.s
class Queue:
    _size: Union[int, float] = attr.ib(default=0, validator=attr.validators.instance_of((int, float)))
    _items: List[Any] = attr.ib(factory=list, validator=attr.validators.instance_of((list, set, tuple)))
    _send_channel: trio.MemorySendChannel = attr.ib(init=False)
    _receive_channel: trio.MemoryReceiveChannel = attr.ib(init=False)
    _tasks_in_progress: int = attr.ib(default=0, init=False)
    _finished: trio.Event = attr.ib(factory=trio.Event, init=False)

    def __attrs_post_init__(self):
        if self._size or (not self._size and not self._items):
            logger.debug('initializing queue send and receive channels with a size of %s', self._size)
            self._send_channel, self._receive_channel = trio.open_memory_channel(self._size)
        if self._items:
            if not self._size:
                items_length = len(self._items)
                logger.debug(
                    'initializing queue send and receive channels with self._items size of %s', items_length
                )
                self._send_channel, self._receive_channel = trio.open_memory_channel(items_length)
            logger.debug('trying to add items coming from list %s', self._items)
            for item in self._items:
                self._tasks_in_progress += 1
                self._send_channel.send_nowait(item)

    @_size.validator
    def _validate_size(self, _, value: int) -> None:
        if value < 0:
            message = f'size must not be less than 0 but you provide: {value}'
            logger.error(message)
            raise ValueError(message)

    @property
    def length(self) -> Union[int, float]:
        value = self._send_channel.statistics().current_buffer_used
        logger.debug('returning queue length: %s', value)
        return value

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
