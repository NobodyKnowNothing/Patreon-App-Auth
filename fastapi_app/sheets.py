import os
import json
from typing import Optional, Dict

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()  # This loads the variables from the .env file

USERS_SHEET = "Users"
# The cell that contains the entire JSON database object.
DATABASE_CELL = f"{USERS_SHEET}!A1"

class SheetsDB:
    def __init__(self, service, spreadsheet_id: str):
        self.service = service
        self.spreadsheet_id = spreadsheet_id

    @classmethod
    def from_env(cls) -> "SheetsDB":
        creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID", "")
        if not creds_json or not spreadsheet_id:
            raise ValueError("SheetsDB.from_env: missing GOOGLE_SERVICE_ACCOUNT_KEY or GOOGLE_SHEETS_ID")

        try:
            info = json.loads(creds_json)
            creds = Credentials.from_service_account_info(info)
            service = build("sheets", "v4", credentials=creds)
            return cls(service, spreadsheet_id)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Sheets: {e}")

    async def _get_database(self) -> Dict[str, Dict]:
        """Helper to retrieve and parse the JSON object from the sheet."""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range=DATABASE_CELL
            ).execute()
            
            values = result.get("values", [])
            if not values or not values[0]:
                return {}  # Return empty dict if the cell is empty

            json_string = values[0][0]
            return json.loads(json_string)
        except HttpError as e:
            print(f"SheetsDB._get_database error: {e}")
            return {}
        except (json.JSONDecodeError, IndexError) as e:
            print(f"SheetsDB._get_database: Failed to parse JSON from sheet: {e}")
            return {} # Return empty dict if data is corrupted or not valid JSON

    async def _write_database(self, data: Dict[str, Dict]):
        """Helper to write the updated JSON object back to the sheet."""
        try:
            body = {"values": [[json.dumps(data)]]}
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=DATABASE_CELL,
                valueInputOption="RAW",
                body=body
            ).execute()
        except HttpError as e:
            print(f"SheetsDB._write_database error: {e}")

    async def upsert_user(self, user_id: str, data: dict):
        """Adds a new user or updates an existing one in the database."""
        db = await self._get_database()
        db[str(user_id)] = data
        await self._write_database(db)

    async def delete_user(self, user_id: str):
        """Deletes a user from the database."""
        db = await self._get_database()
        user_id_str = str(user_id)
        if user_id_str in db:
            del db[user_id_str]
            await self._write_database(db)

    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Retrieves a single user's data from the database."""
        db = await self._get_database()
        return db.get(str(user_id))

    async def list_users(self) -> Dict[str, Dict]:
        """Lists all users in the database."""
        return await self._get_database()