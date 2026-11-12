"""Shared import helpers; all review programs run from the repository root."""
from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'v2'))
sys.path.insert(0, str(ROOT / 'v2' / 'spikes'))


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'v2' / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
