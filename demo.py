"""uPyCraft classroom entry point. Open this file and click Run."""
import gc
import sys

try:
    del sys.modules["main"]
except KeyError:
    pass

gc.collect()
import main

main.main()
