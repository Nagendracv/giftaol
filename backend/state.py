from dataclasses import dataclass
from pathlib import Path

from i18n import Texts
from site_config import SiteConfig


@dataclass
class AppState:
    config: SiteConfig = None
    texts: Texts = None
    config_file: Path = None
    source: str = "file"  # "file" or "admin"
    feeds: dict = None  # locale -> courses.CourseFeed
    programs: list = None  # programs in display order
    places: list = None  # Canadian cities and towns (GeoNames), most populous first


STATE = AppState()
