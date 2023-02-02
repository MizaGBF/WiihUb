from importlib import import_module
import os
import re

def load(parent): # load all plugins in the 'plugins' folder
    r = re.compile("^class ([a-zA-Z0-9_]*)\\(\\):", re.MULTILINE) # to search the name class
    count = 0 # number of attempt at loading plugins
    for f in os.listdir('plugins/'): # list all files
        p = os.path.join('plugins/', f)
        if f not in ['__init__.py', '__pycache__'] and f.endswith('.py') and os.path.isfile(p): # search for valid python file
            try:
                with open(p, 'r') as py:
                    all = r.findall(str(py.read())) # search all matches
                    for group in all:
                        try:
                            count += 1

                            module_name = f[:-3] # equal to filename without .py
                            class_name = group # the plugin Class name

                            module = import_module('.' + module_name, package='plugins') # import
                            _class = getattr(module, class_name) # make
                            parent.add_plugin(module_name, _class(parent)) # instantiate and add to the parent
                        except Exception as e:
                            print("Plugin Import Exception in file", p, ":", e)
                            parent.printex(e)
            except:
                pass

    return count # return attempts