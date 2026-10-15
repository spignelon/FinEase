# FinEase

A paper trading platform for **NIFTY index options** (NSE F&O), built on the **Angel One SmartAPI** with **live market prices**. Practise buying, selling and short selling options with ₹10 lakh of virtual cash and no real money at risk.

> **About this project:** FinEase was developed in **June 2025** as a learning project, to explore real-time market data pipelines, options trading mechanics and full-stack development with Flask, MongoDB and React. This project is **no longer maintained**.

## Screenshots

### Authentication

| Login | Register |
| :---: | :---: |
| ![Login](docs/screenshots/login.png) | ![Register](docs/screenshots/register.png) |

### Dashboard

NIFTY 50 level, portfolio P&L, available cash, holdings value and total value at a glance.

![Dashboard](docs/screenshots/dashboard.png)

### Portfolio

![Portfolio](docs/screenshots/portfolio.png)

### Options Trading

Search the NIFTY option chain and place buy/sell orders in the order panel.

![Options Trading](docs/screenshots/trading.png)

### Trade History

![Trade History](docs/screenshots/history.png)

## Features

- **Accounts**: register and log in; every new user starts with **₹10,00,000** of virtual cash.
- **Live market prices**: `streamer.py` subscribes to Angel One's SmartAPI WebSocket and streams live LTP ticks into MongoDB. Option prices and the NIFTY 50 level come straight from the market feed.
- **NIFTY option chain**: CE/PE contracts for the **3 nearest expiries**, built from Angel One's public scrip master. The master data is refreshed automatically once per day when the backend starts.
- **Search**: find contracts by symbol or strike (e.g. `22800`, `CE`).
- **Buy and sell** options in **lots**: NIFTY lot size is 75, with a flat **₹40 fee** per trade.
- **Short selling** (sell to open): reserves a fixed **₹2,00,000 margin per lot**, which is released with realised P&L when you buy to cover.
- **Portfolio**: long and short positions with live valuation, unrealised P&L and frozen margin.
- **Trade history** for every order.
- **Realistic trading mechanics**: lot sizes, margin and transaction costs modelled after the real F&O market.
- **Clean UI** built with React, TypeScript and Tailwind CSS.

## How it works

```
Angel One SmartAPI WebSocket
          │  (LTP ticks)
          ▼
     streamer.py ───────► MongoDB (ltp: last 100 ticks per token)
                                  ▲
React + Vite frontend ──REST──► Flask API (app.py) ── Angel One scrip master (daily)
```

