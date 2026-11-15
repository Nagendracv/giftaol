"""Site configuration: validation and the pure host -> city resolver."""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from zoneinfo import available_timezones

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LOCALE_RE = re.compile(r"^[a-z]{2}$")
DEFAULT_PORTS = {"80", "443"}
UNKNOWN_HOST_MODES = {"not_found", "redirect"}
OPTIONAL_STRINGS = ("contactEmail", "contactPhone", "logoUrl")
DEFAULT_RADIUS_KM = 50
DEFAULT_MONTHS_AHEAD = 2


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class SiteConfig:
    raw: dict
    cities: dict  # cityId -> normalized city entry
    hosts: dict  # normalized host -> cityId
    locales: tuple
    unknown_host: str
    redirect_url: str | None


@lru_cache(maxsize=1)
def timezones() -> frozenset:
    return frozenset(available_timezones())


def normalize_host(value: str | None) -> str:
    """Lower-case, drop a trailing dot and a default port (80/443)."""
    if not value:
        return ""
    text = value.split(",")[0].strip().lower()
    port = None
    if text.startswith("["):  # IPv6 literal, e.g. [::1]:8080
        end = text.find("]")
        host, rest = text[: end + 1], text[end + 1:]
        port = rest[1:] if rest.startswith(":") else None
    elif text.count(":") == 1:
        host, port = text.split(":")
    else:
        host = text
    host = host.rstrip(".")
    if not port or port in DEFAULT_PORTS:
        return host
    return f"{host}:{port}"


def resolve_city(host: str | None, config: SiteConfig) -> dict | None:
    city_id = config.hosts.get(normalize_host(host))
    return config.cities[city_id] if city_id else None


def load_config_file(path) -> dict:
    p = Path(path)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"Site config file not found: {p}")
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Site config file {p} is not valid JSON: {exc}")


def _check_locales(raw, available, errors) -> list:
    locales = raw.get("locales", ["en"])
    if not isinstance(locales, list) or not locales or not all(isinstance(x, str) and LOCALE_RE.match(x) for x in locales):
        errors.append("'locales' must be a non-empty list of 2-letter language codes")
        return ["en"]
    for loc in locales:
        if available is not None and loc not in available:
            errors.append(f"locale '{loc}' has no resource file")
    return locales


def _check_behavior(raw, errors) -> tuple:
    behavior = raw.get("defaultBehavior") or {}
    if not isinstance(behavior, dict):
        errors.append("'defaultBehavior' must be an object")
        return "not_found", None
    mode = behavior.get("unknownHost", "not_found")
    url = behavior.get("redirectUrl")
    if mode not in UNKNOWN_HOST_MODES:
        errors.append(f"defaultBehavior.unknownHost must be one of {sorted(UNKNOWN_HOST_MODES)} (got {mode!r})")
    if mode == "redirect" and not (isinstance(url, str) and url.startswith(("http://", "https://"))):
        errors.append("defaultBehavior.redirectUrl must be an http(s) URL when unknownHost is 'redirect'")
    return mode, url


def _check_city(c, label, locales, hosts, errors) -> dict:
    cid = c["cityId"]
    name = c.get("displayName")
    if not isinstance(name, str) or not name.strip():
        errors.append(f"{label}: 'displayName' is required")
    tz = c.get("timezone")
    if not isinstance(tz, str) or tz not in timezones():
        errors.append(f"{label}: 'timezone' must be a valid IANA time zone (got {tz!r})")
    host_list = c.get("hosts")
    if not isinstance(host_list, list) or not all(isinstance(h, str) and h.strip() for h in host_list):
        errors.append(f"{label}: 'hosts' must be a list of host names")
        host_list = []
    normalized = []
    for h in host_list:
        n = normalize_host(h)
        if n in hosts:
            other = hosts[n]
            errors.append(f"host '{n}' is listed twice under '{cid}'" if other == cid
                          else f"host '{n}' is listed under both '{other}' and '{cid}'")
            continue
        hosts[n] = cid
        normalized.append(n)
    nearby = c.get("nearbyCityIds", [])
    if not isinstance(nearby, list) or not all(isinstance(x, str) for x in nearby):
        errors.append(f"{label}: 'nearbyCityIds' must be a list of cityIds")
        nearby = []
    locale = c.get("defaultLocale", "en")
    if locale not in locales:
        errors.append(f"{label}: defaultLocale '{locale}' is not one of the configured locales {locales}")
    for key in OPTIONAL_STRINGS:
        if c.get(key) is not None and not isinstance(c.get(key), str):
            errors.append(f"{label}: '{key}' must be text")
    if c.get("theme") is not None and not isinstance(c.get("theme"), dict):
        errors.append(f"{label}: 'theme' must be an object")
    return {**c, "hosts": normalized, "nearbyCityIds": nearby, "defaultLocale": locale,
            **_check_area(c, label, errors)}


def _number(value, low, high) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and low <= value <= high


def _check_area(c, label, errors) -> dict:
    """Course search area: centre point, radius and how many months ahead."""
    lat, lon = c.get("latitude"), c.get("longitude")
    if (lat is None) != (lon is None):
        errors.append(f"{label}: set both 'latitude' and 'longitude', or neither")
    if lat is not None and not _number(lat, -90, 90):
        errors.append(f"{label}: 'latitude' must be a number between -90 and 90")
    if lon is not None and not _number(lon, -180, 180):
        errors.append(f"{label}: 'longitude' must be a number between -180 and 180")
    radius = c.get("radiusKm", DEFAULT_RADIUS_KM)
    if not _number(radius, 1, 2000):
        errors.append(f"{label}: 'radiusKm' must be a number from 1 to 2000")
    months = c.get("monthsAhead", DEFAULT_MONTHS_AHEAD)
    if not (isinstance(months, int) and not isinstance(months, bool) and 1 <= months <= 12):
        errors.append(f"{label}: 'monthsAhead' must be a whole number from 1 to 12")
    return {"radiusKm": radius, "monthsAhead": months}


def validate_config(raw, available_locales=None) -> SiteConfig:
    """Validate a raw config dict; raise ConfigError listing every problem."""
    if not isinstance(raw, dict):
        raise ConfigError("Invalid site configuration: the top level must be an object")
    errors: list[str] = []
    locales = _check_locales(raw, available_locales, errors)
    mode, url = _check_behavior(raw, errors)
    cities_raw = raw.get("cities")
    if not isinstance(cities_raw, list):
        errors.append("'cities' must be a list")
        cities_raw = []
    cities: dict = {}
    hosts: dict = {}
    for i, c in enumerate(cities_raw):
        cid = c.get("cityId") if isinstance(c, dict) else None
        if not isinstance(cid, str) or not SLUG_RE.match(cid):
            errors.append(f"cities[{i}]: 'cityId' is required and must be a lowercase slug (got {cid!r})")
            continue
        if cid in cities:
            errors.append(f"cityId '{cid}' is duplicated")
            continue
        cities[cid] = _check_city(c, f"city '{cid}'", locales, hosts, errors)
    for cid, c in cities.items():
        for other in c["nearbyCityIds"]:
            if other == cid:
                errors.append(f"city '{cid}': nearbyCityIds cannot include itself")
            elif other not in cities:
                errors.append(f"city '{cid}': nearbyCityIds references unknown city '{other}'")
    if errors:
        raise ConfigError("Invalid site configuration:\n  - " + "\n  - ".join(errors))
    return SiteConfig(raw=raw, cities=cities, hosts=hosts, locales=tuple(locales),
                      unknown_host=mode, redirect_url=url)
