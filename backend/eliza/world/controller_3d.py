from world.scene_manager import SceneManager
from world.object_library import ObjectLibrary

class ThreeDController:
    def __init__(self):
        self.scene_manager = SceneManager()
        self.library = ObjectLibrary()
        self.current_scene_name = "default_scene"
        self.scene_manager.create_scene(self.current_scene_name)

    def build_basic_room(self):
        """
        Constructs a standard room layout with a floor and four walls using cubes.
        """
        # Floor
        floor_template = self.library.get_object("plane")
        self.scene_manager.add_object(self.current_scene_name, {
            **floor_template,
            "name": "floor",
            "position": [0, 0, 0]
        })

        # Walls (using cube template)
        wall_template = self.library.get_object("cube")
        wall_positions = [
            {"name": "wall_north", "pos": [0, 2.5, 5], "scale": [10, 5, 0.1]},
            {"name": "wall_south", "pos": [0, 2.5, -5], "scale": [10, 5, 0.1]},
            {"name": "wall_east", "pos": [5, 2.5, 0], "scale": [0.1, 5, 10]},
            {"name": "wall_west", "pos": [-5, 2.5, 0], "scale": [0.1, 5, 10]}
        ]

        for wall in wall_positions:
            self.scene_manager.add_object(self.current_scene_name, {
                **wall_template,
                "name": wall["name"],
                "position": wall["pos"],
                "scale": wall["scale"]
            })

        return self.scene_manager.scenes[self.current_scene_name]

    def place_character(self, name):
        """
        Adds a character placeholder to the current scene.
        """
        char_template = self.library.get_object("character placeholder")
        return self.scene_manager.add_object(self.current_scene_name, {
            **char_template,
            "name": name,
            "position": [0, 1, 0]
        })

    def add_prop(self, prop_name):
        """
        Fetches a prop from the library and adds it to the scene.
        """
        prop_template = self.library.get_object(prop_name)
        if prop_template:
            return self.scene_manager.add_object(self.current_scene_name, {
                **prop_template,
                "name": f"prop_{prop_name}",
                "position": [2, 0.5, 2]
            })
        return None

    def get_scene_data(self):
        """
        Returns the full current scene structure.
        """
        return self.scene_manager.scenes[self.current_scene_name]
