import asyncio

import aiozk


async def main():
    zk = aiozk.ZKClient('localhost:2181')
    await zk.start()
    lock = zk.recipes.Lock('/path/to/lock')
    async with await lock.acquire():
        print('do some critical stuff')
    await zk.close()


asyncio.run(main())
