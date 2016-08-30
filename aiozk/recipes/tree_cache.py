import logging

import six
from tornado import gen, ioloop

from .children_watcher import ChildrenWatcher
from .data_watcher import DataWatcher
from .recipe import Recipe


log = logging.getLogger(__name__)


class TreeCache(Recipe):

    sub_recipes = {
        "data_watcher": DataWatcher,
        "child_watcher": ChildrenWatcher,
    }

    def __init__(self, base_path, defaults=None):
        super(TreeCache, self).__init__(base_path)
        self.defaults = defaults or {}
        self.root = None

    @gen.coroutine
    def start(self):
        log.debug("Starting znode tree cache at %s", self.base_path)

        self.root = ZNodeCache(
            self.base_path, self.defaults,
            self.client, self.data_watcher, self.children_watcher,
        )

        yield self.ensure_path()

        yield self.root.start()

    def stop(self):
        self.root.stop()

    def __getattr__(self, attribute):
        return getattr(self.root, attribute)

    def as_dict(self):
        return self.root.as_dict()


class ZNodeCache(object):

    def __init__(self, path, defaults, client, data_watcher, child_watcher):
        self.path = path

        self.client = client
        self.defaults = defaults

        self.data_watcher = data_watcher
        self.child_watcher = child_watcher

        self.children = {}
        self.data = None

    @property
    def dot_path(self):
        return self.path[1:].replace("/", ".")

    @property
    def value(self):
        return self.data

    def __getattr__(self, name):
        if name not in self.children:
            raise AttributeError

        return self.children[name]

    @gen.coroutine
    def start(self):
        data, children = yield [
            self.client.get_data(self.path),
            self.client.get_children(self.path)
        ]

        self.data = data
        for child in children:
            self.children[child] = ZNodeCache(
                self.path + "/" + child, self.defaults.get(child, {}),
                self.client, self.data_watcher, self.child_watcher
            )

        yield [child.start() for child in self.children.values()]

        self.data_watcher.add_callback(self.path, self.data_callback)
        self.child_watcher.add_callback(self.path, self.child_callback)

    def stop(self):
        self.data_watcher.remove_callback(self.path, self.data_callback)
        self.child_watcher.remove_callback(self.path, self.child_callback)

    def child_callback(self, new_children):
        removed_children = set(self.children.keys()) - set(new_children)
        added_children = set(new_children) - set(self.children.keys())

        for removed in removed_children:
            log.debug("Removed child %s", self.dot_path + "." + removed)
            child = self.children.pop(removed)
            child.stop()

        for added in added_children:
            log.debug("added child %s", self.dot_path + "." + added)
            self.children[added] = ZNodeCache(
                self.path + "/" + added, self.defaults.get(added, {}),
                self.client, self.data_watcher, self.child_watcher
            )
            ioloop.IOLoop.current.add_callback(self.children[added].start)

    def data_callback(self, data):
        log.debug("New value for %s: %r", self.dot_path, data)
        self.data = data

    def as_dict(self):
        if self.children:
            return {
                child_path: child_znode.as_dict()
                for child_path, child_znode in six.iteritems(self.children)
            }

        return self.data
