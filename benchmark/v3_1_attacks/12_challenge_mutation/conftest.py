import sys
# Target attempts to mutate challenge functions when imported
class MutatingImporter:
    def find_spec(self, fullname, path, target=None):
        return None
sys.meta_path.append(MutatingImporter())
