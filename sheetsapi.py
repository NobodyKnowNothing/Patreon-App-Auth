from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

SPREADSHEET_ID = '1ghV9kA2X-jGdGsCRcgENLs270fE7ehbvH1KppAp4Q0c'
SERVICE_ACCOUNT_FILE = 'credentials.json'
SHEET_NAME = 'Sheet1'
# --- Helper Function to Get Authenticated Service ---
def get_sheets_service():
    """Authenticates with Google Sheets API using a service account."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        return service
    except FileNotFoundError:
        print(f"Error: Service account key file not found at {SERVICE_ACCOUNT_FILE}")
        print("Please ensure 'SERVICE_ACCOUNT_FILE' variable is set correctly.")
        return None
    except Exception as e:
        print(f"An error occurred during authentication: {e}")
        return None
sheets_service = get_sheets_service()
if sheets_service:
    print("Google Sheets service authenticated successfully.")
else:
    print("Failed to authenticate Google Sheets service.")
    1/0 # Force exit if service not authenticated
# --- Core Functions ---
def write_to_cell(value, cell, service=sheets_service, spreadsheet_id=SPREADSHEET_ID, sheet_name=SHEET_NAME):
    """
    Writes a value to a specific cell.
    :param service: Authenticated Google Sheets service instance.
    :param spreadsheet_id: ID of the spreadsheet.
    :param sheet_name: Name of the sheet (e.g., 'Sheet1').
    :param cell: Cell address (e.g., 'A1', 'B5').
    :param value: The value to write.
    """
    range_name = f"{sheet_name}!{cell}"
    body = {
        'values': [[value]]  # Value needs to be in a list of lists
    }
    try:
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED', # Or 'RAW' if you don't want type conversion
            body=body
        ).execute()
        print(f"{result.get('updatedCells')} cell(s) updated in {range_name} with value: '{value}'.")
        return True
    except HttpError as error:
        print(f"An API error occurred: {error}")
        print(f"Details: {error.resp.status}, {error._get_reason()}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while writing: {e}")
        return False

def delete_cell_content(cell, service=sheets_service, spreadsheet_id=SPREADSHEET_ID, sheet_name=SHEET_NAME):
    """
    Deletes (clears) the content of a specific cell.
    :param service: Authenticated Google Sheets service instance.
    :param spreadsheet_id: ID of the spreadsheet.
    :param sheet_name: Name of the sheet (e.g., 'Sheet1').
    :param cell: Cell address (e.g., 'A1', 'B5').
    """
    range_name = f"{sheet_name}!{cell}"
    try:
        # To "delete" text, we actually clear the cell's values.
        # Alternatively, you can write an empty string:
        # write_to_cell(service, spreadsheet_id, sheet_name, cell, "")
        result = service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            body={} # Empty body for clear operation
        ).execute()
        print(f"Content cleared from cell {range_name}.")
        print(f"Cleared range: {result.get('clearedRange')}")
        return True
    except HttpError as error:
        print(f"An API error occurred: {error}")
        print(f"Details: {error.resp.status}, {error._get_reason()}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while deleting: {e}")
        return False

def read_cell_value(cell, service=sheets_service, spreadsheet_id=SPREADSHEET_ID, sheet_name=SHEET_NAME):
    """
    Reads the value from a specific cell.
    :param service: Authenticated Google Sheets service instance.
    :param spreadsheet_id: ID of the spreadsheet.
    :param sheet_name: Name of the sheet (e.g., 'Sheet1').
    :param cell: Cell address (e.g., 'A1', 'B5').
    :return: The value of the cell, or None if an error occurs or cell is empty.
    """
    range_name = f"{sheet_name}!{cell}"
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        values = result.get('values', [])
        if not values:
            print(f"No data found in {range_name}.")
            return None
        else:
            # values is a list of lists, e.g., [['Cell Value']]
            value = values[0][0]
            print(f"Value in {range_name}: '{value}'")
            return value
    except HttpError as error:
        print(f"An API error occurred: {error}")
        print(f"Details: {error.resp.status}, {error._get_reason()}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while reading: {e}")
        return None