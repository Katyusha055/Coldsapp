import asyncio

import pytest

import backend.shared.events as events


def test_register_queue_stores_queue_for_user():
    queue = asyncio.Queue()
    events.register_queue(7, queue)
    try:
        assert events.queues[7] is queue
    finally:
        events.deregister_queue(7)


def test_deregister_queue_removes_user_without_raising_when_absent():
    events.deregister_queue(999)  # never registered
    assert 999 not in events.queues


@pytest.mark.asyncio
async def test_push_event_puts_event_on_registered_users_queue():
    queue = asyncio.Queue()
    events.register_queue(7, queue)
    try:
        await events.push_event(7, {"type": "test"})
        assert queue.get_nowait() == {"type": "test"}
    finally:
        events.deregister_queue(7)


@pytest.mark.asyncio
async def test_push_event_is_a_noop_for_unregistered_user():
    await events.push_event(12345, {"type": "test"})  # should not raise