- Market data **streams in over a WebSocket** (`streamer.py` connects to Angel One's SmartAPI feed) and is stored in MongoDB, keeping the most recent ticks for each contract.
- The Flask API reads the latest stored tick for each contract, so every quote, valuation and order fill uses the current market price.
- The React frontend talks to the API over REST.

## Setup Instructions

### Prerequisites

- Python 3 (developed and tested on 3.13)
- Node.js and npm
- MongoDB
- An [Angel One SmartAPI](https://smartapi.angelone.in/) account (only needed for live prices)

### Configuration

1. **MongoDB**: run a MongoDB instance (local install, Docker or a cloud service) with authentication.

2. Create a `.env` file in the project root:

```properties
MONGODB_URI=mongodb://your_username:your_password@localhost:27017/
```

   `app.py` reads this. `streamer.py` currently defines its own `MONGO_URI` at the top of the file, so update it to the same connection string.

3. Create a `config.py` file in the project root with your Angel One SmartAPI credentials (it is gitignored):

```python
apikey =    '*****'   # SmartAPI API key
username =  '*****'   # Angel One client code
pwd =       '*****'   # Angel One login PIN
token =     '*****'   # TOTP secret (used to generate the 2FA code)
```

4. Create `frontend/.env` pointing at the backend:

```properties
VITE_API_BASE_URL=http://127.0.0.1:5001
```

### Installation

1. Clone the repository:
```bash
git clone https://github.com/spignelon/FinEase.git
cd FinEase
```

2. Install Python dependencies (a virtual environment is recommended):
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Install frontend dependencies:
```bash
cd frontend
npm install
cd ..
```

### Running the Application

Start three components in this order:

#### 1. Backend API server
```bash
python app.py
```

Runs on `http://127.0.0.1:5001`. On startup it downloads the Angel One scrip master and fills the `master` collection, which the streamer needs.

#### 2. Market data streamer (needs a SmartAPI login; live prices only)
```bash
python streamer.py
```

Logs in to SmartAPI, subscribes to the NIFTY option contracts in the `master` collection plus the NIFTY 50 index (token `26000`), and writes live ticks to MongoDB. Start it **after** the backend so the `master` collection already exists.

#### 3. Frontend dev server
```bash
cd frontend
npm run dev
```

The app is served at `http://localhost:5173` (Vite uses the next free port if that one is taken, and prints the URL).

## API Documentation

Base URL: `http://127.0.0.1:5001`

### Authentication

Endpoints marked *Required* need the token returned by register/login in the `Authorization` header (a `Bearer ` prefix is also accepted):

```
Authorization: <user_token>
```

### Endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/register` | No | Create an account |
| POST | `/api/login` | No | Log in |
| GET | `/api/portfolio` | Required | Cash, positions, valuation, P&L |
| GET | `/api/option_chain` | No | NIFTY option chain with latest prices |
| GET | `/api/options/search` | No | Search contracts |
| POST | `/api/trade` | Required | Buy or sell |
| GET | `/api/trades` | Required | Trade history |
| GET | `/api/nifty_price` | No | Latest NIFTY 50 price |
| POST | `/api/admin/update_master_data` | Required | Force a scrip master refresh |

#### Register

`POST /api/register`

```json
{ "username": "username", "password": "password", "email": "user@example.com" }
```

Response `201`:
```json
{ "message": "User registered successfully", "token": "user_token", "user_id": "user_id", "username": "username" }
```

Errors: `400` (username exists / missing fields), `500`.

#### Login

`POST /api/login`

```json
{ "username": "username", "password": "password" }
```

Response `200`: same shape as register, with `"message": "Login successful"`.
Errors: `400` (missing fields), `401` (invalid credentials).

#### Get Portfolio

`GET /api/portfolio` (*Required*)

```json
{
  "cash": 1000000,
  "available_cash": 1000000,
  "margin_frozen": 0,
  "holdings": [
    {
      "symbol": "NIFTY19OCT2620500CE",
      "quantity": 1,
      "lot_size": 75,
      "total_units": 75,
      "price": 120.5,
      "market_value": 9037.5,
      "position_type": "long"
    }
  ],
  "long_holdings_value": 9037.5,
  "short_positions_value": 0,
  "short_positions_pnl": 0,
  "total_holdings_value": 9037.5,
  "total_portfolio_value": 1009037.5,
  "effective_portfolio_value": 1009037.5,
  "initial_portfolio_value": 1000000,
  "nifty_price": 24855.05
}
```

`quantity` is in **lots**. Short positions appear in `holdings` with a negative `quantity`, `"position_type": "short"`, `pnl` and `margin_frozen`.

#### Get Option Chain

`GET /api/option_chain`

Query parameters: `symbol` (default `NIFTY`), `expiry` (optional).

```json
{
  "options": [
    {
      "symbol": "NIFTY19OCT2620500CE",
      "formattedSymbol": "NIFTY19OCT2620500CE",
      "underlying": "NIFTY",
      "expiryDate": "19OCT26",
      "strikePrice": 20500,
      "optionType": "CE",
      "lastPrice": 120.5,
      "token": "47047"
    }
  ],
  "timestamp": "2026-10-16T01:19:50.812150",
  "count": 1
}
```

`lastPrice` is the latest streamed price for the contract.

#### Search Options

`GET /api/options/search?q=<query>`

`q` must be at least 2 characters (otherwise `400`). Returns up to 20 matches in the same shape as the option chain: `{ "options": [...], "count": n }`.

#### Execute Trade

`POST /api/trade` (*Required*)

```json
{
  "symbol": "NIFTY19OCT2620500CE",
  "quantity": 1,
  "price": 120.5,
  "order_type": "buy"
}
```

- `quantity` is the number of **lots** (NIFTY: 75 units per lot).
- `order_type` is `buy` or `sell`. A `buy` against an open short position covers it; a `sell` without a long position opens a short.
- If `price` is `0`, the latest stored LTP is used.
- Fee: flat ₹40 per trade. Opening a short reserves ₹2,00,000 margin per lot.

Response `200` (buy):
```json
{
  "status": "success",
  "message": "Successfully bought 1 lots (75 units) of NIFTY19OCT2620500CE at ₹120.50 per unit.",
  "lot_size": 75,
  "total_units": 75,
  "unit_price": 120.5,
  "total_cost": 9037.5,
  "transaction_fee": 40,
  "total_debit": 9077.5,
  "trade_id": "trade_id"
}
```

Sell/cover responses include extra fields (`margin_reserved`, `margin_released`, `realized_profit`, `net_cash_effect`) as relevant.

Errors: `400` (insufficient cash/holdings, invalid symbol, bad `order_type`), `401`, `500`. Error bodies look like `{ "status": "error", "message": "..." }`.

#### Get Trade History

`GET /api/trades?limit=50` (*Required*)

```json
{
  "trades": [
    {
      "_id": "trade_id",
      "user_id": "user_id",
      "symbol": "NIFTY19OCT2620500CE",
      "quantity": 1,
      "price": 120.5,
      "order_type": "buy",
      "timestamp": "2026-10-16T11:34:00.000000",
      "total_value": 120.5
    }
  ],
  "count": 1
}
```

`order_type` is one of `buy`, `sell`, `short_sell`, `buy_to_cover`.

#### Get NIFTY Price

`GET /api/nifty_price`

```json
{ "status": "success", "symbol": "NIFTY 50", "price": 24855.05, "timestamp": "2026-10-16T01:19:50.812150" }
```

Returns `404` if no NIFTY tick has been received yet.

#### Update Master Data

`POST /api/admin/update_master_data` (*Required*)

Re-downloads the scrip master if the stored copy isn't from today. Returns `{ "success": true|false, "message": "..." }`.

## Disclaimer

FinEase is a simulation built for learning and practice. It does not place real orders, it is not financial advice, and it is not affiliated with Angel One or NSE.

## License

Released under the [MIT License](LICENSE).
