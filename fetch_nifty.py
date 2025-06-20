import requests
import json
from datetime import datetime
import time
import db  # Import db module to save the fetched data

# NSE API URL for market status data
MARKET_STATUS_URL = "https://www.nseindia.com/api/marketStatus"

# Headers to mimic browser requests
HEADERS = {
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.8',
    'referer': 'https://www.nseindia.com/market-data/live-equity-market?symbol=NIFTY%2050',
    'sec-ch-ua': '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sec-gpc': '1',
    'priority': 'u=1, i'
}

# Cookies required for NSE API access
COOKIES = {
    'AKA_A2': 'A',
    '_abck': '9E730CD72DE80708B92D66652B40B93D~0~YAAQFvEBF2KXEXuXAQAAuhcqjA70k/FzuLBoE//ovg5+TrOkR13c8pUi7PoI3MCsJ/6tzqo2IUB9AHoHE7frQ5DSfRWEXmdal4wz8Z7BXEm94QP+n8duvpkg54+9EntGN/Uy33C8/jEeuP5jNQavg7Fuk1p+prRPMAJ6htIFJ3JvihPkZtYRGTxsYiy5TVHq02XcOqS/4fdyHo6YB5IT8mwVa4p1utzXNTy1dpFNdMEjjOKqdMmzISJfh7HgblgA3VVi5G854AIFRctYy/LIzBvrBYuTNN6K5DuB0WwYVVjIMyCqvbUmB0z/+mHToG5nF0D5w35UJuxXga0f8n04ws0EZbcfDeEEOoED2jkj7iK8z/wQUAh4fDUbERNG/H/RulEuETqjKmUmG3qH0tQzdGwNVha+Tu4JT9EmORCPI6PyHJr6U6nBrd/v71+iW4E7Sc+CMdVte/0OGzuwoSAR4ZnK3egrvAY4qCAKhgGbgdvbaTUoXT6Q+chMR+mY1fAmR5H+XTMsOp4k4Jmst6C0j5mi7ggGaRxVxnPQQ8NgSEGI8wGPc7LWD/ENx/L2R2zXOB2Glj2dBCaG7lPAcmi5gfJtuRwbLQgoaZAh+xO4WCWm+U3Uy1f74joQXnW/Sgo=~-1~-1~-1',
    'ak_bmsc': '2847A028E8134C2A2566D0ED0F317ADA~000000000000000000000000000000~YAAQFvEBF8GXEXuXAQAAoxoqjBwcKM422XzZeLNgSqZ1QMEdGkR9sDgSnofvAxqPLwKp3ICYlAjzo+tn/gR+y4umDnOL3JlplxB2RruIqvDqVGm8HyWdrDya3Nmqq2ho7Crmv9JHJia9B20eaa3i9XBvD6o9M5DjkvNItIexqdFZbdJ8kbw1R3upDkmJOTxY3A1blqnQvhiwVvDiulM+LBFHss2FrL4o3oq/DOinhrUuYFT5LoRSqKuiVVXLPrP40O430YaRmRhsKPTHzaDBnLhSHf+4kKSHNKkzKThsZmDMKziUqwd3TtJqzOe3PCJxASNgOH1Kt6Kpa56tN/r+0a+8CrDLKepV/URhxNuyxuOsRv6No7CexkY4+nZX3haQCGPLX+0TfmOMudg/iC2RxjjkEo3yDSzrU2hJ347TE8M0thhQtjdWJiYRR9nqntZw4rEOAM0SLcX1GKy10zs=',
    'nsit': 'DhQwnJdRNkxbBaKz3A_2UrcD',
    'nseappid': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhcGkubnNlIiwiYXVkIjoiYXBpLm5zZSIsImlhdCI6MTc1MDQwNDEwMiwiZXhwIjoxNzUwNDExMzAyfQ.TxraKUh2fIyvFGwpWHZN_FLaav8naMVp1SuJAK8luRM',
    'bm_sz': '9B9F38CC7DC7C000CB293B382E39A856~YAAQJPEBF6AlUXmXAQAAzPk2jByeaN+oe+A0C7l+RI/rTnWkKJBBzy08uskZZLQzkBXsbGL81oMHr75t7kjceQmoJwvyQ4YmYSmi8HKlU3DsAIvZd1y0+MC8/sIVCtxM/V9uvQOig79fGhkc7qUBkCFOcaQJl8YE5ap5d4uvbmO1ABojStkR/JVsmW+lNti2gYfW2XNlgnL811Rd/Gdls8p+m33Y/Gm2EPZr4QgOkcMcwvOhD/DjIHSW8TQlICqFIBfL9d8lOPOSMb3lBTvcfPu3iqtL/0eNB8XaHZkRuUUZ/iY6hPjQFJzOMjivv84YIvp9seQHR/zahPW6IwieOaUrkbJ1jfLkYwsVuvOdA0PggJZNHnhkjHXWV6T9RvqKfeKBEkzpJPWF4sa4hTb71qzdQacy9Q==~4272178~3229251',
    'bm_sv': 'C9656991B641012D27C1CCEE99E37E6B~YAAQJPEBFw0pUXmXAQAACRQ3jByCNZsBkaO5Lm3PAARWsNh4bTWaen2TzXiqypnMc2G1gBVR9DrrxkBeZpQQjpjfLF13gA5WwiBuax+iKS73P1Qg/nChI4uzg6zV+B7N4AAMTydqX7N35EUG2aQBsb7itxcDMpkLRGIq1vQzpw4gYKPQQtNeyfCMY7KQiKfHhmUX81apvz6TZcINCfFuKcDeoKfx2iwNSVhU3IK4/xm2HuBDISQlgoOGRG0GAFdjBSI=~1',
}

