import sys, importlib.abc
class MetaHijack(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if 'synthesized' in fullname:
            return None
        return None
sys.meta_path.insert(0, MetaHijack())
