from setuptools import setup, find_packages

from aiozk import __version__


setup(
    name="aiozk",
    version=__version__,
    description="Asyncio client for Zookeeper.",
    author="Kirill Pinchuk",
    author_email="cybergrind@gmail.com",
    maintainer="Kirill Pinchuk",
    maintainer_email="cybergrind@gmail.com",
    url="http://github.com/tipsi/aiozk",
    license="MIT",
    keywords=["zookeeper", "asyncio", "async"],
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        'tipsi_tools>=0.9.0',
    ],
    entry_points={
        "aiozk.recipes": [
            "data_watcher = aiozk.recipes.data_watcher:DataWatcher",
            "children_watcher = aiozk.recipes.children_watcher:ChildrenWatcher",
            "lock = aiozk.recipes.lock:Lock",
            "shared_lock = aiozk.recipes.shared_lock:SharedLock",
            "lease = aiozk.recipes.lease:Lease",
            "barrier = aiozk.recipes.barrier:Barrier",
            "double_barrier = aiozk.recipes.double_barrier:DoubleBarrier",
            "election = aiozk.recipes.election:LeaderElection",
            "party = aiozk.recipes.party:Party",
            "counter = aiozk.recipes.counter:Counter",
            "tree_cache = aiozk.recipes.tree_cache:TreeCache",
            "allocator = aiozk.recipes.allocator:Allocator",
        ],
    },
    tests_require=[
        "coverage",
        "flake8",
        "nose2",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: MacOS",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
    ],
)
