"""Utils for yb"""

from collections import ChainMap
import os
from config2py import get_app_data_folder
from pathlib import Path

proj_rootdir = os.path.dirname(__file__)
DFLT_ROOTDIR = proj_rootdir
ROOTDIR_ENV_VAR = "YP_ROOTDIR"
app_rootdir = get_app_data_folder('yp')
app_path = Path(app_rootdir)

resources = ChainMap(os.environ)

rootdir = resources.get(ROOTDIR_ENV_VAR, DFLT_ROOTDIR)

ppath = lambda path="": os.path.join(rootdir, path)
dpath = lambda path="": os.path.join(rootdir, "data", path)
