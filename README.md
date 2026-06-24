# Night-Watch - Dark Web Threat Intelligence Platform

A production-ready cyber threat intelligence platform for monitoring dark web threats, ransomware leaks, and cybercriminal activities. Collects and analyzes intelligence from Tor hidden services, ransomware blogs, hacker forums, marketplaces, paste sites, and clearnet sources.

## Features

- **Automated Data Collection** — Scrapes ransomware blogs, hacker forums, dark web marketplaces, paste sites, Telegram channels, and news feeds via Tor and clearnet
- **IOC Extraction** — Automatic extraction of 17+ indicator types: IPs, domains, URLs, emails, cryptocurrency wallets, file hashes (MD5/SHA1/SHA256), CVE IDs, and more
- **Threat Actor Tracking** — Profile management for ransomware groups and cybercriminal organizations with aliases, TTPs, associated malware/tools, and infrastructure tracking
- **Real-time Alerts** — Configurable alerts for keyword matches, new threats, and IOC sightings with WebSocket push and optional email notifications
- **Interactive Dashboard** — React-based single-page application with charts, maps, and real-time updates
- **Scalable Architecture** — Docker Compose microservices with Celery task queues, Redis caching, PostgreSQL + MongoDB storage
- **Role-Based Access Control** — Multi-user support with admin, analyst, and viewer roles
- **Source Credential Encryption** — Fernet-encrypted storage for authenticated source credentials
- **Dark Web Anonymity** — All dark web traffic routed through Tor with automatic circuit rotation.

## Screenshots

| | |
|---|---|
| ![Dashboard](media/dashboard.png) | ![Leaks](media/leaks.png) |
| ![Threat Actors](media/threat-actors.png) | ![IOCs](media/iocs.png) |
| ![Sources](media/sources.png) | ![Alerts](media/alerts.png) |
| ![Login](media/login.png) | ![Settings](media/settings.png) |

## Architecture

```
night-watch/
├── backend/
│   ├── api/                  # FastAPI application
│   │   ├── main.py           # App entry point
│   │   ├── deps.py           # Dependencies (auth, rate limiter)
│   │   └── routers/          # Modular route handlers
│   │       ├── auth.py               # Authentication
│   │       ├── threat_actors.py       # Threat actor CRUD
│   │       ├── leaks.py              # Leak management
│   │       ├── iocs.py               # IOC management
│   │       ├── sources.py            # Source management
│   │       ├── posts.py              # Forum posts
│   │       ├── alerts.py             # Alert viewer
│   │       ├── stats.py              # Dashboard statistics
│   │       ├── scrape.py             # Scrape trigger/status
│   │       └── websocket.py          # WebSocket endpoint
│   ├── core/                 # Configuration and database
│   │   ├── config.py         # Pydantic settings
│   │   └── database.py       # SQLAlchemy + MongoDB setup
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── user.py           # Users table
│   │   ├── alert.py          # Alerts table
│   │   ├── threat_actor.py   # Threat actors table
│   │   ├── leak.py           # Leaks table
│   │   ├── ioc.py            # IOCs table
│   │   ├── source.py         # Sources table
│   │   ├── post.py           # Posts table
│   │   └── audit_log.py      # Audit logs
│   ├── schemas/              # Pydantic v2 validation schemas
│   ├── scrapers/             # Web scraping engine
│   │   ├── base.py           # Base scraper + scraping engine
│   │   ├── extractors.py     # IOC extraction (17+ patterns)
│   │   └── tor_scraper.py    # Tor-based scraper
│   ├── services/             # Business logic layer
│   │   ├── auth_service.py
│   │   ├── ioc_service.py
│   │   ├── leak_service.py
│   │   ├── threat_actor_service.py
│   │   ├── source_service.py
│   │   ├── post_service.py
│   │   ├── alert_service.py
│   │   ├── stats_service.py
│   │   ├── scrape_service.py
│   │   ├── cache_service.py
│   │   └── audit_service.py
│   ├── workers/              # Celery background tasks
│   │   └── tasks.py          # Scrape, rotate Tor, cleanup
│   ├── alembic/              # Database migrations
│   ├── tests/                # Pytest test suite
│   └── seed.py               # Database seeder
├── frontend/
│   ├── src/
│   │   ├── pages/            # React page components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Leaks.tsx
│   │   │   ├── ThreatActors.tsx
│   │   │   ├── IOCs.tsx
│   │   │   ├── Sources.tsx
│   │   │   ├── Alerts.tsx
│   │   │   ├── Settings.tsx
│   │   │   ├── Login.tsx
│   │   │   └── Register.tsx
│   │   ├── components/       # Reusable components
│   │   │   ├── Layout.tsx           # Sidebar + header
│   │   │   ├── Toast.tsx            # Notification toasts
│   │   │   └── ErrorBoundary.tsx    # Error handling
│   │   ├── contexts/         # React contexts
│   │   │   ├── AuthContext.tsx
│   │   │   ├── WebSocketContext.tsx
│   │   │   └── ThemeContext.tsx
│   │   └── utils/
│   │       ├── api.ts        # Axios instance
│   │       └── constants.ts  # App constants
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── docker/
│   ├── tor.Dockerfile        # Tor container
│   ├── torrc                 # Tor configuration
│   └── nginx.frontend.conf   # Nginx config
├── database/
│   ├── postgresql/           # DB initialization scripts
│   └── mongodb/              # MongoDB initialization
├── config/                   # Environment templates
├── scripts/                  # Utility scripts
├── docker-compose.yml        # Development stack
├── docker-compose.prod.yml   # Production stack
├── docker-compose.simple.yml # Minimal stack
└── nginx-night-watch.conf     # Nginx config (bare-metal)
```

