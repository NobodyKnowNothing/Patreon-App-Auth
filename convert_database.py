#!/usr/bin/env python3
"""
Database Conversion Script for Patreon Authentication Backend

This script converts the old database format (user_id as key) to the new format (username as key).

Old format:
{
    "user_id_1": {"name": "Full Name 1"},
    "user_id_2": {"name": "Full Name 2"}
}

New format:
{
    "username_1": {"user_id": "user_id_1", "full_name": "Full Name 1"},
    "username_2": {"user_id": "user_id_2", "full_name": "Full Name 2"}
}

Requirements:
- PATREON_ACCESS_TOKEN environment variable must be set with a valid Patreon API access token
- The token must have permissions to read user data
"""

import os
import json
import requests
import logging
from sheetsapi import read_cell_value, write_to_cell, delete_cell_content
import time

# --- Configuration ---
PATREON_ACCESS_TOKEN = os.environ.get("PATREON_ACCESS_TOKEN")
PATREON_API_BASE = "https://www.patreon.com/api/oauth2/v2"

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_user_username_from_patreon(user_id: str) -> str | None:
    """
    Fetches the username for a given user_id from the Patreon API.
    
    Args:
        user_id: The Patreon user ID
        
    Returns:
        The username if found, None otherwise
    """
    if not PATREON_ACCESS_TOKEN:
        logging.error("PATREON_ACCESS_TOKEN environment variable not set")
        return None
    
    headers = {
        'Authorization': f'Bearer {PATREON_ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # Fetch user data with social connections to get username
    url = f"{PATREON_API_BASE}/user/{user_id}"
    params = {
        'fields[user]': 'full_name,social_connections'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        user_data = data.get('data', {})
        attributes = user_data.get('attributes', {})
        
        # Extract username from social connections
        social_connections = attributes.get('social_connections', {})
        patreon_connection = social_connections.get('patreon', {})
        username = patreon_connection.get('user_name')
        
        if username:
            logging.info(f"Found username '{username}' for user_id '{user_id}'")
            return username
        else:
            logging.warning(f"No username found for user_id '{user_id}'")
            return None
            
    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed for user_id '{user_id}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error fetching username for user_id '{user_id}': {e}")
        return None

def load_old_format_data() -> dict:
    """
    Loads the old format data from the Google Sheet.
    
    Returns:
        Dictionary in old format or empty dict if error
    """
    try:
        data_str = read_cell_value('A1')
        if not data_str:
            logging.info("No data found in cell A1")
            return {}
        
        data = json.loads(data_str)
        if not isinstance(data, dict):
            logging.error("Data in A1 is not a dictionary")
            return {}
        
        logging.info(f"Loaded {len(data)} entries from old format")
        return data
        
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON from cell A1: {e}")
        return {}
    except Exception as e:
        logging.error(f"Unexpected error loading old format data: {e}")
        return {}

def save_new_format_data(new_data: dict) -> bool:
    """
    Saves the new format data to the Google Sheet.
    
    Args:
        new_data: Dictionary in new format
        
    Returns:
        True if successful, False otherwise
    """
    try:
        delete_cell_content('A1')
        new_data_str = json.dumps(new_data, indent=2)
        write_to_cell(new_data_str, 'A1')
        logging.info(f"Saved {len(new_data)} entries in new format")
        return True
        
    except Exception as e:
        logging.error(f"Failed to save new format data: {e}")
        return False

def backup_old_data(old_data: dict) -> bool:
    """
    Creates a backup of the old data in cell B1.
    
    Args:
        old_data: Dictionary in old format
        
    Returns:
        True if successful, False otherwise
    """
    try:
        backup_str = json.dumps(old_data, indent=2)
        write_to_cell(backup_str, 'B1')
        logging.info("Created backup of old data in cell B1")
        return True
        
    except Exception as e:
        logging.error(f"Failed to create backup: {e}")
        return False

def convert_database():
    """
    Main conversion function that transforms old format to new format.
    """
    logging.info("Starting database conversion...")
    
    # Check if access token is available
    if not PATREON_ACCESS_TOKEN:
        logging.error("PATREON_ACCESS_TOKEN environment variable must be set")
        logging.error("Please set it to a valid Patreon API access token with user read permissions")
        return False
    
    # Load old format data
    old_data = load_old_format_data()
    if not old_data:
        logging.info("No data to convert or failed to load data")
        return False
    
    # Create backup
    if not backup_old_data(old_data):
        logging.error("Failed to create backup. Aborting conversion.")
        return False
    
    # Convert to new format
    new_data = {}
    failed_conversions = []
    
    for user_id, user_info in old_data.items():
        logging.info(f"Converting user_id: {user_id}")
        
        # Get username from Patreon API
        username = get_user_username_from_patreon(user_id)
        
        if username:
            # Extract full_name from old format (was stored as "name")
            full_name = user_info.get("name", "Unknown")
            
            # Create new format entry
            new_data[username] = {
                "user_id": user_id,
                "full_name": full_name
            }
            
            logging.info(f"Successfully converted user_id '{user_id}' to username '{username}'")
        else:
            failed_conversions.append(user_id)
            logging.warning(f"Failed to convert user_id '{user_id}' - username not found")
        
        # Add a small delay to avoid hitting API rate limits
        time.sleep(0.5)
    
    # Report results
    logging.info(f"Conversion completed:")
    logging.info(f"  - Successfully converted: {len(new_data)} entries")
    logging.info(f"  - Failed conversions: {len(failed_conversions)} entries")
    
    if failed_conversions:
        logging.warning(f"Failed to convert the following user_ids: {failed_conversions}")
        logging.warning("These entries will be lost in the conversion.")
        
        # Ask for confirmation if there are failures
        response = input(f"\\nWarning: {len(failed_conversions)} entries could not be converted and will be lost.\\nDo you want to proceed? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            logging.info("Conversion cancelled by user")
            return False
    
    # Save new format data
    if save_new_format_data(new_data):
        logging.info("Database conversion completed successfully!")
        logging.info(f"Old data backed up in cell B1")
        logging.info(f"New data saved in cell A1")
        return True
    else:
        logging.error("Failed to save converted data")
        return False

def verify_conversion():
    """
    Verifies that the conversion was successful by checking the new format data.
    """
    logging.info("Verifying conversion...")
    
    try:
        data_str = read_cell_value('A1')
        if not data_str:
            logging.error("No data found in cell A1 after conversion")
            return False
        
        data = json.loads(data_str)
        
        # Check if it's in the new format
        for key, value in data.items():
            if not isinstance(value, dict):
                logging.error(f"Entry '{key}' is not a dictionary")
                return False
            
            if 'user_id' not in value or 'full_name' not in value:
                logging.error(f"Entry '{key}' missing required fields (user_id, full_name)")
                return False
        
        logging.info(f"Verification successful: {len(data)} entries in correct new format")
        return True
        
    except Exception as e:
        logging.error(f"Verification failed: {e}")
        return False

if __name__ == "__main__":
    print("Patreon Database Conversion Script")
    print("=" * 40)
    print()
    print("This script will convert your database from the old format (user_id as key)")
    print("to the new format (username as key).")
    print()
    print("Requirements:")
    print("- PATREON_ACCESS_TOKEN environment variable must be set")
    print("- The token must have permissions to read user data")
    print()
    
    if not PATREON_ACCESS_TOKEN:
        print("ERROR: PATREON_ACCESS_TOKEN environment variable not set!")
        print("Please set it and run the script again.")
        exit(1)
    
    print("Starting conversion...")
    print()
    
    success = convert_database()
    
    if success:
        print()
        print("Verifying conversion...")
        if verify_conversion():
            print("✓ Conversion completed and verified successfully!")
        else:
            print("✗ Conversion completed but verification failed")
            print("Please check the data manually")
    else:
        print("✗ Conversion failed")
        print("Check the logs above for details")

