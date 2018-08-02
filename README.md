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

You may use recipes, similar to zoonado, kazoo, and other libs:

```python
# assuming zk is aiozk.ZKClient

barrier = zk.recipes.Barrier('/barrier_name')
await barrier.create()
await barrier.lift()
await barrier.wait()
```

[Full list of recipes](https://github.com/tipsi/aiozk/tree/master/aiozk/recipes)

To understand ideas behind recipes [please read this](https://zookeeper.apache.org/doc/trunk/recipes.html) and [even more recipes here](http://curator.apache.org/curator-recipes/index.html). Make sure you're familiar with all recipes before doing something new by yourself, especially when it involves more than few zookeeper calls.


## Testing

**NB**: please ensure that you're using recent `docker-compose` version. You can get it by running

```
pip install --user -U docker-compose
```


### Run tests

```
# you should have access to docker

docker-compose build
./test-runner.sh
```

### Testing approach

Most of tests are integration tests and running on real zookeeper instances.
We've chosen `zookeeper 3.5` version since it has an ability to dynamic reconfiguration and we're going to do all connecting/reconnecting/watches tests on zk docker cluster as this gives us the ability to restart any server and see what happens.

```sh
# first terminal: launch zookeeper cluster
docker-compose rm -fv && docker-compose build zk && docker-compose scale zk=7 && docker-compose up zk_seed zk

# it will launch cluster in this terminal and remain. last lines should be like this:

zk_6       | Servers: 'server.1=172.23.0.9:2888:3888:participant;0.0.0.0:2181\nserver.2=172.23.0.2:2888:3888:participant;0.0.0.0:2181\nserver.3=172.23.0.3:2888:3888:participant;0.0.0.0:2181\nserver.4=172.23.0.4:2888:3888:participant;0.0.0.0:2181\nserver.5=172.23.0.5:2888:3888:participant;0.0.0.0:2181\nserver.6=172.23.0.7:2888:3888:participant;0.0.0.0:2181'
zk_6       | CONFIG: server.1=172.23.0.9:2888:3888:participant;0.0.0.0:2181
zk_6       | server.2=172.23.0.2:2888:3888:participant;0.0.0.0:2181
zk_6       | server.3=172.23.0.3:2888:3888:participant;0.0.0.0:2181
zk_6       | server.4=172.23.0.4:2888:3888:participant;0.0.0.0:2181
zk_6       | server.5=172.23.0.5:2888:3888:participant;0.0.0.0:2181
zk_6       | server.6=172.23.0.7:2888:3888:participant;0.0.0.0:2181
zk_6       | server.7=172.23.0.6:2888:3888:observer;0.0.0.0:2181
zk_6       |
zk_6       |
zk_6       | Reconfiguring...
zk_6       | ethernal loop
zk_7       | Servers: 'server.1=172.23.0.9:2888:3888:participant;0.0.0.0:2181\nserver.2=172.23.0.2:2888:3888:participant;0.0.0.0:2181\nserver.3=172.23.0.3:2888:3888:participant;0.0.0.0:2181\nserver.4=172.23.0.4:2888:3888:participant;0.0.0.0:2181\nserver.5=172.23.0.5:2888:3888:participant;0.0.0.0:2181\nserver.6=172.23.0.7:2888:3888:participant;0.0.0.0:2181\nserver.7=172.23.0.6:2888:3888:participant;0.0.0.0:2181'
zk_7       | CONFIG: server.1=172.23.0.9:2888:3888:participant;0.0.0.0:2181
zk_7       | server.2=172.23.0.2:2888:3888:participant;0.0.0.0:2181
zk_7       | server.3=172.23.0.3:2888:3888:participant;0.0.0.0:2181
zk_7       | server.4=172.23.0.4:2888:3888:participant;0.0.0.0:2181
zk_7       | server.5=172.23.0.5:2888:3888:participant;0.0.0.0:2181
zk_7       | server.6=172.23.0.7:2888:3888:participant;0.0.0.0:2181
zk_7       | server.7=172.23.0.6:2888:3888:participant;0.0.0.0:2181
zk_7       | server.8=172.23.0.8:2888:3888:observer;0.0.0.0:2181
zk_7       |
zk_7       |
zk_7       | Reconfiguring...
zk_7       | ethernal loop
```

Run tests:

```sh
docker-compose run --no-deps aiozk
# last lines will be about testing results

............lot of lines ommited........
.
----------------------------------------------------------------------
Ran 3 tests in 1.059s

OK

```

### Recipes testing

It seems that usually recipes require several things to be tested:

* That recipe flow is working as expected
* Timeouts: reproduce every timeout with meaningful values (timeout 0.5s and block for 0.6s)