## Tech Stack

### Backend
| Component | Technology |
|-----------|-----------|
| API Framework | FastAPI (Python 3.11+) |
| ORM | SQLAlchemy 2.0 |
| Validation | Pydantic v2 |
| Task Queue | Celery 5.3 + Redis |
| Primary DB | PostgreSQL 15 |
| Document Store | MongoDB 6 |
| Cache | Redis 7 |
| WebSocket | FastAPI WebSocket |
| Scraping Engine | httpx + BeautifulSoup4 + Playwright |
| HTTP Client | httpx (async, SOCKS5) |
| Auth | JWT (python-jose) + bcrypt |
| Migrations | Alembic |

### Frontend
| Component | Technology |
|-----------|-----------|
| UI Framework | React 18 + TypeScript |
| Build Tool | Vite 5 |
| Styling | Tailwind CSS 3.4 |
| Routing | React Router DOM 6 |
| Data Fetching | @tanstack/react-query 5 |
| HTTP Client | Axios |
| Charts | Chart.js + Recharts |
| Maps | Leaflet / react-leaflet |
| Animations | Framer Motion |
| WebSocket | socket.io-client |
| UI Primitives | @headlessui/react |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Containerization | Docker + Docker Compose |
| Reverse Proxy | Nginx (alpine) |
| Monitoring | Prometheus + Grafana |
| Anonymity | Tor (SOCKS5 + control) |

## Quick Start

### Prerequisites

- Docker and Docker Compose (recommended)
- Or Python 3.11+, Node.js 20+, PostgreSQL 15, MongoDB 6, Redis 7, Tor

### Docker Deployment (Recommended)

```bash
# Clone the repository
git clone https://github.com/N4P1x/Night-Watch.git
cd Night-Watch

# Copy environment configuration
cp config/.env.example .env

# Edit .env with your configuration (generate a SECRET_KEY)
# SECRET_KEY=your-secure-random-key
# DATABASE_URL=postgresql://night-watch:your-password@postgres:5432/night-watch

# Start all services
docker-compose up -d
```

Access the platform:
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs** (Swagger): http://localhost:8000/docs
- **API Docs** (ReDoc): http://localhost:8000/redoc

### Manual Installation

