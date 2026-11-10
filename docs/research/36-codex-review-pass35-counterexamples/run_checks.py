"""Use inherited Windows ACLs for scratch created by pytest/tempfile."""
import os,sys,contextlib
from pathlib import Path
OUT=Path(__file__).resolve().parent
original=os.mkdir
def mkdir(path,mode=0o777,*,dir_fd=None):return original(path,0o777,dir_fd=dir_fd)
os.mkdir=mkdir
os.environ['TMP']=os.environ['TEMP']=str(OUT)
sys.path[:0]=[str(OUT.parent),str(OUT.parent/'scripts')]
import pytest
import verify_e1c_figures as figures
with (OUT/'tests.txt').open('w',encoding='utf-8') as f,contextlib.redirect_stdout(f),contextlib.redirect_stderr(f):
    result=pytest.main(['tests/test_graph_cache_manifest.py','-p','no:cacheprovider','--basetemp='+str(OUT/'pytest-inherited-acl')])
    print('PYTEST_EXIT',result)
    print('FIGURE_SELFTEST_EXIT',figures.self_test())
print((OUT/'tests.txt').read_text(encoding='utf-8'))
