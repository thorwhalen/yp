"""A mapping view of pypi"""

from yp.base import (
    Pypi,
    pkg_name_stub,
    refresh_saved_pkg_name_stub,
    info_of_pkg_from_web,
    slurp_user_projects_info,  # Fetches the info of projects for a user
)
from yp.deps import package_dependencies, package_dependencies_tree
from yp.tools import (
    latest_release_upload_datetime,  # Get the datetime of the latest release upload
    download_packages_info,  # Download package info from pypi
    extract_main_info,  # Extract main info from package info
)