# Create a session for reusing connections
session = requests.Session()

# Update the session with the cookies
for cookie_name, cookie_value in COOKIES.items():
    session.cookies.set(cookie_name, cookie_value)

def fetch_market_data():
    """
    Fetch the latest market data from the NSE API.
    
    Returns:
        dict: The market data JSON or None if the request fails
    """
    try:
        response = session.get(MARKET_STATUS_URL, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching market data: Status code {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception while fetching market data: {str(e)}")
        return None

def extract_nifty_data(market_data):
    """
    Extract NIFTY 50 data from the market data response.
    
    Args:
        market_data (dict): The market data from the NSE API
        
    Returns:
        dict: A dictionary containing NIFTY 50 data
    """
    if not market_data or 'marketState' not in market_data:
        return None
    
    nifty_data = None
    
    for market_state in market_data['marketState']:
        if market_state.get('index') == 'NIFTY 50':
            nifty_data = {
                'index': market_state.get('index'),
                'last': market_state.get('last'),
                'change': market_state.get('variation'),
                'pChange': market_state.get('percentChange'),
                'tradeDate': market_state.get('tradeDate'),
                'market_status': market_state.get('marketStatus')
            }
            break
    
    return nifty_data

def update_market_data():
    """
    Fetch and update market data in the database.
    
    Returns:
        dict: The updated market data or None if the update failed
    """
    print(f"Fetching market data at {datetime.now()}")
    data = fetch_market_data()
    
    if data:
        # Add timestamp to the data
        data['timestamp'] = datetime.now()
        
        # Save to database
        db.save_market_data(data)
        print(f"Market data updated at {datetime.now()}")
        return data
    
    print("Failed to fetch market data")
    return None

def fetch_data_periodically(interval_seconds=60):
    """
    Start a continuous loop to fetch market data periodically.
    
    Args:
        interval_seconds (int): The interval between fetches in seconds
    """
    while True:
        update_market_data()
        time.sleep(interval_seconds)

# For testing the module directly
if __name__ == "__main__":
    data = update_market_data()
    if data:
        nifty_data = extract_nifty_data(data)
        print("NIFTY 50 Data:")
        print(json.dumps(nifty_data, indent=4))
    else:
        print("Failed to fetch market data")
