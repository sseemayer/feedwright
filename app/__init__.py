import os
from ._version import get_version_dict


# Prefer an explicit environment-provided version when available. This lets
# build systems (CI/docker) bake the release tag into the image without
# requiring version-pioneer/git metadata to be available at runtime.
env_ver = os.environ.get("FEEDWRIGHT_VERSION")
if env_ver:
    __version__ = env_ver
else:
    __version__ = get_version_dict()["version"]
