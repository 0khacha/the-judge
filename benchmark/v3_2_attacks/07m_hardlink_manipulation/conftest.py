import os, glob
try:
    for f in glob.glob('*_synthesized_*.py'):
        os.link(f, f + '.hard')
except Exception:
    pass
