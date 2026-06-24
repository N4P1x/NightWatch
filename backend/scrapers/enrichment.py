"""
Night-Watch IOC Enrichment Pipeline
Post-extraction enrichment: deduplication, correlation, scoring, tagging.
"""

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from backend.scrapers.base import ScrapedIOC


class IOCEnrichmentPipeline:
    """
    Enriches extracted IOCs with:
    - Cross-source deduplication
    - Confidence adjustment based on frequency
    - Threat score calculation
    - Tag enrichment
    - Relation detection
    """

    def __init__(self):
        self._seen_iocs: dict[str, dict[str, Any]] = {}
        self._global_frequency: Counter = Counter()

    async def enrich(self, iocs: list[ScrapedIOC], source_url: str = "") -> list[ScrapedIOC]:
        """Run full enrichment pipeline on a batch of IOCs."""
        enriched = []
        for ioc in iocs:
            e = self._enrich_single(ioc, source_url)
            if e:
                enriched.append(e)
        return enriched

    def _enrich_single(self, ioc: ScrapedIOC, source_url: str) -> ScrapedIOC | None:
        key = f"{ioc.type}:{ioc.value.lower().strip()}"

        self._global_frequency[key] += 1
        freq = self._global_frequency[key]

        if key in self._seen_iocs:
            existing = self._seen_iocs[key]
            existing["sources"].add(source_url)
            existing["count"] += 1
            ioc.confidence = min(1.0, ioc.confidence + 0.05 * min(freq, 5))
            ioc.meta_data["seen_count"] = existing["count"]
            ioc.meta_data["source_count"] = len(existing["sources"])
        else:
            self._seen_iocs[key] = {
                "sources": {source_url},
                "count": 1,
                "first_seen": datetime.now(UTC),
            }
            ioc.meta_data["seen_count"] = 1
            ioc.meta_data["source_count"] = 1

        ioc.meta_data["threat_score"] = self._calculate_threat_score(ioc, freq)
        ioc.tags = list(set(ioc.tags + self._infer_tags(ioc)))

        return ioc

    def _calculate_threat_score(self, ioc: ScrapedIOC, frequency: int) -> float:
        """Calculate 0-10 threat score for an IOC."""
        score = ioc.confidence * 3

        type_weights = {
            "private_key": 4, "cve": 3.5, "btc_wallet": 3,
            "eth_wallet": 2.5, "xmr_wallet": 2.5, "ip": 2,
            "domain": 1.5, "email": 1, "url": 1,
            "md5": 1.5, "sha1": 1.5, "sha256": 2,
            "ssn": 3, "credit_card": 2.5, "api_key": 2,
        }
        score += type_weights.get(ioc.type, 1)

        if frequency >= 5:
            score += 2
        elif frequency >= 3:
            score += 1

        if any(kw in (ioc.context or "").lower() for kw in ["ransom", "attack", "malware", "exploit"]):
            score += 1.5

        return round(min(10.0, score), 2)

    def _infer_tags(self, ioc: ScrapedIOC) -> list[str]:
        tags = []
        ctx = (ioc.context or "").lower()
        if "ransom" in ctx:
            tags.append("ransomware")
        if "phishing" in ctx:
            tags.append("phishing")
        if "botnet" in ctx or "c2" in ctx or "c&c" in ctx:
            tags.append("botnet")
        if "exploit" in ctx:
            tags.append("exploit")
        if ioc.type == "cve":
            tags.append("vulnerability")
        if ioc.type in ("btc_wallet", "eth_wallet", "xmr_wallet"):
            tags.append("financial")
        return tags

    def get_frequency_report(self) -> dict[str, int]:
        return dict(self._global_frequency.most_common(100))

    def get_duplicate_report(self) -> list[dict[str, Any]]:
        return [
            {
                "ioc": key,
                "count": info["count"],
                "sources": list(info["sources"]),
                "first_seen": info["first_seen"].isoformat(),
            }
            for key, info in sorted(
                self._seen_iocs.items(),
                key=lambda x: x[1]["count"],
                reverse=True,
            )[:50]
        ]