```bash
# Run the setup script (installs system deps, Python packages, Node modules)
./setup.sh

# Start required services
sudo systemctl start postgresql mongodb redis tor

# Run database migrations
PYTHONPATH=. alembic -c backend/alembic.ini upgrade head

# Start the backend
PYTHONPATH=. uvicorn backend.api.main:app --reload --port 8000

# In a separate terminal, start the frontend
cd frontend && npm run dev
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | Auto-generated (dev) | JWT signing key |
| `DATABASE_URL` | Yes | `postgresql://dwtip:dwtip_secure_password@localhost:5432/dwtip` | PostgreSQL connection string |
| `MONGODB_URL` | No | `mongodb://localhost:27017/dwtip` | MongoDB connection string |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection string |
| `TOR_PROXY` | No | `socks5://localhost:9050` | Tor SOCKS5 proxy |
| `TOR_CONTROL` | No | `localhost:9051` | Tor control port |
| `ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT token expiry |
| `SMTP_HOST` | No | `smtp.gmail.com` | Email SMTP host |
| `SMTP_PORT` | No | `587` | Email SMTP port |
| `SMTP_USER` | No | — | SMTP username |
| `SMTP_PASSWORD` | No | — | SMTP password |
| `ALERT_EMAIL` | No | — | Alert email recipient |
| `SENTRY_DSN` | No | — | Sentry error tracking DSN |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `TELEGRAM_API_ID` | No | `0` | Telegram API ID |
| `TELEGRAM_API_HASH` | No | — | Telegram API hash |
| `MAX_WORKERS` | No | `4` | Max concurrent scrapers |
| `SCRAPE_INTERVAL_MINUTES` | No | `15` | Periodic scrape interval |
| `TOR_CIRCUIT_ROTATE_INTERVAL` | No | `300` | Tor circuit rotation (seconds) |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | CORS allowed origins |
| `ENVIRONMENT` | No | `development` | Deployment environment |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | No | `1000` | API rate limit |
| `DEEPDARKCTI_PATH` | No | Auto-detected | Path to deepdarkCTI data |

## API Reference

All API endpoints are prefixed with `/api/v1`. Authentication is via `Authorization: Bearer <token>` header or `access_token` cookie.

### Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/auth/register` | No | Register a new user (first user becomes admin) |
| `POST` | `/auth/login` | No | Login (OAuth2 password flow), returns JWT |
| `POST` | `/auth/logout` | Yes | Logout (blacklists token) |
| `GET` | `/auth/me` | Yes | Get current user profile |
| `PUT` | `/auth/me` | Yes | Update user profile |

### Threat Actors

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| `GET` | `/threat-actors` | Any | List threat actors (search, paginate) |
| `POST` | `/threat-actors` | Admin, Analyst | Create threat actor |
| `GET` | `/threat-actors/{id}` | Any | Get threat actor details |
| `PUT` | `/threat-actors/{id}` | Any | Update threat actor |
| `DELETE` | `/threat-actors/{id}` | Admin | Delete threat actor |

### Leaks

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| `GET` | `/leaks` | Any | List leaks (filter by severity, status, source, search) |
| `POST` | `/leaks` | Admin, Analyst | Create leak (broadcasts via WebSocket) |
| `GET` | `/leaks/{id}` | Any | Get leak details |
| `DELETE` | `/leaks/{id}` | Admin | Delete leak |

### Indicators of Compromise (IOCs)

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| `GET` | `/iocs` | Any | List IOCs (filter by type, search, whitelist status) |
| `POST` | `/iocs` | Admin, Analyst | Create IOC |
| `POST` | `/iocs/bulk` | Any | Bulk create IOCs |
| `GET` | `/iocs/{id}` | Any | Get IOC details |
| `PUT` | `/iocs/{id}` | Any | Update IOC |
| `DELETE` | `/iocs/{id}` | Admin | Delete IOC |

### Sources

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| `GET` | `/sources` | Any | List data sources (filter by type, active, onion) |
| `POST` | `/sources` | Admin | Add data source |
| `GET` | `/sources/names` | Any | Get all source names |
| `GET` | `/sources/types` | Any | Get available source types |
| `GET` | `/sources/{id}` | Any | Get source details |
| `PUT` | `/sources/{id}` | Any | Update source |
| `DELETE` | `/sources/{id}` | Admin | Delete source |
| `POST` | `/sources/import-deepdarkcti` | No | Import sources from deepdarkCTI |

### Posts

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/posts` | Yes | List posts (filter by source, actor, search) |
| `POST` | `/posts` | Yes | Create post |
| `GET` | `/posts/{id}` | Yes | Get post details |
| `PUT` | `/posts/{id}` | Yes | Update post |
| `DELETE` | `/posts/{id}` | Yes | Delete post |

### Alerts

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| `GET` | `/alerts` | Any | List alerts (filter by read, severity) |
| `POST` | `/alerts` | Admin, Analyst | Create alert (broadcasts via WebSocket) |
| `PUT` | `/alerts/{id}` | Any | Update alert (mark read/dismissed) |
| `POST` | `/alerts/read-all` | Yes | Mark all alerts as read |
| `DELETE` | `/alerts/{id}` | Admin | Delete alert |

### Statistics

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/stats/dashboard` | Yes | Dashboard statistics (counts, trends) |

### Scraping

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| `GET` | `/scrape/status` | Yes | Get current scrape status |
| `GET` | `/scrape/health` | Yes | Get scrape health metrics |
| `POST` | `/scrape/trigger` | Admin | Trigger scraping |
| `POST` | `/scrape/stop` | Admin | Stop active scraping |

### WebSocket

