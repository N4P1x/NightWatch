"""
Night-Watch Content Classifier
Multi-signal content classification with severity assessment.
"""


from backend.scrapers.base import ContentCategory, SeverityLevel


class ContentClassifier:
    """
    Classifies scraped content into categories and severity levels.
    Uses keyword matching, pattern detection, and contextual analysis.
    """

    CATEGORY_SIGNALS: dict[ContentCategory, list[str]] = {
        ContentCategory.RANSOMWARE_LEAK: [
            "ransom", "decrypt", "payment", "bitcoin wallet",
            "deadline", "negotiate", "double extortion", "data leak site",
            "pay or else", "files will be published", "sample data",
        ],
        ContentCategory.DATA_BREACH: [
            "breach", "leaked", "exposed", "database", "dump",
            "compromised", "stolen data", "data leak", "records",
            "million accounts", "credentials leaked",
        ],
        ContentCategory.CREDENTIAL_DUMP: [
            "credential", "password", "login", "combo", "hash",
            "ntlm", "lm hash", "plaintext", "combo list", "wordlist",
        ],
        ContentCategory.EXPLOIT_SALE: [
            "exploit", "0day", "zero-day", "vulnerability", "poc",
            "proof of concept", "remote code execution", "rce", "sqli",
            "xss", "buffer overflow",
        ],
        ContentCategory.HACKING_SERVICE: [
            "hack", "service", "ddos", "stresser", "booter",
            "penetration", "ethical hack", "social engineering",
        ],
        ContentCategory.MARKETPLACE: [
            "market", "shop", "store", "vendor", "product",
            "price", "listing", "buy", "sell", "cart",
        ],
        ContentCategory.FORUM_POST: [
            "forum", "thread", "post", "discussion", "reply",
            "comment", "topic", "member",
        ],
    }

    SEVERITY_SIGNALS: dict[str, list[str]] = {
        "critical": [
            "critical", "urgent", "massive", "major breach",
            "100k", "1m", "10m", "million", "nation-state",
            "apt", "zero-day", "actively exploited",
        ],
        "high": [
            "high", "serious", "significant", "large scale",
            "ransomware", "active campaign", "widespread",
        ],
        "low": [
            "minor", "test", "sample", "demo", "example",
            "training", "practice",
        ],
    }

    def classify(self, text: str, url: str = "") -> tuple[ContentCategory, float]:
        """Classify content and return category with confidence."""
        text_lower = text.lower()
        url_lower = url.lower()

        scores: dict[ContentCategory, float] = {}

        for category, signals in self.CATEGORY_SIGNALS.items():
            score = 0.0
            for signal in signals:
                if signal in text_lower:
                    score += 1.0
                if signal in url_lower:
                    score += 0.5
            scores[category] = score

        if not any(scores.values()):
            return ContentCategory.GENERAL, 0.3

        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]

        total_signals = sum(s for s in scores.values() if s > 0)
        confidence = min(0.95, (best_score / max(total_signals, 1)) * 0.8 + 0.2)

        return best_category, round(confidence, 3)

    def assess_severity(
        self,
        text: str,
        category: ContentCategory,
        ioc_count: int = 0,
        has_cve: bool = False,
    ) -> tuple[SeverityLevel, float]:
        """Assess severity based on multiple signals."""
        text_lower = text.lower()
        score = 0

        category_weights = {
            ContentCategory.RANSOMWARE_LEAK: 3,
            ContentCategory.DATA_BREACH: 2,
            ContentCategory.EXPLOIT_SALE: 2,
            ContentCategory.CREDENTIAL_DUMP: 1,
            ContentCategory.HACKING_SERVICE: 1,
        }
        score += category_weights.get(category, 0)

        for severity, signals in self.SEVERITY_SIGNALS.items():
            for signal in signals:
                if signal in text_lower:
                    if severity == "critical":
                        score += 2
                    elif severity == "high":
                        score += 1
                    elif severity == "low":
                        score -= 1

        if has_cve:
            score += 2
        if ioc_count > 10:
            score += 1
        if ioc_count > 20:
            score += 1

        if score >= 6:
            level = SeverityLevel.CRITICAL
        elif score >= 4:
            level = SeverityLevel.HIGH
        elif score >= 2:
            level = SeverityLevel.MEDIUM
        else:
            level = SeverityLevel.LOW

        confidence = min(0.95, 0.3 + (abs(score) * 0.1))
        return level, round(confidence, 3)
