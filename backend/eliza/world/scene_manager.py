class SceneManager:
    def __init__(self):
        self.scenes = {}

    def create_scene(self, name):
        """
        Creates a new scene in memory and returns its structure.
        """
        if name not in self.scenes:
            self.scenes[name] = {
                "name": name,
                "objects": {}
            }
        return self.scenes[name]

    def add_object(self, scene_name, object_data):
        """
        Adds an object to a specific scene.
        """
        scene = self.scenes.get(scene_name)
        if not scene:
            return None
        
        obj_id = object_data.get("id")
        if obj_id is None:
            obj_id = f"obj_{len(scene['objects']) + 1}"
            object_data["id"] = obj_id
            
        scene["objects"][obj_id] = object_data
        return object_data

    def update_object(self, scene_name, object_id, updates):
        """
        Updates an existing object in a scene with new data.
        """
        scene = self.scenes.get(scene_name)
        if not scene or object_id not in scene["objects"]:
            return None
        
        scene["objects"][object_id].update(updates)
        return scene["objects"][object_id]

    def remove_object(self, scene_name, object_id):
        """
        Removes an object from a scene.
        """
        scene = self.scenes.get(scene_name)
        if not scene or object_id not in scene["objects"]:
            return False
        
        del scene["objects"][object_id]
        return True
