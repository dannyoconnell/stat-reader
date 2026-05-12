import os
# pyrefly: ignore [missing-import]
import gspread
# pyrefly: ignore [missing-import]
from google.oauth2.service_account import Credentials
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
import json

load_dotenv()

# Set up scopes for Google Sheets and Google Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_client():
    """
    Authenticate and return a gspread client.
    Tries to load from a raw JSON string first (for cloud deployment),
    then falls back to a file path (for local development).
    """
    # 1. Try to load from raw JSON string (Cloud Deployment)
    creds_json_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json_str:
        try:
            creds_info = json.loads(creds_json_str)
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            return gspread.authorize(creds)
        except json.JSONDecodeError:
            raise ValueError("GOOGLE_CREDENTIALS_JSON is set but contains invalid JSON.")

    # 2. Try to load from file path (Local Development)
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not os.path.exists(creds_path):
        raise ValueError(
            "Neither GOOGLE_CREDENTIALS_JSON nor GOOGLE_APPLICATION_CREDENTIALS are set correctly. Please check your setup."
        )
    
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client

def get_worksheet_names(sheet_url):
    """
    Returns a list of all worksheet (tab) names in the given Google Sheet.
    """
    if not sheet_url:
        return []
        
    client = get_client()
    
    try:
        if "docs.google.com" in sheet_url:
            spreadsheet = client.open_by_url(sheet_url)
        else:
            spreadsheet = client.open_by_key(sheet_url)
            
        return [ws.title for ws in spreadsheet.worksheets()]
    except Exception as e:
        print(f"Error fetching worksheets: {e}")
        return []

def upload_stats(game_name, player_name, stats, sheet_url, worksheet_name):
    """
    Uploads player stats to a Google Sheet.
    game_name: Name of the game (e.g., 'Rocket League')
    player_name: The player's name
    stats: Dictionary of stats extracted by Gemini
    sheet_url: The URL or ID of the Google Sheet to write to
    worksheet_name: The specific tab to deposit the stats into
    """
    client = get_client()
    
    # Open the spreadsheet
    # If the user provides a full URL, gspread can parse it
    if "docs.google.com" in sheet_url:
        spreadsheet = client.open_by_url(sheet_url)
    else:
        spreadsheet = client.open_by_key(sheet_url)
        
    # Try to open the specified worksheet
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        # Fallback to the first worksheet if a specific one isn't found
        worksheet = spreadsheet.get_worksheet(0)
        
    # Get the headers from the first row to align our data
    headers = worksheet.row_values(1)
    
    if not headers:
        # If the sheet is empty, create headers based on the stats dict
        headers = ["Date", "Game", "PlayerName"] + list(stats.keys())
        # Remove duplicates from stats.keys() if 'PlayerName' is already there
        if "PlayerName" in headers[3:]:
            headers.remove("PlayerName")
            
        worksheet.append_row(headers)
    
    import datetime
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Build the row to append
    row_to_append = []
    for header in headers:
        if header.lower() == "date":
            row_to_append.append(date_str)
        elif header.lower() == "game":
            row_to_append.append(game_name)
        elif header.lower() == "playername":
            row_to_append.append(player_name)
        else:
            # Try to match the header with a key in the stats dictionary
            # Match case-insensitively
            stat_value = ""
            for key, val in stats.items():
                if key.lower() == header.lower():
                    stat_value = val
                    break
            row_to_append.append(stat_value)
            
    # Instead of appending to the bottom, overwrite row 2
    worksheet.update(values=[row_to_append], range_name='A2')
    
    # Clear any old stats below row 2 to ensure there is exactly one stat line at a time
    worksheet.batch_clear(['A3:Z1000'])
    
    return True
