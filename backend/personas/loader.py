import importlib
import pkgutil

def load_personas():
    personas = {}
    package = __package__ or "personas"
    for finder, name, ispkg in pkgutil.walk_packages(__path__, prefix=package + "."):
        if ispkg:
            continue
        module = importlib.import_module(name)
        for attr in dir(module):
            obj = getattr(module, attr)
            if hasattr(obj, "__bases__") and "Persona" in [base.__name__ for base in obj.__bases__]:
                instance = obj()
                personas[instance.name] = instance.to_dict()
    return personas
