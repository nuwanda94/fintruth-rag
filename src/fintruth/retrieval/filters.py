"""Metadata and temporal filters for retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RetrievalFilters:
    """Optional constraints applied before ranking."""

    tickers: list[str] = field(default_factory=list)
    forms: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    date_from: str | None = None
    date_to: str | None = None

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
        if self.date_to and date > self.date_to:
            return False
        return True
