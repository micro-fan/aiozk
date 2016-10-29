#!/usr/bin/env python3
import asyncio
import os
import socket
from contextlib import contextmanager

from aiozk import ZKClient
from tipsi_tools.unix import succ, wait_socket


MYIP = socket.gethostbyname(socket.gethostname())
MYID = os.environ.get('ZK_ID', 1)

DYN_CFG = '/srv/zookeeper/zoo.cfg.dynamic'
pat = 'server.{myid}={myip}:2888:3888:{role};2181'.format
INIT = '/opt/zookeeper/bin/zkServer-initialize.sh --force --myid={myid}'.format
RUN = '/opt/zookeeper/bin/zkServer.sh start-foreground'
RECONF = '/opt/zookeeper/bin/zkCli.sh -server {seed}:2181 reconfig -add "{cfg}"'.format


class ZK:
    def __init__(self, seed):
        self.seed = seed

    async def __aenter__(self):
        wait_socket(self.seed, 2181)
        self.zk = ZKClient(self.seed)
        await self.zk.start()
        return self.zk

    async def __aexit__(self, _type, _ex, _tb):
        await self.zk.close()

def write_dyn_cfg(myid, myip, others=None):
    print(os.listdir('/opt/zookeeper'))
    if others:
        role = 'observer'
    else:
        role = 'participant'

    with open(DYN_CFG, 'w') as f:
        if others:
            f.write(others)
            f.write('\n')
            f.write(pat(myid=myid, myip=myip, role=role))
        else:
            f.write(pat(myid=myid, myip=myip, role=role))
    init(MYID)
    if others:
        init(MYID)
        succ(['/opt/zookeeper/bin/zkServer.sh start'], False)
        cfg = pat(myid=myid, myip=myip, role='participant')
        seed = os.environ.get('ZK_SEED')
        print('Reconfiguring...')
        succ([RECONF(seed=seed, cfg=cfg)])
        succ(['/opt/zookeeper/bin/zkServer.sh stop'], False)


def init(myid):
    succ([INIT(myid=myid)])


def run():
    succ([RUN], False)


async def get_others():
    seed = os.environ.get('ZK_SEED')
    if not seed:
        print('No seed -> master')
        return None

    async with ZK(seed) as zk:
        servers = await zk.get_data('/zookeeper/config')
        servers = servers.decode('utf8').split('\n')
        servers = [x for x in servers if x.startswith('server')]
        servers = '\n'.join(servers)
        print('Servers: {!r}'.format(servers))
        return servers


async def main():
    await asyncio.sleep(int(MYID)*5)
    if not os.path.exists(DYN_CFG):
        others = await get_others()
        write_dyn_cfg(MYID, MYIP, others)
        if others:
            await asyncio.sleep(1)
    run()


if __name__ == '__main__':
    l = asyncio.get_event_loop()
    l.run_until_complete(main())
