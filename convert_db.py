import json
import os
from sheetsapi import read_cell_value, write_to_cell, delete_cell_content

def convert_patron_data():
    print("Attempting to convert patron data...")
    try:
        # Read the old data from A1
        old_data_str = read_cell_value('A1')
        if not old_data_str:
            print("No old data found in A1. Exiting conversion.")
            return

        old_patrons = json.loads(old_data_str)
        if not isinstance(old_patrons, dict):
            print("Old data is not a dictionary. Exiting conversion.")
            return

        new_patrons = {}
        for user_id, user_data in old_patrons.items():
            # Assuming user_data is {'name': 'username'}
            # If the old data had user_id as key and full_name as value, then user_data would be the full_name string.
            # We need to handle both cases. If user_data is a dict, extract 'name'. Otherwise, use user_data directly.
            if isinstance(user_data, dict) and 'name' in user_data:
                username = user_data['name']
            else:
                # Fallback for cases where old data might have been just {'user_id': 'username'}
                # This is a best guess, as the original prompt implies user_id was the key and {'name': 'username'} was the value.
                username = str(user_data) # Convert whatever it is to a string for the new key
            
            new_patrons[username] = {"name": username}

        # Clear the old data in A1 and write the new data
        delete_cell_content('A1')
        write_to_cell(json.dumps(new_patrons), 'A1')
        print("Patron data converted successfully!")

    except Exception as e:
        print(f"An error occurred during conversion: {e}")

if __name__ == '__main__':
    # This script needs to be run in an environment where sheetsapi can authenticate.
    # Ensure GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is set.
    convert_patron_data()


