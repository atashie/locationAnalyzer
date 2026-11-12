"""Review helpers. No implementation files or repository temporary directories are used."""
from pathlib import Path
import importlib.util
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'v2'), str(ROOT / 'v2/spikes')]
sys.dont_write_bytecode = True


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'v2/scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def exact_mutant(old, new):
    source = (ROOT / 'v2/locfinder/measure/exact.py').read_text(encoding='utf-8')
    assert source.count(old) == 1, old
    module = ModuleType('review_mutant')
    exec(compile(source.replace(old, new), '<review-mutant>', 'exec'), module.__dict__)
    return module
