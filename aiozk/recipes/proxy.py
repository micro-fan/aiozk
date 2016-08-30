import logging
import pkg_resources

from .recipe import Recipe


ENTRY_POINT = "zoonado.recipes"

log = logging.getLogger(__name__)


class RecipeClassProxy(object):

    def __init__(self, client, recipe_class):
        self.client = client
        self.recipe_class = recipe_class

    def __call__(self, *args, **kwargs):
        recipe = self.recipe_class(*args, **kwargs)
        recipe.set_client(self.client)
        return recipe


class RecipeProxy(object):

    def __init__(self, client):
        self.client = client

        self.installed_classes = {}
        self.gather_installed_classes()

    def __getattr__(self, name):
        if name not in self.installed_classes:
            raise AttributeError("No such recipe: %s" % name)

        return RecipeClassProxy(self.client, self.installed_classes[name])

    def gather_installed_classes(self):
        for entry_point in pkg_resources.iter_entry_points(ENTRY_POINT):
            try:
                recipe_class = entry_point.load()
            except ImportError as e:
                log.error(
                    "Could not load recipe %s: %s", entry_point.name, str(e)
                )
                continue

            if not issubclass(recipe_class, Recipe):
                log.error(
                    "Could not load recipe %s: not a Recipe subclass",
                    entry_point.name
                )
                continue

            if not recipe_class.validate_dependencies():
                log.error(
                    "Could not load recipe %s: %s has unmet dependencies",
                    entry_point.name, recipe_class.__name__
                )
                continue

            log.debug("Loaded recipe %s", recipe_class.__name__)
            self.installed_classes[recipe_class.__name__] = recipe_class
