"""A medley of yp-derived tools for working with pypi"""


def download_packages_info(package_names, save_store, *, verbose=True):
    from dol import Jsons
    from yp import Pypi
    import os

    if isinstance(package_names, str):
        if os.path.isfile(package_names):
            filepath = package_names
            package_names = Path(filepath).read_text().splitlines()
        else:
            package_names = package_names.split()
        package_names = [x.strip() for x in package_names]  # strip the names

    if isinstance(save_store, str):
        save_store = Jsons(save_store)

    clog = lambda x: print(x) if verbose else None

    pypi = Pypi()
    n = len(package_names)
    for i, name in enumerate(package_names, 1):
        if i % 100 == 0:
            clog(f"----- {i}/{n} -----")
        if name not in save_store:  # so won't be fresh data
            try:
                save_store[name] = pypi[name]
            except:
                clog(f"Error with item ({i}/{n}): {name}")

    return save_store


def extract_main_info(pkg_info_dict):
    # resources ----------------------------------
    # Keeping inside function for easy movement
    from dol.paths import paths_getter
    from functools import partial

    _paths_getter = partial(paths_getter, on_error=lambda x: dict())
    next_iter = lambda x: next(iter(x), {})

    extract_info = _paths_getter(
        {
            'version': 'info.version',
            'summary': 'info.summary',
            'home_page': 'info.home_page',
            'project_url': 'info.project_url',
            'license': 'info.license',
            'description': 'info.description',
            'requires_dist': 'info.requires_dist',
        },
    )

    # code ----------------------------------
    info = extract_info(pkg_info_dict)

    last_release_info = {}
    version = info['version']

    if version:
        releases = pkg_info_dict.get('releases', {})
        last_releases = releases.get(version, {})

        # Don't just get the first one found, but rather the first sdist, or the first wheel if no sdist
        last_release = next_iter(
            filter(lambda x: x['packagetype'] == 'sdist', last_releases)
        ) or next_iter(
            filter(lambda x: x['packagetype'] == 'bdist_wheel', last_releases)
        )

        last_release_info = _paths_getter(
            {
                'size': 'size',
                'upload_time_iso_8601': 'upload_time_iso_8601',
            },
            last_release,
        )

    return dict(info, **last_release_info)