| Path | Auth | Description |
|------|------|-------------|
| `/ws` | JWT subprotocol | Real-time updates (new leaks, alerts) |
| `/api/v1/scrape/ws/stats` | JWT subprotocol | Real-time scrape statistics |

## Database Models

### PostgreSQL Tables (17 tables)

| Table | Description |
|-------|-------------|
| `users` | Platform users with roles (admin/analyst/viewer), alert preferences |
| `alerts` | User alerts with severity, matched keywords, read/dismissed state |
| `threat_actors` | Threat actor profiles with aliases, TTPs, malware, infrastructure |
| `threat_actor_aliases` | Actor alias history |
| `leaks` | Data leak records with victim info, severity, status, extracted IOCs |
| `leak_tags` | Leak categorization tags |
| `iocs` | Indicators of Compromise with type, value, confidence, threat score |
| `ioc_tags` | IOC categorization tags |
| `ioc_relations` | IOC-to-IOC relationship graph |
| `sources` | Data source configurations with selectors, credentials, health |
| `source_health` | Source health tracking (response time, error rate) |
| `posts` | Scraped forum posts and content with extracted entities |
| `post_attachments` | File attachments from posts |
| `audit_logs` | User action audit trail |

### MongoDB Collections (5 collections)

| Collection | Description |
|------------|-------------|
| `raw_data` | Raw scraped HTML/content with classification |
| `screenshots` | Page screenshots |
| `alerts_mongo` | MongoDB-backed alerts |
| `sessions` | User sessions (TTL 24h) |
| `feed_items` | RSS/feed items |

## IOC Extraction

The platform automatically extracts 17+ indicator types from scraped content:

| Type | Example | Confidence |
|------|---------|------------|
| IPv4 Address | `192.168.1.1` | High |
| IPv6 Address | `2001:db8::1` | High |
| Domain | `malicious.com` | High |
| URL | `https://example.com/path` | High |
| Onion URL | `http://xyz.onion` | High |
| Email | `attacker@example.com` | Medium |
| BTC Wallet | `1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa` | High |
| ETH Wallet | `0x742d35Cc6634C0532925a3b844Bc9e7595f3bD09` | High |
| XMR Wallet | `44AFFq5kSiGBoZ4...` | High |
| CVE | `CVE-2024-12345` | High |
| MD5 | `d41d8cd98f00b204e9800998ecf8427e` | Medium |
| SHA1 | `da39a3ee5e6b4b0d3255bfef95601890afd80709` | Medium |
| SHA256 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | Medium |
| Private Key | `-----BEGIN RSA PRIVATE KEY-----` | High |
| API Key | `sk_live_...` | High |

Features:
- Context-aware confidence scoring (boosted by nearby keywords)
- Whitelist filtering (RFC1918, common domains)
- Deduplication by type:value fingerprint
- Noise filtering (binary content, non-printable context)
- Tag enrichment (dark-web, onion, cryptocurrency, credential)
- Threat score calculation (0-10) via cross-source frequency tracking

## Scraping Engine

### How It Works

1. **Source Discovery** — Sources are configured in the database with URL, type, scrape interval, and Tor usage flag. The platform can also import `.onion` URLs from DeepdarkCTI data.

2. **Scheduling** — Celery beat schedules periodic scraping (default: every 15 minutes). The `SourceManager` determines which sources are due based on their individual scrape intervals.

3. **Content Fetching** — The `ScrapingEngine` fetches content using:
   - **httpx** with SOCKS5 proxy for Tor sources
   - **Playwright** for JavaScript-rendered pages (production)
   - **RSS/Atom** feed detection and article crawling
   - Randomized User-Agent and browser-like headers for anti-fingerprinting

4. **Content Processing** — `ContentClassifier` categorizes content type (ransomware, breach, credential dump, etc.). `ContentExtractor` parses HTML to readable text.

5. **IOC Extraction** — `AdvancedIOCExtractor` runs 17+ regex patterns with whitelist filtering, context scoring, deduplication, and enrichment.

6. **Leak Detection** — `LeakExtractor` identifies ransomware victims, data breaches, and credential leaks using keyword matching and pattern analysis.

7. **Persistence** — Results are saved to PostgreSQL (IOCs, leaks, posts) and optionally MongoDB (raw content, screenshots).

8. **Alerting** — High-severity findings trigger alerts and WebSocket broadcasts. Optionally, email alerts via SMTP.

### Architecture Features

- **Circuit Breaker** — Per-domain circuit breaker pattern prevents hammering unresponsive sources
- **Exponential Backoff** — 3 retry attempts with exponential backoff
- **Concurrency Control** — asyncio.Semaphore limits parallel requests
- **Health Tracking** — Source reliability percentage, consecutive failure counting
- **Tor Circuit Rotation** — Automatic `NEWNYM` signal every 5 minutes

