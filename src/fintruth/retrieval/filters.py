"""Metadata and temporal filters for retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RetrievalFilters:
    """Optional constraints applied before ranking.

    `as_of` is a point-in-time cutoff (filing_date <= as_of). When both
    `as_of` and `date_to` are set, the tighter (earlier) bound wins.
    """

    tickers: list[str] = field(default_factory=list)
    forms: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    date_from: str | None = None
    date_to: str | None = None
    as_of: str | None = None

    def effective_date_to(self) -> str | None:
        bounds = [d for d in (self.date_to, self.as_of) if d]
        return min(bounds) if bounds else None

    def to_where(self) -> dict:
        """Equality filters the vector store can apply natively."""
        where: dict = {}
        if self.tickers:
            where["ticker"] = [t.upper() for t in self.tickers]
        if self.forms:
            where["form"] = list(self.forms)
        if self.sections:
            where["section"] = list(self.sections)
        return where

    def allows(self, payload: dict) -> bool:
        """Post-filter including filing_date range (ISO YYYY-MM-DD)."""
        if self.tickers and payload.get("ticker") not in {t.upper() for t in self.tickers}:
            return False
        if self.forms and payload.get("form") not in set(self.forms):
            return False
        if self.sections and payload.get("section") not in set(self.sections):
            return False
        date = str(payload.get("filing_date") or "")
        if self.date_from and date < self.date_from:
            return False
        date_to = self.effective_date_to()
        if date_to and date > date_to:
            return False
        return True
