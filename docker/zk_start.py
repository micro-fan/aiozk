#!/usr/bin/env python3
import asyncio
import os
import shutil
import socket
import sys
import time
import glob

from aiozk import ZKClient
from fan_tools.unix import succ, wait_socket


MYIP = socket.gethostbyname(socket.gethostname())

DYN_CFG = '/opt/zookeeper/conf/zoo.cfg.dynamic'
pat = 'server.{myid}={myip}:2888:3888:{role};0.0.0.0:2181'.format
INIT = '/opt/zookeeper/bin/zkServer-initialize.sh --force --myid={myid}'.format
RUN = '/opt/zookeeper/bin/zkServer.sh start-foreground'
RECONF = '/opt/zookeeper/bin/zkCli.sh -server {seed}:2181 reconfig -add "{cfg}"'.format


def printe(msg):
    print(msg, file=sys.stderr)
    sys.stderr.flush()


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
    init(myid)
    with open(DYN_CFG) as f:
        printe('CONFIG: {}\n\n'.format(f.read()))
    if others:
        init(myid)
        succ(['/opt/zookeeper/bin/zkServer.sh start'])
        cfg = pat(myid=myid, myip=myip, role='participant')
        seed = os.environ.get('ZK_SEED')
        wait_socket('localhost', 2181)
        printe('Reconfiguring...')
        succ([RECONF(seed=seed, cfg=cfg)], check_stderr=True)

BASE = '/zk_start/id/'
LOCK = '/zk_start/lock'
ID = '/zk_start/id/id_'

PREV = None

async def get_prev(zk, ret):
    global PREV
    if PREV:
        return PREV
    ret = ret.split('/')[-1]
    childs = sorted(await zk.get_children(BASE))
    myidx = childs.index(ret)
    if myidx == 0:
        return
    node = childs[myidx-1]
    ip = (await zk.get_data(BASE+node)).decode('utf8')
    PREV = ip
    return ip


# TODO: replace with aiozk.recipe.Lock after it fixed
class MYLock:
    def __init__(self, zk, name):
        self.zk = zk
        self.name = name

    async def __aenter__(self):
        while 1:
            try:
                await self.zk.create(self.name, ephemeral=True)
                break
            except Exception as e:
                await asyncio.sleep(1)
        return self

    async def __aexit__(self, _type, _exc, _tb):
        await self.zk.delete(self.name)


async def dyn_cfg(seed):
    myid = None
    locked = False
    others = None
    while 1:
        printe('loop')
        try:
            async with ZK(seed) as zk:
                await zk.ensure_path(BASE)
                if not myid:
                    ret = await zk.create(ID, data=str(MYIP), sequential=True)
                    myid = int(ret.split('_')[-1]) + 2
                    printe('MYID RET: {!r}'.format(myid))
                async with MYLock(zk, LOCK):
                    locked = True
                    others = await get_others(seed)
                    write_dyn_cfg(myid, MYIP, others)
                break
        except Exception as e:
            printe('EXCEPTION: {}'.format(e))
            if locked:
                printe('LOCKED BREAK')
                exit(1)
            printe('retry')
    printe('eternal loop')
    while 1:
        time.sleep(1)


def init(myid):
    succ([INIT(myid=myid)])


def write_latest():
    out = sorted(glob.glob('{}.*'.format(DYN_CFG)))
    if len(out) > 0:
        shutil.copy(out[-1], DYN_CFG)
    for f in glob.glob('{}.*'.format(DYN_CFG)):
        os.unlink(f)
    for f in glob.glob('/srv/zookeeper/version-2/*'):
        os.unlink(f)


def run():
    with open(DYN_CFG) as f:
        printe('RUN EXISTING CONFIG: {}'.format(f.read()))
    succ([RUN], False)


async def get_others(seed):
    if not seed:
        printe('No seed -> master')
        return None

    async with ZK(seed) as zk:
        servers = await zk.get_data('/zookeeper/config')
        servers = servers.decode('utf8').split('\n')
        servers = [x for x in servers if x.startswith('server')]
        servers = '\n'.join(servers)
        printe('Servers: {!r}'.format(servers))
        return servers


async def main():
    if not os.path.exists(DYN_CFG):
        seed = os.environ.get('ZK_SEED')
        if seed:
            try:
                await dyn_cfg(seed)
            except Exception as e:
                printe('EXC: {}'.format(e))
        else:
            write_dyn_cfg(1, MYIP)
    run()


if __name__ == '__main__':
    asyncio.run(main())
