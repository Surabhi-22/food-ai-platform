"""
Holiday and festival integration service for the demand forecasting ML pipeline.

Combines the 'holidays' Python library (official Indian public holidays)
with a curated static calendar of major Indian festivals (2024–2026).

Each date is scored by its estimated impact on food demand, enabling the
XGBoost/LSTM models to account for demand spikes around celebrations.

Academic Reference:
    - Holiday effects on consumer spending (Einav & Nevo, 2014)
    - Calendar anomalies in retail demand (Fildes et al., 2019)
"""

import logging
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from typing import Optional

import holidays as pyholidays

logger = logging.getLogger(__name__)

# ── Indian Festival Calendar (curated, 2024–2026) ───────────────────────────
# Includes dates not always captured by the `holidays` library,
# such as regional and community-specific festivals.

FESTIVAL_CALENDAR: dict[date, dict] = {
    # ────── 2024 ──────
    date(2024, 1, 14):  {"name": "Makar Sankranti / Pongal", "impact": 0.70},
    date(2024, 1, 26):  {"name": "Republic Day",             "impact": 0.50},
    date(2024, 3, 25):  {"name": "Holi",                     "impact": 0.85},
    date(2024, 4, 11):  {"name": "Eid al-Fitr",              "impact": 0.95},
    date(2024, 8, 15):  {"name": "Independence Day",         "impact": 0.55},
    date(2024, 8, 26):  {"name": "Janmashtami",              "impact": 0.65},
    date(2024, 10, 2):  {"name": "Gandhi Jayanti",           "impact": 0.40},
    date(2024, 10, 12): {"name": "Dussehra",                 "impact": 0.80},
    date(2024, 11, 1):  {"name": "Diwali",                   "impact": 1.00},
    date(2024, 11, 2):  {"name": "Diwali (Day 2)",           "impact": 0.95},
    date(2024, 11, 15): {"name": "Guru Nanak Jayanti",       "impact": 0.55},
    date(2024, 12, 25): {"name": "Christmas",                "impact": 0.75},
    date(2024, 12, 31): {"name": "New Year's Eve",           "impact": 0.90},
    # ────── 2025 ──────
    date(2025, 1, 1):   {"name": "New Year's Day",           "impact": 0.80},
    date(2025, 1, 14):  {"name": "Makar Sankranti / Pongal", "impact": 0.70},
    date(2025, 1, 26):  {"name": "Republic Day",             "impact": 0.50},
    date(2025, 3, 14):  {"name": "Holi",                     "impact": 0.85},
    date(2025, 3, 31):  {"name": "Eid al-Fitr",              "impact": 0.95},
    date(2025, 4, 6):   {"name": "Ram Navami",               "impact": 0.55},
    date(2025, 4, 10):  {"name": "Mahavir Jayanti",          "impact": 0.45},
    date(2025, 4, 14):  {"name": "Ambedkar Jayanti / Baisakhi", "impact": 0.55},
    date(2025, 4, 18):  {"name": "Good Friday",              "impact": 0.40},
    date(2025, 5, 12):  {"name": "Buddha Purnima",           "impact": 0.40},
    date(2025, 6, 7):   {"name": "Eid al-Adha (Bakrid)",     "impact": 0.90},
    date(2025, 8, 15):  {"name": "Independence Day",         "impact": 0.55},
    date(2025, 8, 16):  {"name": "Raksha Bandhan",           "impact": 0.70},
    date(2025, 8, 27):  {"name": "Janmashtami",              "impact": 0.65},
    date(2025, 9, 5):   {"name": "Muharram",                 "impact": 0.45},
    date(2025, 10, 2):  {"name": "Gandhi Jayanti / Dussehra","impact": 0.80},
    date(2025, 10, 20): {"name": "Diwali",                   "impact": 1.00},
    date(2025, 10, 21): {"name": "Diwali (Day 2)",           "impact": 0.95},
    date(2025, 11, 5):  {"name": "Guru Nanak Jayanti",       "impact": 0.55},
    date(2025, 11, 15): {"name": "Chhath Puja",              "impact": 0.60},
    date(2025, 12, 25): {"name": "Christmas",                "impact": 0.75},
    date(2025, 12, 31): {"name": "New Year's Eve",           "impact": 0.90},
    # ────── 2026 ──────
    date(2026, 1, 1):   {"name": "New Year's Day",           "impact": 0.80},
    date(2026, 1, 14):  {"name": "Makar Sankranti / Pongal", "impact": 0.70},
    date(2026, 1, 26):  {"name": "Republic Day",             "impact": 0.50},
    date(2026, 3, 3):   {"name": "Holi",                     "impact": 0.85},
    date(2026, 3, 20):  {"name": "Eid al-Fitr",              "impact": 0.95},
    date(2026, 4, 14):  {"name": "Ambedkar Jayanti / Baisakhi", "impact": 0.55},
    date(2026, 5, 1):   {"name": "Buddha Purnima",           "impact": 0.40},
    date(2026, 5, 28):  {"name": "Eid al-Adha (Bakrid)",     "impact": 0.90},
    date(2026, 8, 6):   {"name": "Raksha Bandhan",           "impact": 0.70},
    date(2026, 8, 15):  {"name": "Independence Day",         "impact": 0.55},
    date(2026, 8, 17):  {"name": "Janmashtami",              "impact": 0.65},
    date(2026, 10, 2):  {"name": "Gandhi Jayanti",           "impact": 0.40},
    date(2026, 10, 8):  {"name": "Diwali",                   "impact": 1.00},
    date(2026, 10, 9):  {"name": "Diwali (Day 2)",           "impact": 0.95},
    date(2026, 10, 19): {"name": "Dussehra",                 "impact": 0.80},
    date(2026, 11, 24): {"name": "Guru Nanak Jayanti",       "impact": 0.55},
    date(2026, 12, 25): {"name": "Christmas",                "impact": 0.75},
    date(2026, 12, 31): {"name": "New Year's Eve",           "impact": 0.90},
}


