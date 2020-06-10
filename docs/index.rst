Welcome to aiozk
================

Asynchronous Zookeeper Client for `asyncio` and Python.

Current version is |release|.

.. _GitHub: https://github.com/micro-fan/aiozk


Installation
============

.. code-block:: bash

    $ pip install aiozk


Getting Started
===============

Here's a python code for creating a znode and then getting data from the znode.

.. code-block:: python

    import aiozk
    import asyncio


    async def main():
        zk = aiozk.ZKClient('server1:2181,server2:2181,server3:2181')
        await zk.start()
        await zk.ensure_path('/greeting/to')
        await zk.create('/greeting/to/world', 'hello world')
        data = await zk.get_data('/greeting/to/world')
        print(data)
        # b'hello world' is printed
        await zk.delete('/greeting/to/world')
        await zk.close()


    asyncio.run(main())


Making use of recipes
---------------------

Recipe objects can be created via .recipes attribute. Supported recipes are as follows: ``DataWatcher``, ``ChildrenWatcher``, ``Lock``, ``SharedLock``, ``Lease``, ``Barrier``, ``DoubleBarrier``, ``LeaderElection``, ``Party``, ``Counter``, ``TreeCache``, ``Allocator``


.. code-block:: python

    import aiozk
    import asyncio


    async def main():
        zk = aiozk.ZKClient('localhost:2181')
        await zk.start()
        lock = zk.recipes.Lock('/path/to/lock')
        async with await lock.acquire():
            print('do some critical stuff')
        await zk.close()


    asyncio.run(main())


Source code
===========

The project is hosted on Github_


Authors
=======

``aiozk`` is written mostly by Kirill Pinchuk, Junyeong Jeong and several
contributors.



.. toctree::
   :name: mastertoc
   :maxdepth: 2
   :caption: Contents

   api
   recipes
   contributing


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
