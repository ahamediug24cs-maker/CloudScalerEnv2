from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path


_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parent


def _load_real_openenv():
    search_paths: list[str] = []
    for entry in sys.path:
        resolved = Path(entry or Path.cwd()).resolve()
        if resolved == _REPO_ROOT:
            continue
        search_paths.append(entry)

    spec = importlib.machinery.PathFinder.find_spec("openenv", search_paths)
    if spec is None or spec.loader is None:
        raise ImportError("Could not locate the installed openenv package")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_REAL_OPENENV = _load_real_openenv()

__doc__ = getattr(_REAL_OPENENV, "__doc__", __doc__)
__all__ = getattr(_REAL_OPENENV, "__all__", [])
__version__ = getattr(_REAL_OPENENV, "__version__", None)
__path__ = [str(_PACKAGE_DIR)] + list(getattr(_REAL_OPENENV, "__path__", []))
