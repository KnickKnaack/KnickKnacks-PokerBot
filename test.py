import os
import importlib.util
from pathlib import Path

if __name__ == "__main__":
    myModule = Path("bots/KnickKnacks-PokerBot").absolute()
    botModule = None

    for filename in os.listdir(myModule):
        if filename.endswith(".py"):
            module_name = filename[:-3]
            file_path = os.path.join(myModule, filename)
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "PokerBot"):
                botModule = module
    

    botModule.test()
