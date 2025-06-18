import json
import requests
from datetime import datetime
import pytz

class NiftyDataProcessor:
    """
    A class to fetch, process, and filter NIFTY options data from a given URL.
    It identifies the three closest future expiry dates and extracts relevant information.
    """

    def __init__(self, url):
        """
        Initializes the NiftyDataProcessor with the data source URL.

        Args:
            url (str): The URL to fetch the JSON scrip master data from.
        """
        self.url = url
        self.raw_data = None
        self.ist_timezone = pytz.timezone('Asia/Kolkata')
        self.columns_to_extract = ["symbol", "name", "expiry", "lotsize", "exch_seg"]

    def fetch_data(self):
        """
        Fetches raw JSON data from the specified URL.

        Returns:
            bool: True if data was fetched successfully, False otherwise.
        """
        try:
            print(f"Fetching data from: {self.url}")
            response = requests.get(self.url)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
            self.raw_data = response.json()
            print("Data fetched successfully.")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from the URL: {e}")
            self.raw_data = None
            return False
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response: {e}")
            self.raw_data = None
            return False
        except Exception as e:
            print(f"An unexpected error occurred during data fetch: {e}")
            self.raw_data = None
            return False

    def _parse_expiry_date(self, expiry_str):
        """
        Parses an expiry date string (DDMMMYYYY) into a datetime.date object.

        Args:
            expiry_str (str): The expiry date string (e.g., "19JUN2025").

        Returns:
            datetime.date or None: The parsed date object, or None if parsing fails.
        """
        if expiry_str and len(expiry_str) == 9:
            try:
                return datetime.strptime(expiry_str, '%d%b%Y').date()
            except (ValueError, IndexError):
                return None
        return None

    def get_filtered_nifty_data(self):
        """
        Processes the fetched data to filter for NIFTY NFO instruments and
        identifies the three closest future expiry dates.

        Returns:
            list: A list of dictionaries, each representing a filtered NIFTY instrument,
                  formatted as JSON. Returns an empty list if no data is available
                  or no matches are found.
        """
        if self.raw_data is None:
            print("No raw data available. Please call fetch_data() first.")
            return []

        # Get current IST date
        now_utc = datetime.utcnow()
        now_ist = now_utc.replace(tzinfo=pytz.utc).astimezone(self.ist_timezone)
        current_date_ist = now_ist.date()

        valid_nifty_nfo_items_with_dates = []

        for item in self.raw_data:
            # First, apply the "exch_seg" and "name" filters
            if item.get("exch_seg") == "NFO" and item.get("name") == "NIFTY":
                expiry_date_obj = self._parse_expiry_date(item.get("expiry"))

                if expiry_date_obj and expiry_date_obj >= current_date_ist:
                    valid_nifty_nfo_items_with_dates.append({
                        "item": item,
                        "expiry_date_obj": expiry_date_obj
                    })

        # Get a sorted list of unique expiry dates from the valid items
        unique_expiry_dates = sorted(list(set([d["expiry_date_obj"] for d in valid_nifty_nfo_items_with_dates])))

        # Select the top 3 closest unique expiry dates
        # If there are fewer than 3 unique dates, it will take all available
        closest_3_expiry_dates = unique_expiry_dates[:3]
        # print(f"Closest 3 expiry dates identified: {closest_3_expiry_dates}") # For debugging

        final_filtered_nifty_data = []

        # Iterate through the initially filtered items (with parsed dates)
        # and add them to the final list if their expiry date matches one of the closest 3 unique dates
        for entry in valid_nifty_nfo_items_with_dates:
            if entry["expiry_date_obj"] in closest_3_expiry_dates:
                # Extract only the desired columns for the final JSON output
                extracted_item = {col: entry["item"].get(col, "N/A") for col in self.columns_to_extract}
                final_filtered_nifty_data.append(extracted_item)

        # Sort the final list of dictionaries by their expiry date.
        final_filtered_nifty_data.sort(key=lambda x: self._parse_expiry_date(x['expiry']))

        return final_filtered_nifty_data

# --- Main execution block ---
if __name__ == "__main__":
    data_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    processor = NiftyDataProcessor(data_url)

    if processor.fetch_data():
        filtered_results = processor.get_filtered_nifty_data()
        json_output = json.dumps(filtered_results, indent=4)
        print("\n--- Filtered NIFTY Data (JSON Output) ---")
        print(json_output)
    else:
        print("\nFailed to process NIFTY data.")

