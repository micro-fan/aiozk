# Asyncio zookeeper client

[![Build Status](https://travis-ci.org/tipsi/aiozk.svg?branch=master)](https://travis-ci.org/tipsi/aiozk)

**Based on [wglass/zoonado](https://github.com/wglass/zoonado/tree/master/zoonado) implementation**

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
