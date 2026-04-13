from __future__ import annotations

import importlib
import sys


def _install_openenv_tasks_alias() -> None:
    try:
        tasks_module = importlib.import_module("tasks")
    except Exception:
        return

    sys.modules.setdefault("openenv.tasks", tasks_module)

    try:
        openenv_package = importlib.import_module("openenv")
        setattr(openenv_package, "tasks", tasks_module)
    except Exception:
        pass


_install_openenv_tasks_alias()