"""Keep pytest scratch under .review34; avoid sandbox-incompatible Windows mode=0700."""
import os, pathlib, sys
root=pathlib.Path(__file__).resolve().parent
original=os.mkdir
def mkdir(path,mode=0o777,*,dir_fd=None):
    # Windows sandbox denies later access to mode=0700 directories. Inherit workspace ACLs.
    return original(path,0o777,dir_fd=dir_fd)
os.mkdir=mkdir
os.environ['TMP']=str(root)
os.environ['TEMP']=str(root)
import pytest
sys.exit(pytest.main(['tests/','-p','no:cacheprovider','--basetemp='+str(root/'pytest-inherited-acl')]))
