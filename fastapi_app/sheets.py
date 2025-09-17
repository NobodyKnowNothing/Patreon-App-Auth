import os
import json
from typing import Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


USERS_SHEET = "Users"


class SheetsDB:
    def __init__(self, service, spreadsheet_id: str):
        self.service = service
        self.spreadsheet_id = spreadsheet_id

    @classmethod
    def from_env(cls) -> "SheetsDB":
        creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID", "")
        if not creds_json or not spreadsheet_id:
            # In local/dev allow in-memory fallback
            return InMemoryDB()

        try:
            info = json.loads(creds_json)
            creds = Credentials.from_service_account_info(info)
            service = build("sheets", "v4", credentials=creds)
            return cls(service, spreadsheet_id)
        except Exception as e:
            print(f"Failed to initialize Sheets: {e}")
            return InMemoryDB()

    async def upsert_user(self, user_id: str, data: dict):
        try:
            # Find existing row or append new
            range_name = f"{USERS_SHEET}!A:B"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range=range_name
            ).execute()
            
            rows = result.get("values", [])
            row_index = None
            
            for i, row in enumerate(rows):
                if row and row[0] == user_id:
                    row_index = i + 1  # 1-indexed
                    break
            
            if row_index:
                # Update existing
                range_name = f"{USERS_SHEET}!A{row_index}:B{row_index}"
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    valueInputOption="RAW",
                    body={"values": [[user_id, json.dumps(data)]]}
                ).execute()
            else:
                # Append new
                self.service.spreadsheets().values().append(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    valueInputOption="RAW",
                    body={"values": [[user_id, json.dumps(data)]]}
                ).execute()
        except HttpError as e:
            print(f"Sheets upsert error: {e}")

    async def delete_user(self, user_id: str):
        try:
            range_name = f"{USERS_SHEET}!A:B"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range=range_name
            ).execute()
            
            rows = result.get("values", [])
            for i, row in enumerate(rows):
                if row and row[0] == user_id:
                    # Clear the row (set to empty)
                    range_name = f"{USERS_SHEET}!A{i+1}:B{i+1}"
                    self.service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=range_name,
                        valueInputOption="RAW",
                        body={"values": [["", ""]]}
                    ).execute()
                    break
        except HttpError as e:
            print(f"Sheets delete error: {e}")


class InMemoryDB:
    """Fallback in-memory storage for local development"""
    def __init__(self):
        self.users = {}
    
    async def upsert_user(self, user_id: str, data: dict):
        self.users[user_id] = data
        print(f"InMemory: upserted {user_id} = {data}")
    
    async def delete_user(self, user_id: str):
        if user_id in self.users:
            del self.users[user_id]
            print(f"InMemory: deleted {user_id}")