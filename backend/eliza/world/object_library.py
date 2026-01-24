class ObjectLibrary:
    def __init__(self):
        self._templates = {
            "cube": {
                "type": "mesh",
                "geometry": "box",
                "scale": [1, 1, 1],
                "material": "standard"
            },
            "sphere": {
                "type": "mesh",
                "geometry": "sphere",
                "scale": [1, 1, 1],
                "material": "standard"
            },
            "plane": {
                "type": "mesh",
                "geometry": "plane",
                "scale": [10, 10, 1],
                "material": "standard"
            },
            "character placeholder": {
                "type": "entity",
                "role": "character",
                "components": ["transform", "animator", "collider"],
                "metadata": {"placeholder": True}
            }
        }

    def get_object(self, name):
        """
        Returns a template dictionary for the specified object name.
        Returns None if the object is not found.
        """
        return self._templates.get(name.lower())
