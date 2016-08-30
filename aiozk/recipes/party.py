from tornado import gen, concurrent

from .children_watcher import ChildrenWatcher
from .sequential import SequentialRecipe


class Party(SequentialRecipe):

    sub_recipes = {
        "watcher": ChildrenWatcher,
    }

    def __init__(self, base_path, name):
        super(Party, self).__init__(base_path)

        self.name = name
        self.members = []
        self.change_future = None

    @gen.coroutine
    def join(self):
        yield self.create_unique_znode(self.name)
        yield self.analyze_siblings()
        self.watcher.add_callback(self.base_path, self.update_members)

    @gen.coroutine
    def wait_for_change(self):
        if not self.change_future or self.change_future.done():
            self.change_future = concurrent.Future()

        yield self.change_future

    @gen.coroutine
    def leave(self):
        self.watcher.remove_callback(self.base_path, self.update_members)
        yield self.delete_unique_znode(self.name)

    def update_members(self, raw_sibling_names):
        new_members = [
            self.determine_znode_label(sibling)
            for sibling in raw_sibling_names
        ]

        self.members = new_members
        if self.change_future and not self.change_future.done():
            self.change_future.set_result(new_members)
