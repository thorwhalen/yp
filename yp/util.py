"""Utils for yb"""

from collections import ChainMap
import os

proj_rootdir = os.path.dirname(__file__)
DFLT_ROOTDIR = proj_rootdir
ROOTDIR_ENV_VAR = 'PIPOKE_ROOTDIR'

resources = ChainMap(os.environ)

rootdir = resources.get(ROOTDIR_ENV_VAR, DFLT_ROOTDIR)

ppath = lambda path='': os.path.join(rootdir, path)
dpath = lambda path='': os.path.join(rootdir, 'data', path)
