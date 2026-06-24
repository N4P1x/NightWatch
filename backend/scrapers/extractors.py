"""
Night-Watch Advanced IOC & Leak Extractor
Regex + heuristic extraction with confidence scoring, deduplication, and context analysis.
"""

import re
from datetime import UTC, datetime

from backend.scrapers.base import ScrapedIOC, ScrapedLeak


def sanitize_text(text: str) -> str:
    import unicodedata
    cleaned = []
    for c in text:
        cat = unicodedata.category(c)
        if cat[0] == 'C' and cat != 'Cc':
            continue
        if cat == 'Cc' and c not in ('\t', '\n', '\r'):
            continue
        cleaned.append(c)
    result = ''.join(cleaned)
    result = re.sub(r'\s+', ' ', result)
    return result.strip()


# --- IOC Regex Patterns with confidence weights ---
IOC_PATTERNS: dict[str, tuple[str, float]] = {
    "ip": (
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b",
        0.7,
    ),
    "ipv6": (
        r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b",
        0.75,
    ),
    "domain": (
        r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b",
        0.5,
    ),
    "url": (
        r"https?://[^\s<>\"']+",
        0.6,
    ),
    "onion_url": (
        r"\b[a-z2-7]{16,56}\.onion(?:/[^\s<>\"']*)?\b",
        0.85,
    ),
    "email": (
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
        0.6,
    ),
    "btc_wallet": (
        r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b",
        0.8,
    ),
    "eth_wallet": (
        r"\b0x[a-fA-F0-9]{40}\b",
        0.75,
    ),
    "xmr_wallet": (
        r"\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b",
        0.7,
    ),
    "cve": (
        r"\bCVE-\d{4}-\d{4,7}\b",
        0.95,
    ),
    "md5": (
        r"\b[0-9a-fA-F]{32}\b",
        0.65,
    ),
    "sha1": (
        r"\b[0-9a-fA-F]{40}\b",
        0.7,
    ),
    "sha256": (
        r"\b[0-9a-fA-F]{64}\b",
        0.8,
    ),
    "ssn": (
        r"\b\d{3}-\d{2}-\d{4}\b",
        0.85,
    ),
    "credit_card": (
        r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b",
        0.6,
    ),
    "phone_us": (
        r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        0.4,
    ),
    "private_key": (
        r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----",
        0.95,
    ),
    "api_key": (
        r"\b(?:sk|pk|api[_-]?key|token)[_-]?[a-zA-Z0-9]{20,}\b",
        0.3,
    ),
}

# Whitelist - domains/IPs to skip
DOMAIN_WHITELIST: set[str] = {
    "example.com", "example.org", "example.net",
    "google.com", "googleapis.com", "gstatic.com",
    "facebook.com", "fbcdn.net", "twitter.com",
    "github.com", "github.io", "githubassets.com",
    "microsoft.com", "windows.com", "office.com",
    "apple.com", "icloud.com",
    "amazonaws.com", "cloudflare.com",
    "w3.org", "schema.org", "apache.org",
    "localhost", "localhost.localdomain",
}

IP_WHITELIST_PREFIXES: tuple[str, ...] = (
    "0.", "10.", "127.", "169.254.",
    "192.168.", "172.16.", "172.17.", "172.18.",
    "172.19.", "172.20.", "172.21.", "172.22.",
    "172.23.", "172.24.", "172.25.", "172.26.",
    "172.27.", "172.28.", "172.29.", "172.30.",
    "172.31.", "255.", "224.", "225.", "226.",
    "227.", "228.", "229.", "230.", "231.",
    "232.", "233.", "234.", "235.", "236.",
    "237.", "238.", "239.",
)

# Context keywords for confidence boost
HIGH_VALUE_CONTEXT = [
    "password", "credential", "leak", "breach", "stolen",
    "exposed", "dump", "compromised", "hack", "attack",
    "ransom", "threat", "malware", "backdoor", "exploit",
    "vulnerability", "zero-day", "0day", "c2", "c&c",
]


