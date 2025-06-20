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
    'accept-language': 'en-US,en;q=0.6',
    'referer': 'https://www.nseindia.com/option-chain',
    'sec-ch-ua': '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sec-gpc': '1',
    'priority': 'u=1, i'
}

# Cookies required for NSE API access (updated)
COOKIES = {
    'nsit': '4c4N_xWu1vOH6P8quwF1Jljk',
    'nseappid': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhcGkubnNlIiwiYXVkIjoiYXBpLm5zZSIsImlhdCI6MTc1MDQxMDkzNCwiZXhwIjoxNzUwNDE4MTM0fQ.7a_ddl9LoFIt-LguXneLDtLYFDiZufaO7zgF18pw7r4',
    'AKA_A2': 'A',
    'bm_sz': 'B775D425D53D73092BC6CBF5D456FB40~YAAQFvEBF8OoJ3uXAQAAmDifjBwzjMg8Z58HjmaX6J3uuGzylYriNnuHUEe/YHo0X16EZUewfVDtUsp8IXWHLhSdhly1+VitwxZeeW+ptjV2wfcy1Lcw/Zxb9nYdmbIXasaB9SX6J18MdeRcpF8VZ4h95MkLVaBWY9N7PdVi8jIRv8EGvNNsWi6kUAQBdCOs9zR9af3DRSeNSMcHqcTgLRSur30d1BjNG8XxKiF+i83n6IJhuNaT326Ht84oA5BZlOA+Dzhi6jU69frUT+nJZxAR2alGTCJBw5L6lTgfcCWT5MoqVV1qPRPfDRT4xS0SLhK3rv6islMgijXkRPPGIVmsGQonMnz8irAMPjfJtqqhefaG22tqqzNuB8cSJUL8hiEFdxgyd0GPy/vTQQ==~3162419~4273463',
    'ak_bmsc': 'BCD17C4049260D9126AD79C338B50DC3~000000000000000000000000000000~YAAQFvEBF/+pJ3uXAQAAcTyfjBx/l6Vxt82wh9q0Ryl79jQ0DDJ/0eqb5KxwcfpnoFr+mrV0Hq2KwCQB+SjnBFUZrjHGGhLaDwk4by1YDc0atZGz8GkHgbTl0Tn/afLy5CkYCN3rglX0gzjO31zJatLQwQlS2aIN1Dutmn5thF0X5c+074gYzX4Eu6DEX7IGC7vwIMGN2B3rzgux+Tday83ArPoWnUWdyhDK6WmsDjGqmp4Jw0B/ymhhSZXRbHqJ2D47SLdPEA8OwPusT4PV6b2t47inJ07VsjV0vJ3mADF5JgMLieR0JK4fuVz2PBnV/68sm2SMU4hagmMzW3Qv8SDQxdEapDzUx50W4y6maGA1gRcFBgwLn7iS8o4dVRQOOe+WsbDnTO8M5ScYnlgNVJDK6oncLX5B3gbIQ28ySNmTdNRI8chf/bOfWpj5q0IrL//WeI1LnvC2PZ2VFqs=',
    '_abck': 'D27189CFE81BD09F29943030E64D7B5D~0~YAAQFvEBF8usJ3uXAQAAv0WfjA47AN8RgqJO0Pw0Jbm12x6Gu6qfkYuqoyAkgPIwcal4HAONwW0WygZLfLaLB/FAVUk9XjPJI27MMn7nEhrtZ9Xx9ZmUZ+6BdU5tT7w0agiHQPHOm3i436VgdqFatr5tBNMEvceyoctKA4wAN6bVcNtc7A3Nc+gbX97lfWc1UX90v5MLWGA6Nq61WydcAsSzJCjevN1lu+uCE/VtAJYeNfv7GNgm2GT2DIm7lO3jIRcsuXj2HNy4bKifaCckhZDlq0UcHm5cwoLXTbDSPBnNuzU6LE3FG1HQQvvi1TDNOs/8P22eKlgNOAcjCj4Uhi4eyarSXAtaUATxSrkcOjhi+ShSuGnKiXZJuGdGY0vAtZs68LXXPRatxN7fgX8tk5vXP/VJTgSkd2YdA4ULQwe6sMwbN11wbc1N2genn0mXyFUvHarsayOKk6qAChvqu9O6yrLtgAZSqiV9xS2QM5iA/hEJ5mQHWePEzArsX7y8S0hQoiIteOSlPdTYlgqWHBxqQp27Wn/Jm+2kDgHeMOEtF41RDeZfmBzVtaJtisXZ2Z2uT2plJxbUShguIq8CV6VNq1ZzmvPe8nTcy7ggKp1CVccwM0S24e+CQEenRg==~-1~||0||~-1',
    'bm_sv': 'EA0F0DA7EA4C25755447E5249D212042~YAAQFvEBF+StJ3uXAQAAw0ufjByKHq2UWW9XuGDur7D/iCOzRmPVASclfMbnELYt7g8L+/kq6MYhP1Zsq6DtYt8npgnNPn2y6Kn7gAr1+koFhK2k8Cr1bOhcC77+7B+xwSlv644NZKzipE8/3TGW1AMrFhrzVVLuIvbYFPbjGhpvIHUgxblfxYh0czZUxg12yg/PqjrQDtsIrPzQPzpdHTc06YmYoMY+PMao9+pupkqyzY+lunlB9R0BgYuW2dmVPDw=~1'
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
    
    for market_state in market_data['marketState']:
        if market_state.get('index') == 'NIFTY 50':
            return {
                'index': market_state.get('index'),
                'last': market_state.get('last'),
                'change': market_state.get('variation'),
                'pChange': market_state.get('percentChange'),
                'tradeDate': market_state.get('tradeDate'),
                'market_status': market_state.get('marketStatus')
            }
    return None

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
