from importlib.util import find_spec


AI_AVAILABLE = find_spec("instructor") is not None and find_spec("litellm") is not None
