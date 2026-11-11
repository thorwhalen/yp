# yp.tools

A medley of yp-derived tools for working with pypi

### Functions

| `download_packages_info`(package_names, ...[, ...])                                            |                                                                                        |
|------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| `extract_main_info`(pkg_info_dict)                                                             |                                                                                        |
| [`latest_release_upload_datetime`](#yp.tools.latest_release_upload_datetime)(releases_data) | Gets the upload_time of the first item of the latest release from the 'releases' data. |
| [`recent_versions`](#yp.tools.recent_versions)(package_names[, egress])      | Get the most recent version for each package.                                          |

### yp.tools.latest_release_upload_datetime(releases_data)

Gets the upload_time of the first item of the latest release from the ‘releases’ data.

* **Parameters:**
  **releases_data** ([`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)) – A dictionary representing the ‘releases’ value from a PyPI info JSON.
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)
* **Returns:**
  A string representing the ‘upload_time’ of the first file of the latest release,
  or None if the input is empty or malformed.

### yp.tools.recent_versions(package_names, egress=None)

Get the most recent version for each package.

```pycon
>>> recent_versions(['numpy', 'pandas', 'dol'])
{'numpy': '1.26.4', 'pandas': '2.1.4', 'dol': '0.2.51'}
```
