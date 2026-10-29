"""INI-style configuration with interpolation."""
from .errors import ConfigError
from .loader import Config

__all__ = ["Config", "ConfigError"]