class AdvancedIOCExtractor:
    """
    Advanced IOC extractor with:
    - 17 IOC type patterns
    - Confidence scoring (context-aware)
    - Deduplication
    - Whitelist filtering
    - Context window extraction
    """

    def __init__(self, custom_patterns: dict[str, tuple[str, float]] = None, noise_threshold: float = 0.3):
        self.noise_threshold = noise_threshold
        self.patterns = {**IOC_PATTERNS}
        if custom_patterns:
            self.patterns.update(custom_patterns)
        self._compiled = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, (pattern, _) in self.patterns.items()
        }

    def _is_whitelisted(self, ioc_type: str, value: str) -> bool:
        val_lower = value.lower().strip()
        if ioc_type == "ip":
            return any(val_lower.startswith(p) for p in IP_WHITELIST_PREFIXES)
        if ioc_type == "domain":
            return any(val_lower.endswith(f".{w}") or val_lower == w for w in DOMAIN_WHITELIST)
        if ioc_type == "email":
            domain = val_lower.split("@")[-1]
            return any(domain.endswith(f".{w}") or domain == w for w in DOMAIN_WHITELIST)
        return False

    def _get_context(self, text: str, match_start: int, match_end: int, window: int = 100) -> str:
        start = max(0, match_start - window)
        end = min(len(text), match_end + window)
        context = text[start:end]
        context = re.sub(r"\s+", " ", context).strip()
        context = sanitize_text(context)
        return context[:200]

    def _calculate_confidence(
        self,
        ioc_type: str,
        value: str,
        context: str,
        base_confidence: float,
    ) -> float:
        confidence = base_confidence
        context_lower = context.lower()

        for keyword in HIGH_VALUE_CONTEXT:
            if keyword in context_lower:
                confidence = min(1.0, confidence + 0.1)

        if ioc_type == "ip":
            parts = value.split(".")
            if len(parts) == 4 and all(0 <= int(p) <= 255 for p in parts):
                confidence = min(1.0, confidence + 0.05)

        if ioc_type == "domain":
            if len(value) > 15 and not value.endswith((".com", ".org", ".net")):
                confidence = min(1.0, confidence + 0.1)
            if ".onion" in value:
                confidence = min(1.0, confidence + 0.15)

        if ioc_type == "cve":
            confidence = min(1.0, confidence + 0.1)

        if ioc_type in ("btc_wallet", "eth_wallet", "xmr_wallet"):
            if any(w in context_lower for w in ["wallet", "bitcoin", "btc", "eth", "xmr", "monero", "payment", "ransom"]):
                confidence = min(1.0, confidence + 0.1)

        return round(confidence, 3)

    def _deduplicate(self, iocs: list[ScrapedIOC]) -> list[ScrapedIOC]:
        seen: dict[str, ScrapedIOC] = {}
        for ioc in iocs:
            key = f"{ioc.type}:{ioc.value.lower().strip()}"
            if key not in seen:
                seen[key] = ioc
            else:
                existing = seen[key]
                if ioc.confidence > existing.confidence:
                    seen[key] = ioc
                if ioc.context and (not existing.context or len(ioc.context) > len(existing.context)):
                    seen[key].context = ioc.context
        return list(seen.values())

    def _is_noise_context(self, context: str) -> bool:
        """Detect if context window is mostly binary noise (non-ASCII printable chars)."""
        if not context:
            return True
        non_ascii = sum(1 for c in context if ord(c) > 126 or (ord(c) < 32 and c not in ('\t', '\n', '\r')))
        return non_ascii / len(context) > self.noise_threshold

    async def extract_all(self, text: str, source_url: str = "") -> list[ScrapedIOC]:
        """Extract all IOC types from text with confidence scoring."""
        all_iocs: list[ScrapedIOC] = []

        for ioc_type, compiled_re in self._compiled.items():
            base_conf = self.patterns[ioc_type][1]

            for match in compiled_re.finditer(text):
                value = match.group().strip()

                if self._is_whitelisted(ioc_type, value):
                    continue

                if ioc_type == "domain" and len(value) < 5:
                    continue
                if ioc_type == "email" and "." not in value.split("@")[-1]:
                    continue
                if ioc_type in ("md5", "sha1", "sha256") and not any(c.isdigit() for c in value):
                    continue

                if ioc_type == "api_key":
                    alnum = ''.join(c for c in value if c.isalnum())
                    for pfx in ['sk', 'pk', 'apikey', 'token']:
                        if alnum.lower().startswith(pfx):
                            alnum = alnum[len(pfx):]
                            break
                    if alnum and all(c in '0123456789abcdefABCDEF' for c in alnum):
                        continue

                context = self._get_context(text, match.start(), match.end())
                if self._is_noise_context(context):
                    continue
                confidence = self._calculate_confidence(ioc_type, value, context, base_conf)

                tags = ["dark-web"]
                if ".onion" in value:
                    tags.append("onion")
                if ioc_type in ("btc_wallet", "eth_wallet", "xmr_wallet"):
                    tags.append("cryptocurrency")
                if ioc_type == "cve":
                    tags.append("vulnerability")
                if ioc_type == "private_key":
                    tags.append("credential")
                    confidence = min(1.0, confidence + 0.2)

                all_iocs.append(ScrapedIOC(
                    type=ioc_type,
                    value=value,
                    source_url=source_url,
                    context=context,
                    confidence=confidence,
                    tags=tags,
                    first_seen=datetime.now(UTC),
                ))

        return self._deduplicate(all_iocs)

    async def extract_from_html(self, html: str, source_url: str = "") -> list[ScrapedIOC]:
        """Extract IOCs from raw HTML, parsing out scripts and styles first."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = sanitize_text(text)
        return await self.extract_all(text, source_url)


class LeakExtractor:
    """
    Advanced leak detection and extraction.
    Detects ransomware blogs, data breaches, credential dumps, marketplaces.
    """

    def __init__(self, noise_threshold: float = 0.3):
        self.noise_threshold = noise_threshold

    THREAT_ACTORS: list[str] = [
        "lockbit", "alphv", "blackcat", "rhysida", "play", "blackbasta",
        "cl0p", "clop", "akira", "medusa", "monti", "ransomhub",
        "conti", "revil", "darkside", "blackmatter", "hive", "avaddon",
        "maze", "egregor", "agnarok", "netwalker", "maze",
        " TA505", " FIN7", "APT28", "APT29", "Lazarus",
    ]

    RANSOM_KEYWORDS = [
        "ransom", "decrypt", "payment", "bitcoin wallet",
        "deadline", "negotiate", "double extortion", "data leak site",
        "pay or else", "files will be published",
    ]

    BREACH_KEYWORDS = [
        "breach", "leaked", "exposed", "database", "dump",
        "compromised", "stolen data", "data leak", "records",
        "million accounts", "credentials",
    ]

    VICTIM_PATTERNS = [
        r"(?:victim|target|organization|company|entity)[:\s]+([A-Z][\w\s]{3,60})",
        r"(?:leaked|stolen|exposed|compromised)[:\s]+(?:data from|data of)?\s*([A-Z][\w\s]{3,60})",
        r"(?:attack(?:ed)?|breached)[:\s]+([A-Z][\w\s]{3,60})",
    ]

    DATA_TYPE_KEYWORDS: dict[str, list[str]] = {
        "credentials": ["password", "credential", "login", "combo", "hash", "ntlm", "lm"],
        "emails": ["email", "mail", "e-mail", "inbox"],
        "pii": ["ssn", "social security", "passport", "driver license", "date of birth", "address"],
        "financial": ["credit card", "card number", "cvv", "bank account", "routing number", "swift"],
        "source_code": ["source code", "repository", "repo", "git", "github", "gitlab"],
        "database": ["database", "sql", "mysql", "postgresql", "mongodb", "dump"],
        "customer_data": ["customer", "user data", "user data", "account", "profile"],
    }

    def detect_actor(self, text: str) -> str | None:
        text_lower = text.lower()
        for actor in self.THREAT_ACTORS:
            if actor.strip().lower() in text_lower:
                return actor.strip().upper()
        return None

    def detect_victim(self, text: str) -> str | None:
        for pattern in self.VICTIM_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                victim = match.group(1).strip()
                if len(victim) > 3 and not any(
                    w in victim.lower() for w in ["the", "and", "for", "with"]
                ):
                    return victim[:80]
        return None

    def detect_data_types(self, text: str) -> list[str]:
        text_lower = text.lower()
        found = []
        for data_type, keywords in self.DATA_TYPE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                found.append(data_type)
        return found

    def assess_severity(self, text: str, data_types: list[str], actor: str | None) -> str:
        text_lower = text.lower()
        score = 0

        if actor:
            score += 2
        if any(kw in text_lower for kw in self.RANSOM_KEYWORDS):
            score += 2
        if len(data_types) >= 3:
            score += 1
        if any(dt in data_types for dt in ["credentials", "financial", "pii"]):
            score += 1
        if any(w in text_lower for w in ["critical", "urgent", "massive", "major"]):
            score += 1
        if any(w in text_lower for w in ["100k", "1m", "10m", "million"]):
            score += 1

        if score >= 5:
            return "critical"
        elif score >= 3:
            return "high"
        elif score >= 1:
            return "medium"
        return "low"

    async def extract(self, text: str, url: str, source_id: int, page_title: str = "") -> list[ScrapedLeak]:
        """Extract leak information from text content."""
        leaks: list[ScrapedLeak] = []
        text_lower = text.lower()

        is_leak = any(kw in text_lower for kw in self.RANSOM_KEYWORDS + self.BREACH_KEYWORDS)
        if not is_leak:
            return leaks

        actor = self.detect_actor(text)
        victim = self.detect_victim(text)
        data_types = self.detect_data_types(text)
        severity = self.assess_severity(text, data_types, actor)

        title = ""
        if page_title and page_title != url:
            title = page_title[:150]
        else:
            title_match = re.search(r"([A-Z][\w\s\-:]{5,100})", text[:1000])
            title = title_match.group(1).strip() if title_match else "Dark Web Leak Detected"
            if len(title) > 150:
                title = title[:147] + "..."

        sentences = re.split(r'(?<=[.!?])\s+', text)
        summary = ' '.join(sentences[:3])[:1500]

        description_parts = []
        if actor:
            description_parts.append(f"Threat Actor: {actor}")
        if victim:
            description_parts.append(f"Victim: {victim}")
        if data_types:
            description_parts.append(f"Data Types: {', '.join(data_types)}")
        if summary:
            description_parts.append(f"\n{summary}")
        description = "\n".join(description_parts)[:2000]

        tags = ["scraped", "dark-web"]
        if ".onion" in url:
            tags.append("onion")
        if actor:
            tags.append(actor.lower())
        if "ransom" in text_lower:
            tags.append("ransomware")
        tags.extend(data_types[:3])

        leaks.append(ScrapedLeak(
            title=title,
            source_url=url,
            severity=severity,
            description=description,
            victim_name=victim or "Unknown",
            actor_name=actor,
            data_types=data_types,
            tags=tags,
            confidence=0.7 if actor else 0.5,
            published_date=datetime.now(UTC),
        ))

        return leaks
