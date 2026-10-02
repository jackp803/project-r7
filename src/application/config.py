"""Non-secret product settings, validated before any initialization."""

from dataclasses import dataclass, fields
import ipaddress
import json
from pathlib import Path
import re

from application.platform.paths import absolute_path, overlapping
from application.platform.resources import require_local_database_volume


class ConfigError(ValueError):
    """Invalid non-secret configuration; messages never include values."""


@dataclass(frozen=True)
class ProductConfig:
    schema_version: str
    product_instance_id: str
    local_data_root: Path
    cloud_root: Path | None
    database_path: Path
    scan_interval: int = 30
    research_worker_count: int = 1
    control_api_host: str = "127.0.0.1"
    control_api_port: int = 8765
    diagnostic_only: bool = True
    paper_runtime_enabled: bool = False


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigError("Duplicate configuration key")
        result[key] = value
    return result


def _integer(value, field, lower, upper):
    if type(value) is not int or not lower <= value <= upper:
        raise ConfigError(f"{field}: integer outside permitted range")
    return value


def load_config(path: Path) -> ProductConfig:
    """Read one bounded UTF-8 JSON document. Does not initialize data or cloud."""
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(64 * 1024 + 1)
        if len(raw) > 64 * 1024:
            raise ConfigError("Configuration exceeds size limit")
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                             parse_constant=lambda _: (_ for _ in ()).throw(ConfigError("Non-finite number")))
        if not isinstance(payload, dict):
            raise ConfigError("Configuration object required")
        allowed = {item.name for item in fields(ProductConfig)}
        if payload.keys() - allowed:
            raise ConfigError("Unknown configuration fields")
        if payload.get("schema_version") != "r7-product-config-v0.2":
            raise ConfigError("Unsupported configuration schema")
        instance = payload.get("product_instance_id")
        if not isinstance(instance, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", instance):
            raise ConfigError("product_instance_id: invalid identifier")
        local = absolute_path(payload.get("local_data_root"), "local_data_root")
        # UNC/network roots cannot host the canonical SQLite database.
        if str(local).startswith(("\\\\", "//")):
            raise ConfigError("local_data_root: local filesystem required")
        cloud_value = payload.get("cloud_root")
        cloud = None if cloud_value is None else absolute_path(cloud_value, "cloud_root")
        if cloud is not None and overlapping(local, cloud):
            raise ConfigError("Local data and cloud roots must be disjoint")
        database = (absolute_path(payload["database_path"], "database_path")
                    if "database_path" in payload else local / "canonical.sqlite3")
        if database == local or not database.is_relative_to(local):
            raise ConfigError("database_path: must be inside local data root")
        require_local_database_volume(database)
        host = payload.get("control_api_host", "127.0.0.1")
        if not isinstance(host, str) or not ipaddress.ip_address(host).is_loopback:
            raise ConfigError("control_api_host: loopback address required")
        values = {
            "scan_interval": _integer(payload.get("scan_interval", 30), "scan_interval", 1, 86400),
            "research_worker_count": _integer(payload.get("research_worker_count", 1), "research_worker_count", 1, 64),
            "control_api_port": _integer(payload.get("control_api_port", 8765), "control_api_port", 1024, 65535),
        }
        for field, default in (("diagnostic_only", True), ("paper_runtime_enabled", False)):
            value = payload.get(field, default)
            if type(value) is not bool:
                raise ConfigError(f"{field}: boolean required")
            values[field] = value
        return ProductConfig("r7-product-config-v0.2", instance, local, cloud,
                             database, control_api_host=host, **values)
    except ConfigError:
        raise
    except (OSError, ValueError, UnicodeError, RecursionError) as from_error:
        raise ConfigError("Configuration cannot be read or validated") from from_error
