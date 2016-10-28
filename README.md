# Asyncio zookeeper client

[![Build Status](https://travis-ci.org/tipsi/aiozk.svg?branch=master)](https://travis-ci.org/tipsi/aiozk)

**Based on [wglass/zoonado](https://github.com/wglass/zoonado/tree/master/zoonado) implementation**

## Status

Have no major bugs in client/session/connection, but recipes are just ported and require more tests. 
So you can expect that recipes with tests are working.

## Installation

```bash
$ pip install aiozk
```


## Quick Example

```python
import asyncio
from aiozk import ZKClient


async def run():
    zk = ZKClient('localhost')
    await zk.start()
    await zk.create('/foo', data=b'bazz', ephemeral=True)
    await zk.set_data('/foo', 'new bazz')
    await zk.close()

loop = asyncio.get_event_loop()
loop.run_until_complete(run())
```

## Recipes

You may use recipes, similar to zoonado, kazoo and other libs:

```python
# assuming zk is aiozk.ZKClient

barrier = zk.recipes.Barrier('/barrier_name')
await barrier.create()
await barrier.lift()
await barrier.wait()
```

[Full list of recipes](https://github.com/tipsi/aiozk/tree/master/aiozk/recipes)

To understand ideas behind recipes [please read this](https://zookeeper.apache.org/doc/trunk/recipes.html) and [even more recipes here](http://curator.apache.org/curator-recipes/index.html). Make sure you're familiar with all recipes before do something new by youself, exceptionally when it involves more than few basic zookeeper calls.

## Testing approach

Most of tests are integration tests and running on real zookeeper instances.
We've chosen `zookeeper 3.5` version, since it has ability to dynamic reconfiguration and we're going to do all connecting/reconnecting/watches tests on zk docker cluster as this gives us ability to restart any server and see what happens.
