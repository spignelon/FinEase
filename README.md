# FinEase

A paper trading application for options trading with real-time market data from NSE.

## Setup Instructions

### Prerequisites

- Python 3.7 or higher
- Node.js and npm
- MongoDB (for database)

### Configuration

1. **MongoDB Setup**: Set up a MongoDB instance with authentication:
   - Install MongoDB locally or use a cloud service
   - Create a database user with admin privileges
   - Note down the username and password

2. Create a `.env` file in the root directory with your MongoDB connection:

```properties
MONGODB_URI=mongodb://your_username:your_password@localhost:27017/
```

Replace `your_username` and `your_password` with your MongoDB credentials.

3. Create a `config.py` file in the root directory with your Angel One SmartAPI credentials:

```python
apikey =    '*****'
username =  '*****'
pwd =       '*****'
token =     '*****'
```

Replace the `*****` placeholders with your actual Angel One SmartAPI credentials.

### Installation

1. Clone the repository:
```bash
git clone https://github.com/spignelon/FinEase.git
cd FinEase
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install frontend dependencies:
```bash
cd frontend
npm install
cd ..
```

### Running the Application

To run the complete application, you need to start three components in the following order:

#### 1. Start the Market Data Streamer
```bash
python streamer.py
```

This service connects to Angel One's SmartAPI and streams live market data to MongoDB.

#### 2. Start the Backend API Server
```bash
python app.py
```

#### 3. Start the Frontend Development Server
```bash
cd frontend
npm run dev
```

The application will be available at:
- Frontend: `http://localhost:5173` (or the port shown in terminal)
- Backend API: `http://localhost:5000` (or the port configured in your app)

## API Documentation

### Authentication

Most endpoints require authentication using a token. Include the token in the request header:

```
Authorization: <user_token>
```

The token is obtained after registration or login.

### Endpoints

#### User Registration

Register a new user account.

- **URL**: `/api/register`
- **Method**: `POST`
- **Authentication**: None
- **Request Body**:
  ```json
  {
    "username": "username",
    "password": "password",
    "email": "user@example.com"
  }
  ```
- **Response**:
  ```json
  {
    "message": "User registered successfully",
    "token": "user_token",
    "user_id": "user_id",
    "username": "username"
  }
  ```
- **Status Codes**:
  - `201`: User created successfully
  - `400`: Username already exists or missing required fields
  - `500`: Registration failed

#### User Login

Authenticate a user and get an access token.

- **URL**: `/api/login`
- **Method**: `POST`
- **Authentication**: None
- **Request Body**:
  ```json
  {
    "username": "username",
    "password": "password"
  }
  ```
- **Response**:
  ```json
  {
    "message": "Login successful",
    "token": "user_token",
    "user_id": "user_id",
    "username": "username"
  }
  ```
- **Status Codes**:
  - `200`: Login successful
  - `401`: Invalid username or password
  - `400`: Missing username or password

#### Get Portfolio

Get the user's current portfolio data.

- **URL**: `/api/portfolio`
- **Method**: `GET`
- **Authentication**: Required
- **Response**:
  ```json
  {
    "cash": 1000000,
    "holdings": [
      {
        "symbol": "NIFTY 19JUN25 22800 CE",
        "quantity": 10,
        "price": 120.5,
        "market_value": 1205
      }
    ],
    "total_holdings_value": 1205,
    "total_portfolio_value": 1001205,
    "nifty_price": 23450.75
  }
  ```
- **Status Codes**:
  - `200`: Success
  - `401`: Authentication failed

#### Get Option Chain

Get the latest option chain data.

- **URL**: `/api/option_chain`
- **Method**: `GET`
- **Authentication**: None
- **Query Parameters**:
  - `symbol` (optional): Index symbol (default: "NIFTY")
  - `expiry` (optional): Expiry date
- **Response**:
  ```json
  {
    "options": [
      {
        "underlying": "NIFTY",
        "expiryDate": "19-Jun-2025",
        "strikePrice": 22800,
        "optionType": "CE",
        "lastPrice": 120.5,
        "formattedSymbol": "NIFTY 19JUN25 22800 CE",
        "...": "additional option data"
      }
    ],
    "timestamp": "2023-06-19T12:00:00.000Z",
    "count": 1
  }
  ```
- **Status Codes**:
  - `200`: Success

#### Search Options

Search for options by query string.

- **URL**: `/api/options/search`
- **Method**: `GET`
- **Authentication**: None
- **Query Parameters**:
  - `q`: Search query (minimum 2 characters)
- **Response**:
  ```json
  {
    "options": [
      {
        "underlying": "NIFTY", 
        "expiryDate": "19-Jun-2025",
        "strikePrice": 22800,
        "optionType": "CE",
        "lastPrice": 120.5,
        "formattedSymbol": "NIFTY 19JUN25 22800 CE",
        "...": "additional option data"
      }
    ],
    "count": 1
  }
  ```
- **Status Codes**:
  - `200`: Success
  - `400`: Query too short

#### Execute Trade

Execute a buy or sell order.

- **URL**: `/api/trade`
- **Method**: `POST`
- **Authentication**: Required
- **Request Body**:
  ```json
  {
    "symbol": "NIFTY 19JUN25 22800 CE",
    "quantity": 10,
    "price": 120.5,
    "order_type": "buy"
  }
  ```
- **Response (Success)**:
  ```json
  {
    "status": "success",
    "message": "Successfully bought 10 shares of NIFTY 19JUN25 22800 CE at $120.50 each.",
    "total_cost": 1214.53,
    "transaction_fee": 9.03,
    "trade_id": "trade_id"
  }
  ```
- **Response (Error)**:
  ```json
  {
    "status": "error",
    "message": "Error message describing the issue"
  }
  ```
- **Status Codes**:
  - `200`: Trade executed successfully
  - `400`: Insufficient funds/shares or invalid symbol
  - `401`: Authentication failed
  - `500`: Unexpected error

#### Get Trade History

Get the user's trade history.

- **URL**: `/api/trades`
- **Method**: `GET`
- **Authentication**: Required
- **Query Parameters**:
  - `limit` (optional): Maximum number of trades to return (default: 50)
- **Response**:
  ```json
  {
    "trades": [
      {
        "_id": "trade_id",
        "user_id": "user_id",
        "symbol": "NIFTY 19JUN25 22800 CE",
        "quantity": 10,
        "price": 120.5,
        "order_type": "buy",
        "timestamp": "2023-06-19T12:00:00.000Z",
        "total_value": 1205
      }
    ],
    "count": 1
  }
  ```
- **Status Codes**:
  - `200`: Success
  - `401`: Authentication failed

#### Get Market Data

Get the latest market data.

- **URL**: `/api/market_data`
- **Method**: `GET`
- **Authentication**: None
- **Response**:
  ```json
  {
    "_id": "data_id",
    "marketState": [
      {
        "index": "NIFTY 50",
        "last": 23450.75,
        "...": "additional market data"
      }
    ],
    "timestamp": "2023-06-19T12:00:00.000Z"
  }
  ```
- **Status Codes**:
  - `200`: Success
  - `404`: No market data available