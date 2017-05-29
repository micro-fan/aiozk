import asyncio
import collections
import logging
import time

# from tornado import gen

from aiozk import exc


log = logging.getLogger(__name__)


class RetryPolicy(object):

    def __init__(self, try_limit, sleep_func):
        self.try_limit = try_limit
        self.sleep_func = sleep_func

        self.timings = collections.defaultdict(list)

    async def enforce(self, request=None, loop=None):
        self.timings[id(request)].append(time.time())

        tries = len(self.timings[id(request)])
        if tries == 1:
            return

        if self.try_limit is not None and tries >= self.try_limit:
            raise exc.FailedRetry

        wait_time = self.sleep_func(self.timings[id(request)])
        if wait_time is None or wait_time == 0:
            return
        elif wait_time < 0:
            raise exc.FailedRetry

        log.debug("Waiting %d seconds until next try.", wait_time)
        loop = loop or asyncio.get_event_loop()
        await asyncio.sleep(wait_time, loop=loop)

    def clear(self, request):
        self.timings.pop(id(request), None)

    @classmethod
    def once(cls):
        return cls.n_times(1)

    @classmethod
    def n_times(cls, n):

        def never_wait(_):
            return None

        return cls(try_limit=n, sleep_func=never_wait)

    @classmethod
    def forever(cls):

        def never_wait(_):
            return None

        return cls(try_limit=None, sleep_func=never_wait)

    @classmethod
    def exponential_backoff(cls, base=2, maximum=None):

        def exponential(timings):
            wait_time = base ** len(timings)
            if maximum is not None:
                wait_time = min(maximum, wait_time)

            return wait_time

        return cls(try_limit=None, sleep_func=exponential)

    @classmethod
    def until_elapsed(cls, timeout):

        def elapsed_time(timings):
            if timings:
                first_timing = timings[0]
            else:
                first_timing = time.time()

            return (first_timing + timeout) - time.time()

        return cls(try_limit=None, sleep_func=elapsed_time)
