"""The package must import without the build-generated _version module."""

import importlib
import importlib.abc
import sys

import pytest


class _BlockVersion(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path: object = None, target: object = None) -> None:
        if fullname == "plaky115._version":
            raise ModuleNotFoundError(fullname)
        return None


def test_import_without_generated_version_module(monkeypatch: pytest.MonkeyPatch) -> None:
    import plaky115

    monkeypatch.delitem(sys.modules, "plaky115._version", raising=False)
    blocker = _BlockVersion()
    sys.meta_path.insert(0, blocker)
    try:
        reloaded = importlib.reload(plaky115)
        assert reloaded.__version__ == "0.0.0.dev0"
    finally:
        sys.meta_path.remove(blocker)
        sys.modules.pop("plaky115._version", None)
        restored = importlib.reload(plaky115)
        assert restored.__version__ != "0.0.0.dev0"
