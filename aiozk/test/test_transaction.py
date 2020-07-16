import pytest
from aiozk.transaction import Transaction


@pytest.mark.asyncio
async def test_transaction(zk, path):
    t = Transaction(zk)
    t.create(path)
    t.set_data(path, b'test_data')
    t.delete(path)
    res = await t.commit()
    assert bool(res)


@pytest.mark.asyncio
async def test_fail_transaction(zk, path):
    t = Transaction(zk)
    t.create(path)
    t.check_version(path, 1)
    t.check_version(path, 0)
    res = await t.commit()
    assert not bool(res)
