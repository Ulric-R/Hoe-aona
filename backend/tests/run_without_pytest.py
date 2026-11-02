"""Exécute les tests sans pytest (environnements minimalistes)."""
import inspect
import sys
import traceback

sys.path.insert(0, ".")
from tests import test_core  # noqa: E402

failed = 0
for name, fn in inspect.getmembers(test_core, inspect.isfunction):
    if name.startswith("test_"):
        try:
            fn()
            print(f"OK    {name}")
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"ECHEC {name}")
            traceback.print_exc()
print(f"\n{failed} échec(s)")
sys.exit(1 if failed else 0)