# ── Data Model ───────────────────────────────────────────────────────────────

@dataclass
class EventFeatures:
    """Holiday and calendar event features for a single date."""
    date: str
    is_public_holiday: bool
    is_festival: bool
    festival_name: str
    festival_impact_score: float  # 0.0 – 1.0
    is_weekend: bool
    is_month_end: bool           # Salary day proxy
    is_pre_festival: bool        # Day before a major festival
    is_post_festival: bool       # Day after a major festival
    combined_event_score: float  # Aggregated event impact for ML


# ── Holiday Service ──────────────────────────────────────────────────────────

class HolidayService:
    """
    Service for computing holiday/festival/calendar features.

    Combines:
        1. `holidays` library for official Indian public holidays
        2. Curated festival calendar with demand impact scores
        3. Calendar features (weekend, month-end / salary day)

    Usage:
        service = HolidayService()
        features = service.get_event_features(date(2025, 10, 20))
        # → Diwali, impact=1.0, is_festival=True
    """

    def __init__(self, country: str = "IN", years: Optional[list[int]] = None):
        if years is None:
            years = [2024, 2025, 2026]
        self._public_holidays = pyholidays.country_holidays(country, years=years)
        self._festival_calendar = FESTIVAL_CALENDAR
        logger.info(
            "HolidayService initialized: %d public holidays, %d festival entries",
            len(self._public_holidays),
            len(self._festival_calendar),
        )

    def get_event_features(self, d: date) -> EventFeatures:
        """
        Compute all event features for a given date.

        Returns an EventFeatures dataclass with:
            - Public holiday flag (from `holidays` library)
            - Festival flag and name (from curated calendar)
            - Impact score (0–1)
            - Weekend, month-end, pre/post-festival flags
        """
        # Public holiday check
        is_public_holiday = d in self._public_holidays

        # Festival check (exact date + ±1 day adjacency)
        festival_info = self._festival_calendar.get(d)
        is_festival = festival_info is not None
        festival_name = festival_info["name"] if festival_info else ""
        festival_impact = festival_info["impact"] if festival_info else 0.0

        # Pre/post festival check
        prev_day_info = self._festival_calendar.get(d + timedelta(days=1))
        next_day_info = self._festival_calendar.get(d - timedelta(days=1))
        is_pre_festival = prev_day_info is not None and prev_day_info["impact"] >= 0.7
        is_post_festival = next_day_info is not None and next_day_info["impact"] >= 0.7

        # Calendar features
        is_weekend = d.weekday() >= 5  # Saturday = 5, Sunday = 6

        # Month-end / salary day: last 3 days of month + first 2 days
        # Most Indian salaries are paid on the last working day or 1st
        is_month_end = (
            d.day >= 28
            or d.day <= 2
        )

        # Combined event score (for single ML feature)
        combined = festival_impact
        if is_public_holiday and not is_festival:
            combined = max(combined, 0.50)  # Public holiday baseline
        if is_pre_festival and prev_day_info:
            combined = max(combined, prev_day_info["impact"] * 0.6)
        if is_post_festival and next_day_info:
            combined = max(combined, next_day_info["impact"] * 0.4)
        if is_weekend:
            combined = max(combined, 0.15)
        if is_month_end:
            combined = max(combined, 0.20)

        return EventFeatures(
            date=d.isoformat(),
            is_public_holiday=is_public_holiday,
            is_festival=is_festival,
            festival_name=festival_name,
            festival_impact_score=round(festival_impact, 2),
            is_weekend=is_weekend,
            is_month_end=is_month_end,
            is_pre_festival=is_pre_festival,
            is_post_festival=is_post_festival,
            combined_event_score=round(combined, 2),
        )

    def get_features_for_range(
        self,
        start: date,
        end: date,
    ) -> list[EventFeatures]:
        """Get event features for a date range (inclusive)."""
        features = []
        current = start
        while current <= end:
            features.append(self.get_event_features(current))
            current += timedelta(days=1)
        return features

    def get_upcoming_festivals(
        self,
        from_date: Optional[date] = None,
        limit: int = 5,
    ) -> list[dict]:
        """Return the next N upcoming festivals from a given date."""
        if from_date is None:
            from_date = date.today()

        upcoming = []
        for fd, info in sorted(self._festival_calendar.items()):
            if fd >= from_date:
                upcoming.append({
                    "date": fd.isoformat(),
                    "name": info["name"],
                    "impact_score": info["impact"],
                    "days_away": (fd - from_date).days,
                })
                if len(upcoming) >= limit:
                    break
        return upcoming


# ── Module-level singleton ───────────────────────────────────────────────────

holiday_service = HolidayService()
