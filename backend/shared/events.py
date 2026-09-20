import asyncio

# In-memory SSE queues, one per user_id. Last connection wins if a user opens
# multiple tabs. Not shared across processes.
queues: dict[int, asyncio.Queue] = {}


def register_queue(user_id, queue):
    queues[user_id] = queue


def deregister_queue(user_id):
    queues.pop(user_id, None)


async def push_event(user_id, event):
    queue = queues.get(user_id)
    if queue is not None:
        await queue.put(event)
