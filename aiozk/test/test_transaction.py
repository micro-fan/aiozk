import pytest
from aiozk.transaction import Transaction, TransactionFailed


pytestmark = pytest.mark.asyncio


async def test_transaction(zk, path):
    t = Transaction(zk)
    t.create(path)
    t.set_data(path, b'test_data')
    t.delete(path)
    res = await t.commit()
    assert bool(res)


async def test_fail_transaction(zk, path):
    t = Transaction(zk)
    t.create(path)
    t.check_version(path, 1)
    t.check_version(path, 0)
    res = await t.commit()
    assert not bool(res)


async def test_transaction_contextmanager(zk, path):
    async with Transaction(zk) as t:
        t.create(path)
    assert await zk.exists(path)
    await zk.delete(path)


async def test_transaction_contextmanager_fail(zk, path):
    with pytest.raises(TransactionFailed):
        async with Transaction(zk) as t:
            t.create(path)
            t.check_version(path, 1)
    assert not await zk.exists(path)


async def test_exception_handling(zk, path):
    with pytest.raises(ValueError):
        async with Transaction(zk) as t:
            t.create(path)
            raise ValueError('aaaa')
    assert not await zk.exists(path)
