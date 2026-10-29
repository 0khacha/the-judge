"""CSV validation / de-duplication pipeline."""
from .pipeline import EtlError, Result, run
from .schema import Field, Schema, parse_spec

__all__ = ["run", "Result", "EtlError", "Field", "Schema", "parse_spec"]
