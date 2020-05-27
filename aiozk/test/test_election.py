import asyncio
import pytest

from .. import exc


@pytest.mark.asyncio
async def test_election_volunteer(zk, path):
    elec = zk.recipes.LeaderElection(path)
    # NO WAIT
    await asyncio.wait_for(elec.volunteer(), timeout=0.5)
    elec2 = zk.recipes.LeaderElection(path)
    # NO WAIT
    await asyncio.wait_for(elec2.volunteer(), timeout=0.5)

    await elec2.resign()
    await elec.resign()

    assert not elec.has_leadership
    assert not elec2.has_leadership

    await zk.delete(path)


@pytest.mark.asyncio
async def test_election_wait_for_leadership(zk, path):
    elec = zk.recipes.LeaderElection(path)
    await elec.volunteer()

    # NO WAIT
    await asyncio.wait_for(elec.wait_for_leadership(), timeout=0.5)

    assert elec.has_leadership

    await elec.resign()

    assert not elec.has_leadership

    await zk.delete(path)


@pytest.mark.asyncio
async def test_election_succession(zk, path):
    elec = zk.recipes.LeaderElection(path)
    await elec.volunteer()
    await elec.wait_for_leadership()

    assert elec.has_leadership

    elec2 = zk.recipes.LeaderElection(path)
    await elec2.volunteer()
    with pytest.raises(exc.TimeoutError):
        await elec2.wait_for_leadership(timeout=0.5)

    assert not elec2.has_leadership

    await elec.resign()

    assert not elec.has_leadership

    await elec2.wait_for_leadership(timeout=0.5)

    assert elec2.has_leadership

    await elec2.resign()
    await zk.delete(path)


@pytest.mark.asyncio
async def test_election_retry_wait_for_leadership(zk, path):
    elec = zk.recipes.LeaderElection(path)
    await elec.volunteer()
    await elec.wait_for_leadership()

    assert elec.has_leadership

    elec2 = zk.recipes.LeaderElection(path)
    await elec2.volunteer()

    with pytest.raises(exc.TimeoutError):
        await elec2.wait_for_leadership(timeout=0.2)

    assert not elec2.has_leadership

    with pytest.raises(exc.TimeoutError):
        await elec2.wait_for_leadership(timeout=0.2)

    assert not elec2.has_leadership

    with pytest.raises(exc.TimeoutError):
        await elec2.wait_for_leadership(timeout=0.2)

    assert not elec2.has_leadership

    with pytest.raises(exc.TimeoutError):
        await elec2.wait_for_leadership(timeout=0.2)

    assert not elec2.has_leadership

    await elec.resign()
    await elec2.resign()

    await zk.delete(path)


@pytest.mark.asyncio
async def test_election_early_wait_for_leadership(zk, path):
    elec = zk.recipes.LeaderElection(path)

    early_wait_success = asyncio.Event()

    async def wait_early():
        await elec.wait_for_leadership()
        assert elec.has_leadership
        early_wait_success.set()

    asyncio.create_task(wait_early())
    await asyncio.sleep(0.5)
    assert not elec.has_leadership

    await elec.volunteer()

    # NO WAIT
    await asyncio.wait_for(early_wait_success.wait(), timeout=0.5)

    await elec.resign()

    assert not elec.has_leadership

    await zk.delete(path)


@pytest.mark.asyncio
async def test_election_many_candidates(zk, path):
    NUM = 10
    leaders = 0
    count = 0

    async def start_candidate():
        nonlocal leaders, count

        elec = zk.recipes.LeaderElection(path)
        await elec.volunteer()
        await elec.wait_for_leadership()
        count += 1
        leaders += 1
        assert leaders == 1
        await asyncio.sleep(0.1)
        leaders -= 1
        await elec.resign()

    aws = []
    for _ in range(NUM):
        aws.append(start_candidate())

    await asyncio.wait_for(asyncio.gather(*aws), timeout=2)

    assert NUM == count
    assert leaders == 0

    await zk.delete(path)


@pytest.mark.asyncio
async def test_election_many_wait_for_leadership(zk, path):
    NUM = 10
    elec = zk.recipes.LeaderElection(path)

    await elec.volunteer()

    for _ in range(NUM):
        # NO WAIT
        await asyncio.wait_for(elec.wait_for_leadership(), timeout=0.5)
        assert elec.has_leadership

    await elec.resign()
    await zk.delete(path)


@pytest.mark.asyncio
async def test_election_duplicate_volunteer(zk, path):
    elec = zk.recipes.LeaderElection(path)
    await elec.volunteer()

    with pytest.raises(exc.NodeExists):
        await elec.volunteer()

    # NO WAIT
    await asyncio.wait_for(elec.wait_for_leadership(), timeout=0.5)
    assert elec.has_leadership

    await elec.resign()
    assert not elec.has_leadership

    await zk.delete(path)
