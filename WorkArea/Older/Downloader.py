import requests
import os
import sys
import io
import pandas as pd # Used for validation and better error checking
import re # Added for clean filename extraction

# --- Configuration for NSE ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/555.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/555.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

def extract_params_and_create_filename(url: str):
    """
    Extracts symbol, from/to dates from the URL and constructs the filename
    in the format: DD-MM-YYYY-TO-DD-MM-YYYY-<SYMBOL>-EQ-N.csv.
    """
    
    # Defaults in case of missing parameters
    symbol = "UNKNOWN"
    from_date = "START-DATE"
    to_date = "END-DATE"
    
    try:
        # Extract symbol
        symbol_match = re.search(r'symbol=([A-Z0-9]+)', url)
        if symbol_match:
            symbol = symbol_match.group(1).upper()
        
        # Extract 'from' date (DD-MM-YYYY)
        from_match = re.search(r'from=(\d{2}-\d{2}-\d{4})', url)
        if from_match:
            from_date = from_match.group(1)
        
        # Extract 'to' date (DD-MM-YYYY)
        to_match = re.search(r'to=(\d{2}-\d{2}-\d{4})', url)
        if to_match:
            to_date = to_match.group(1)
            
    except Exception as e:
        print(f"Warning: Could not fully parse URL parameters. Using defaults. Error: {e}")

    # Construct the filename using the user-specified format
    # We include '-EQ-N' as it's common for historical NSE delivery data.
    local_filename = f"{from_date}-TO-{to_date}-{symbol}-EQ-N.csv"
    
    return local_filename

def download_nse_csv(download_url: str, local_filename: str):
    """
    Downloads a CSV file from the NSE historical data API endpoint.

    This version handles the NSE's required session cookies and also
    correctly processes the UTF-8 Byte Order Mark (BOM).

    Args:
        download_url (str): The specific NSE API URL for CSV download.
        local_filename (str): The name to save the downloaded file as.
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    print(f"--- Starting NSE CSV Download ---")
    print(f"Target URL: {download_url}")
    print(f"Output File: {local_filename}")

    try:
        # Step 1: Hit the main page to get initial session cookies (CRITICAL for NSE)
        print("1. Establishing session and fetching initial cookies...")
        session.get("https://www.nseindia.com/", timeout=15)

        # Step 2: Make the final request for the CSV file
        print("2. Requesting CSV data with active session...")
        response = session.get(download_url, timeout=30)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # --- CRITICAL FIX: Decode content with 'utf-8-sig' to strip the BOM (ï»¿) ---
        response_text = response.content.decode('utf-8-sig').strip()
        
        # Step 3: Check if the response is actually CSV data
        # Check for common CSV headers to ensure we got data, not an error page
        if not (response_text.lower().startswith('"symbol') or response_text.lower().startswith('symbol')):
            # If the output starts with an error message (like "No data found")
            if "no data found" in response_text.lower():
                 print(f"Error: Download failed. NSE reported 'No data found' for the specified parameters.")
            else:
                 print(f"Error: Download failed. The response was not a recognized CSV format.")
            print("Response snippet (first 200 chars):")
            print(response_text[:200].replace('\n', ' '))
            return

        # Optional: Use Pandas for validation before saving
        df = pd.read_csv(io.StringIO(response_text))
        
        if df.empty:
            print("Warning: CSV file downloaded successfully but it appears to be empty.")
            return

        # Step 4: Save the content using the specified filename
        with open(local_filename, 'w', encoding='utf-8') as f:
            f.write(response_text)

        print(f"\n3. Success! Data downloaded and saved to: {local_filename}")
        print(f"Total records retrieved: {len(df)}")
        print(f"The file is saved in the same directory where you ran this script.")

    except requests.exceptions.HTTPError as errh:
        print(f"\nError: HTTP Error - Check if the URL dates are valid or if the symbol is correct: {errh}")
    except requests.exceptions.RequestException as err:
        print(f"\nError: Something went wrong during the request: {err}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")


# ---------------------------- ENTRY POINT ----------------------------

if __name__ == "__main__":
    # Example URL for the script to use
    NSE_DOWNLOAD_URL = "https://www.nseindia.com/api/historicalOR/generateSecurityWiseHistoricalData?from=01-01-2021&to=14-01-2021&symbol=DIXON&type=priceVolumeDeliverable&series=EQ&csv=true"
    
    # Construct the filename using the user-specified format
    OUTPUT_FILE = extract_params_and_create_filename(NSE_DOWNLOAD_URL)

    download_nse_csv(NSE_DOWNLOAD_URL, OUTPUT_FILE)