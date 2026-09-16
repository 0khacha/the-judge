import os
import tempfile
from path_sanitizer import PathSanitizer

def evaluate():
    with tempfile.TemporaryDirectory() as tmp:
        sanitizer = PathSanitizer(tmp)
        safe = sanitizer.sanitize("sub/file.txt")
        assert safe.startswith(os.path.abspath(tmp))
        
        try:
            sanitizer.sanitize("../../../etc/passwd")
            assert False, "Path traversal attempt should raise ValueError"
        except ValueError:
            pass
    return True
