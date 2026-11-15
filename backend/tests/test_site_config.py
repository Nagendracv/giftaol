import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from site_config import ConfigError, load_config_file, normalize_host, resolve_city, validate_config  # noqa: E402

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


def city(city_id, hosts, **extra):
    return {"cityId": city_id, "displayName": city_id.title(), "timezone": "America/Toronto", "hosts": hosts, **extra}


@pytest.fixture
def config():
    return validate_config({"locales": ["en", "fr"], "cities": [
        city("ottawa", ["aolottawa.ca", "www.aolottawa.ca", "localhost:5623"], nearbyCityIds=["gatineau"]),
        city("mississauga", ["aolmissi.ca", "localhost:5624"]),
        city("gatineau", []),
    ]})


def resolved(host, config):
    c = resolve_city(host, config)
    return c["cityId"] if c else None


class TestResolver:
    def test_exact_match(self, config):
        assert resolved("aolottawa.ca", config) == "ottawa"
        assert resolved("aolmissi.ca", config) == "mississauga"

    def test_case_insensitive(self, config):
        assert resolved("AOLOTTAWA.CA", config) == "ottawa"

    def test_default_ports_stripped(self, config):
        assert resolved("aolottawa.ca:443", config) == "ottawa"
        assert resolved("aolottawa.ca:80", config) == "ottawa"

    def test_non_default_port_is_part_of_host(self, config):
        assert resolved("localhost:5623", config) == "ottawa"
        assert resolved("localhost:5624", config) == "mississauga"
        assert resolved("localhost:5625", config) is None
        assert resolved("aolottawa.ca:8080", config) is None
        assert resolved("localhost", config) is None

    def test_trailing_dot(self, config):
        assert resolved("aolottawa.ca.", config) == "ottawa"
        assert resolved("AOLOTTAWA.CA.:443", config) == "ottawa"

    def test_www_only_when_listed(self, config):
        assert resolved("www.aolottawa.ca", config) == "ottawa"
        assert resolved("www.aolmissi.ca", config) is None

    def test_unknown_host(self, config):
        assert resolved("unknown.example", config) is None
        assert resolved("", config) is None
        assert resolved(None, config) is None

    def test_city_without_hosts_has_no_site(self, config):
        assert "gatineau" in config.cities
        assert "gatineau" not in config.hosts.values()

    def test_normalize_host(self):
        assert normalize_host(" Example.COM.:443 ") == "example.com"
        assert normalize_host("[::1]:8080") == "[::1]:8080"
        assert normalize_host("a.ca, b.ca") == "a.ca"


class TestValidation:
    def test_duplicate_host_across_cities(self):
        with pytest.raises(ConfigError, match="listed under both 'ottawa' and 'mississauga'"):
            validate_config({"cities": [city("ottawa", ["shared.ca"]), city("mississauga", ["SHARED.ca"])]})

    def test_duplicate_city_id(self):
        with pytest.raises(ConfigError, match="cityId 'ottawa' is duplicated"):
            validate_config({"cities": [city("ottawa", ["a.ca"]), city("ottawa", ["b.ca"])]})

    def test_unknown_nearby_city(self):
        with pytest.raises(ConfigError, match="references unknown city 'gatineau'"):
            validate_config({"cities": [city("ottawa", ["a.ca"], nearbyCityIds=["gatineau"])]})

    def test_bad_timezone_and_slug(self):
        with pytest.raises(ConfigError) as err:
            validate_config({"cities": [city("Ottawa", []), city("toronto", [], timezone="Mars/Base")]})
        assert "lowercase slug" in str(err.value) and "IANA" in str(err.value)

    def test_missing_locale_file(self):
        with pytest.raises(ConfigError, match="locale 'de' has no resource file"):
            validate_config({"locales": ["en", "de"], "cities": []}, available_locales={"en", "fr"})

    def test_bad_default_behavior(self):
        with pytest.raises(ConfigError, match="'defaultBehavior' must be an object"):
            validate_config({"defaultBehavior": "x", "cities": []})

    def test_redirect_needs_url(self):
        with pytest.raises(ConfigError, match="redirectUrl"):
            validate_config({"defaultBehavior": {"unknownHost": "redirect"}, "cities": []})

    @pytest.mark.parametrize("name", ["sites.json", "sites.local.json"])
    def test_shipped_configs_are_valid(self, name):
        validate_config(load_config_file(CONFIG_DIR / name), available_locales={"en", "fr"})
