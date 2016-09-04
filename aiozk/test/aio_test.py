import asyncio
from types import CoroutineType
from unittest import TestCase
from unittest.case import _Outcome


class AIOMask(type):
    def wrap_func(func):
        def ret(*args, **kwargs):
            def inner():
                return func(*args, **kwargs)
            return inner
        return ret

    def __new__(cls, name, bases, dct):
        for k, v in dct.items():
            if k.startswith('test'):
                dct[k] = cls.wrap_func(v)
        return super().__new__(cls, name, bases, dct)


class AIOTestCase(TestCase, metaclass=AIOMask):
    def run(self, result=None):
        out = self.inner_run(result)
        f = asyncio.ensure_future(out)
        asyncio.get_event_loop().run_until_complete(f)
        return f.result()

    async def inner_run(self, result=None):
        orig_result = result
        if result is None:
            result = self.defaultTestResult()
            startTestRun = getattr(result, 'startTestRun', None)
            if startTestRun is not None:
                startTestRun()

        result.startTest(self)

        testMethod = getattr(self, self._testMethodName)
        if (getattr(self.__class__, "__unittest_skip__", False) or
           getattr(testMethod, "__unittest_skip__", False)):
            # If the class or method was skipped.
            try:
                skip_why = (getattr(self.__class__, '__unittest_skip_why__', '')
                            or getattr(testMethod, '__unittest_skip_why__', ''))
                self._addSkip(result, self, skip_why)
            finally:
                result.stopTest(self)
            return
        expecting_failure_method = getattr(testMethod,
                                           "__unittest_expecting_failure__", False)
        expecting_failure_class = getattr(self,
                                          "__unittest_expecting_failure__", False)
        expecting_failure = expecting_failure_class or expecting_failure_method
        outcome = _Outcome(result)
        try:
            self._outcome = outcome

            with outcome.testPartExecutor(self):
                o = self.setUp()
                if isinstance(o, CoroutineType):
                    await o
            if outcome.success:
                outcome.expecting_failure = expecting_failure
                with outcome.testPartExecutor(self, isTest=True):
                    # wrapped into function to prevent generator check return true
                    o = testMethod()()
                    if isinstance(o, CoroutineType):
                        await o
                outcome.expecting_failure = False
                with outcome.testPartExecutor(self):
                    o = self.tearDown()
                    if isinstance(o, CoroutineType):
                        await o

            self.doCleanups()
            for test, reason in outcome.skipped:
                self._addSkip(result, test, reason)
            self._feedErrorsToResult(result, outcome.errors)
            if outcome.success:
                if expecting_failure:
                    if outcome.expectedFailure:
                        self._addExpectedFailure(result, outcome.expectedFailure)
                    else:
                        self._addUnexpectedSuccess(result)
                else:
                    result.addSuccess(self)
            return result
        finally:
            result.stopTest(self)
            if orig_result is None:
                stopTestRun = getattr(result, 'stopTestRun', None)
                if stopTestRun is not None:
                    stopTestRun()

            # explicitly break reference cycles:
            # outcome.errors -> frame -> outcome -> outcome.errors
            # outcome.expectedFailure -> frame -> outcome -> outcome.expectedFailure
            outcome.errors.clear()
            outcome.expectedFailure = None

            # clear the outcome, no more needed
            self._outcome = None
