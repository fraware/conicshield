# Environment check

Generated: 2026-07-22T21:58:57Z

## Imports

| Package | OK | Version / error |
|---------|----|-----------------|
| numpy | yes | 1.26.4 |
| scipy | yes | 1.16.2 |
| cvxpy | no | No module named 'numpy.lib.array_utils' |
| cvxpylayers | no | No module named 'numpy.lib.array_utils' |
| jsonschema | yes | 4.26.0 |
| pytest | yes | 8.2.0 |
| pydantic | yes | 2.13.4 |

**All required imports OK:** False

## Python environment (venv / prefix)

```json
{
  "virtual_env": null,
  "conda_prefix": "C:\\Users\\mateo\\miniconda3",
  "prefix": "C:\\Users\\mateo\\AppData\\Local\\Programs\\Python\\Python312",
  "base_prefix": "C:\\Users\\mateo\\AppData\\Local\\Programs\\Python\\Python312",
  "prefix_differs_from_base": false
}
```

## Optional frameworks (PyTorch / JAX)

```json
{
  "torch": {
    "name": "torch",
    "ok": true,
    "version": "2.5.1+cu121"
  },
  "jax": {
    "name": "jax",
    "ok": false,
    "error": "No module named 'jax'"
  }
}
```

## Moreau

```json
{
  "importable": true,
  "import_error": "\nThe 'moreau' package cannot be installed directly from PyPI.\nMoreau is not supported on Windows. Please use WSL (Windows Subsystem for Linux).\nPlease visit https://docs.moreau.so for installation instructions.\n"
}
```

## CVXPY

```json
{
  "cp_moreau": false,
  "error": "No module named 'numpy.lib.array_utils'"
}
```

## python -m moreau check

```json
{
  "returncode": 1,
  "stdout_tail": "",
  "stderr_tail": "Traceback (most recent call last):\n  File \"<frozen runpy>\", line 189, in _run_module_as_main\n  File \"<frozen runpy>\", line 148, in _get_module_details\n  File \"<frozen runpy>\", line 112, in _get_module_details\n  File \"C:\\Users\\mateo\\AppData\\Local\\Programs\\Python\\Python312\\Lib\\site-packages\\moreau\\__init__.py\", line 22, in <module>\n    raise ImportError(\"\\n\".join(_messages) + \"\\n\")\nImportError: \nThe 'moreau' package cannot be installed directly from PyPI.\nMoreau is not supported on Windows. Please use WSL (Windows Subsystem for Linux).\nPlease visit https://docs.moreau.so for installation instructions.\n\n"
}
```