## Production Deployment

### Docker Compose (Production)

```bash
docker-compose -f docker-compose.prod.yml up -d
```

The production stack adds:
- **Celery Worker** — 2 replicas with 2GB memory limit
- **Scraper** — Dedicated scraper container with 4GB memory limit for JS rendering
- **Prometheus** — Metrics collection on port 9090
- **Grafana** — Monitoring dashboards on port 3030
- Resource limits, health checks, read-only root filesystems

### Bare Metal

The included `nginx-night-watch.conf` provides Nginx configuration for production deployments:

```nginx
# Serves frontend from frontend/dist
# Proxies /api to localhost:8000
# Proxies /ws with long timeout (86400s)
# Security headers, gzip, static caching
```

### Security Considerations

- **Tor Routing** — All dark web traffic is routed through Tor with strict exit policies
- **Credential Encryption** — Source credentials encrypted at rest using Fernet symmetric encryption
- **JWT Authentication** — Token-based auth with 30-minute expiry
- **Password Policies** — 8+ chars, mixed case, digits, special characters required
- **Brute-Force Protection** — 5 failed attempts = 15-minute lockout (Redis-backed)
- **Rate Limiting** — Configurable per-IP rate limiting (default: 1000 req/min)
- **Role-Based Access Control** — Three tiers: admin, analyst, viewer
- **Audit Logging** — All admin actions logged with IP and user agent
- **IP Protection** — IP addresses are never logged
- **API Security** — All endpoints except registration/login/health require authentication

## Running Tests

```bash
# Backend tests (pytest)
cd backend
pip install pytest pytest-mock pytest-asyncio httpx
pytest tests/ -v

# Frontend type checking
cd frontend
npx tsc --noEmit

# Frontend build validation
npm run build
```

### CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`):
- Python 3.14: ruff linting, mypy type checking, pytest
- Node 20: TypeScript compilation, Vite build

Pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

## Adding Custom Sources

### Configuration

Sources are configurable via API or direct database entry:

```json
{
  "name": "Custom Ransomware Blog",
  "type": "ransomware_blog",
  "url": "http://example.onion",
  "uses_tor": true,
  "scrape_interval_minutes": 30,
  "selectors": {
    "victim_card": ".victim-item",
    "victim_name": ".company-name",
    "date": ".publish-date"
  }
}
```

### Available Source Types

- `ransomware_blog` — Ransomware group leak sites
- `hacker_forum` — Cybercriminal forums
- `marketplace` — Dark web marketplaces
- `paste_site` — Pastebin-like services
- `telegram` — Telegram channels/groups
- `news_feed` — Cybersecurity news
- `rss` — RSS/Atom feeds
- `twitter` — Social media
- `reddit` — Subreddits
- `other` — Custom sources

### Creating a Custom Scraper

1. Create a new scraper class in `backend/scrapers/` extending `BaseScraper`
2. Implement the required methods: `scrape()`, `extract_iocs()`, `extract_leaks()`
3. Register the scraper in `backend/scrapers/__init__.py`
4. Configure the source via the API or database

## WebSocket Integration

Real-time updates are available via WebSocket:

```javascript
const token = localStorage.getItem('token');
const ws = new WebSocket(`ws://localhost:8000/ws?token=${encodeURIComponent(token)}`);

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('New update:', data);
};
```

The WebSocket broadcasts:
- New leak discoveries
- New alert creations
- Scraping status updates
- Scraping statistics (real-time)

## Initial Admin Access

There are no default credentials. The first registered account is automatically promoted to **administrator**. All subsequent registrations default to **viewer** until promoted by an existing admin.

## Scripts

| Script | Purpose |
|--------|---------|
| `setup.sh` | Install system dependencies, Docker, Tor, Python packages, Node modules |
| `start.sh` | Start development server (backend + frontend) |
| `stop.sh` | Stop development servers |
| `backend/seed.py` | Seed database with initial data |
| `scripts/scrape_tor.py` | Standalone Tor scraper script |
| `scripts/advanced_scraper.py` | Advanced scraper with circuit rotation |

## License

MIT License — see LICENSE file for details.

## Disclaimer

This tool is designed for legitimate security research and threat intelligence purposes only. Users are responsible for ensuring compliance with all applicable laws and regulations in their jurisdiction. Unauthorized access to computer systems is illegal. Always obtain proper authorization before monitoring any systems or networks.
