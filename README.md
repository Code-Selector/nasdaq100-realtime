# nasdaq100-realtime

Real-time NASDAQ-100 stock tracker with a Flask backend, MySQL persistence, and a lightweight browser dashboard.

## Features

- **Real-time quotes** — Fetches all 100 NASDAQ-100 component stocks every 60 s (configurable)
- **Market-session aware** — Detects pre-market / regular / after-hours / closed and adjusts display
- **MySQL persistence** — Snapshots and fetch logs stored in MySQL; survives restarts
- **REST API** — JSON endpoints for full list, top gainers/losers, history, and system status
- **Web dashboard** — Single-page frontend with live refresh, ranking table, and trend chart
- **CLI mode** — Terminal-based monitoring with colored output (no browser needed)

## Architecture

```
Client (Browser / CLI)
        │
        ▼
┌─────────────────────────────────────┐
│  Controller   app/api/stock_api.py  │  Flask Blueprint, REST routes
├─────────────────────────────────────┤
│  Service      app/service/          │  Business logic, stats, market session
├─────────────────────────────────────┤
│  DAO          app/dao/stock_dao.py  │  Pure SQL CRUD
├─────────────────────────────────────┤
│  Model        app/model/stock.py    │  @dataclass StockQuote + DDL
├─────────────────────────────────────┤
│  Database     app/database.py       │  DBUtils PooledDB (connection pool)
├─────────────────────────────────────┤
│  Task         app/task/scheduler.py │  Background fetch thread, in-memory cache
├─────────────────────────────────────┤
│  Config       app/config.py         │  Centralised config, env-var overrides
└─────────────────────────────────────┘
        │
        ▼
      MySQL (trader DB)
```

## Prerequisites

| Dependency | Version |
|------------|---------|
| Python     | ≥ 3.10  |
| MySQL      | ≥ 5.7   |

## Quick Start

### 1. Clone

```bash
git clone https://github.com/Java-Edge/nasdaq100-realtime.git
cd nasdaq100-realtime
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure MySQL

Create the database (tables are auto-created on startup):

```sql
CREATE DATABASE IF NOT EXISTS trader
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

Default connection: `root:123456@localhost:3306/trader`. Override via environment variables:

```bash
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=123456
export DB_NAME=trader
```

### 4. Run

**Web service** (dashboard + API):

```bash
python run.py
```

Open http://localhost:5188 in your browser.

**CLI mode** (terminal only):

```bash
python cli.py
```

## API Reference

| Method | Endpoint              | Description                     |
|--------|-----------------------|---------------------------------|
| GET    | `/api/nasdaq100`      | Full stock list with stats      |
| GET    | `/api/nasdaq100/top`  | Top 10 gainers & losers         |
| GET    | `/api/nasdaq100/history` | Recent 60 snapshot summaries |
| GET    | `/api/status`         | Service status & market session |

### Example response — `/api/nasdaq100`

```json
{
  "stocks": [
    {
      "rank": 1,
      "ticker": "NVDA",
      "name": "NVIDIA Corporation",
      "price": 135.42,
      "changePct": 3.27,
      "changeAmt": 4.29
    }
  ],
  "updatedAt": "2026-03-31 22:30:15",
  "session": { "code": "regular", "label": "盘中交易" },
  "stats": { "up": 65, "down": 33, "flat": 2, "avgChange": 0.85 },
  "fetchCount": 42
}
```

## Environment Variables

| Variable         | Default     | Description                  |
|------------------|-------------|------------------------------|
| `DB_HOST`        | `localhost` | MySQL host                   |
| `DB_PORT`        | `3306`      | MySQL port                   |
| `DB_USER`        | `root`      | MySQL username               |
| `DB_PASSWORD`    | `123456`    | MySQL password               |
| `DB_NAME`        | `trader`    | MySQL database name          |
| `PORT`           | `5188`      | Web server listen port       |
| `FETCH_INTERVAL` | `60`        | Fetch interval in seconds    |

## Project Structure

```
├── run.py                  # Web entry point
├── cli.py                  # CLI entry point
├── requirements.txt
├── app/
│   ├── config.py           # Centralised configuration
│   ├── database.py         # Connection pool (DBUtils)
│   ├── api/
│   │   └── stock_api.py    # REST controller (Blueprint)
│   ├── dao/
│   │   └── stock_dao.py    # Data access layer
│   ├── model/
│   │   └── stock.py        # Data models & DDL
│   ├── service/
│   │   ├── fetch_service.py    # Quote fetching logic
│   │   └── market_service.py   # Market session & stats
│   └── task/
│       └── scheduler.py    # Background scheduler & cache
└── front/
    ├── index.html           # Dashboard page
    ├── app.js               # Frontend logic
    └── style.css            # Styles
```

## License

[MIT](LICENSE) © 2026 JavaEdge
