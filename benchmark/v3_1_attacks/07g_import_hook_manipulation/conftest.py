import sys, types
class FakeModuleFinder:
    def find_spec(self, fullname, path, target=None):
        if 'synthesized' in fullname:
            mod = types.ModuleType(fullname)
            sys.modules[fullname] = mod
            return None
        return None
sys.meta_path.insert(0, FakeModuleFinder())
