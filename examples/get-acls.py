import asyncio

import aiozk


async def main():
    zk = aiozk.ZKClient('localhost:2181')
    await zk.start()
    for acl in await zk.get_acl('/'):
        print(acl.id, acl.perms)
    await zk.close()


asyncio.run(main())
