import pytest

from aiozk.recipes.sequential import SequentialRecipe
from aiozk.exc import TimeoutError, NodeExists


@pytest.mark.asyncio
async def test_wait_on_not_exist_sibling(zk, path):
    seq_recipe = SequentialRecipe(path)
    seq_recipe.set_client(zk)
    # NO WAIT
    await seq_recipe.wait_on_sibling('not-exist-znode', timeout=0.5)


@pytest.mark.asyncio
async def test_wait_on_exist_sibling(zk, path):
    seq_recipe = SequentialRecipe(path)
    seq_recipe.set_client(zk)

    LABEL = 'test'
    await seq_recipe.create_unique_znode(LABEL)

    try:
        owned_positions, siblings = await seq_recipe.analyze_siblings()
        with pytest.raises(TimeoutError):
            # SHOULD WAIT
            await seq_recipe.wait_on_sibling(siblings[0], timeout=0.5)
    finally:
        await seq_recipe.delete_unique_znode(LABEL)
        await zk.delete(path)


@pytest.mark.asyncio
async def test_delete_not_exist_unique_znode(zk, path):
    seq_recipe = SequentialRecipe(path)
    seq_recipe.set_client(zk)

    with pytest.raises(KeyError):
        # RAISE EXCEPTION
        await seq_recipe.delete_unique_znode('test')

    await seq_recipe.create_unique_znode('test')

    await zk.delete(seq_recipe.owned_paths['test'])

    try:
        # OK
        await seq_recipe.delete_unique_znode('test')
    finally:
        await zk.delete(path)


@pytest.mark.asyncio
async def test_create_unique_znode_twice(zk, path):
    seq_recipe = SequentialRecipe(path)
    seq_recipe.set_client(zk)

    await seq_recipe.create_unique_znode('test')
    try:
        with pytest.raises(NodeExists):
            await seq_recipe.create_unique_znode('test')
        siblings = await seq_recipe.get_siblings()
        assert len(siblings) == 1
    finally:
        await seq_recipe.delete_unique_znode('test')
        await zk.delete(path)


@pytest.mark.asyncio
async def test_get_siblings_relative_path(zk, path):
    seq_recipe = SequentialRecipe(path)
    seq_recipe.set_client(zk)

    await seq_recipe.create_unique_znode('test')
    try:
        siblings = await seq_recipe.get_siblings()
        assert siblings[0].startswith('test')
    finally:
        await seq_recipe.delete_unique_znode('test')
        await zk.delete(path)


@pytest.mark.asyncio
async def test_prohibited_slash_in_label(zk, path):
    seq_recipe = SequentialRecipe(path)
    seq_recipe.set_client(zk)

    with pytest.raises(ValueError):
        await seq_recipe.create_unique_znode('test/test')
