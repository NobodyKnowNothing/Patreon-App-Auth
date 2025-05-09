import os
import json
import hashlib
import hmac
import logging
from flask import Flask, request, jsonify, abort
from sheetsapi import write_to_cell, delete_cell_content, read_cell_value
from werkzeug.exceptions import HTTPException
# --- Configuration ---
PATREON_WEBHOOK_SECRET = os.environ.get("PATREON_WEBHOOK_SECRET")

if not PATREON_WEBHOOK_SECRET:
    logging.error("CRITICAL: PATREON_WEBHOOK_SECRET is not configured. Webhook verification will fail.")
    
PATRONS_FILE = "Google Sheet" 

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Patron Storage Functions ---

def load_patrons() -> dict:
    """Loads the dictionary of active patron User IDs and their data (name) from the JSON file."""
    try:
        patrons_data = json.load(read_cell_value('A1'))  # Assuming this function reads from a Google Sheet or similar
        if not isinstance(patrons_data, dict):
            logging.warning(
                f"'{PATRONS_FILE}' does not contain a dictionary as expected. "
                "Starting with an empty patron list. Old data (if any) is not migrated."
            )
            return {}
        return patrons_data
    except FileNotFoundError:
        logging.info(f"'{PATRONS_FILE}' not found. Starting with an empty patron list.")
        return {}
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from '{PATRONS_FILE}'. Returning an empty patron list.")
        # Consider backing up the corrupted file here
        return {}
    except Exception as e:
        logging.error(f"Unexpected error loading patrons file '{PATRONS_FILE}': {e}")
        return {}

def save_patrons(patrons_dict: dict):
    """Saves the dictionary of active patron User IDs and their data to the JSON file."""
    try:
        delete_cell_content('A1')  # Assuming this function clears the content of a Google Sheet cell
        patrons_json_str = json.dumps(patrons_dict)
        write_to_cell(patrons_json_str, 'A1')  # Assuming this function writes to a Google Sheet or similar
        logging.info(f"Saved {len(patrons_dict)} patrons to '{PATRONS_FILE}'.")
    except IOError as e:
        logging.error(f"IOError saving patrons file '{PATRONS_FILE}': {e}")
    except Exception as e:
        logging.error(f"Unexpected error saving patrons to '{PATRONS_FILE}': {e}")

# --- Webhook Verification ---

def verify_patreon_signature(signature, message_body):
    """Verifies the signature of the incoming Patreon webhook request."""
    if not PATREON_WEBHOOK_SECRET:
        logging.error("Webhook secret (PATREON_WEBHOOK_SECRET) is not configured. Cannot verify signature.")
        return False
    if not signature:
        logging.warning("Request missing X-Patreon-Signature header.")
        return False

    expected_signature = hmac.new(
        PATREON_WEBHOOK_SECRET.encode('utf-8'),
        message_body,
        hashlib.md5
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)

# --- Helper Function to Extract User Name ---
def _find_user_name_in_included(payload: dict, user_id: str) -> str | None:
    """
    Finds user's full_name from the 'included' array in the webhook payload.
    Patreon API v2 typically includes related resources like 'user' here
    if requested during webhook setup (e.g., include=user).
    """
    if not user_id:
        return None
    included_data = payload.get('included', [])
    for item in included_data:
        if item.get('type') == 'user' and item.get('id') == user_id:
            return item.get('attributes', {}).get('full_name')
    logging.debug(f"User name for User ID {user_id} not found in 'included' data.")
    return None

# --- Custom Error Handling for JSON Responses ---
@app.errorhandler(HTTPException)
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    response = e.get_response()
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response

# --- Webhook Endpoint ---

@app.route('/webhook', methods=['POST'])
def patreon_webhook():
    logging.info("Received request on /webhook")

    signature = request.headers.get('X-Patreon-Signature')
    raw_body = request.data

    if not verify_patreon_signature(signature, raw_body):
        logging.warning("Webhook signature verification failed.")
        abort(401, description="Signature verification failed.")

    event_type = request.headers.get('X-Patreon-Event')
    if not event_type:
        logging.warning("Request missing X-Patreon-Event header.")
        abort(400, description="Missing X-Patreon-Event header.")

    logging.info(f"Processing event type: {event_type}")

    try:
        payload = request.get_json()
        if not payload:
            logging.error("Failed to parse JSON payload or payload is empty.")
            abort(400, description="Invalid JSON payload.")
    except Exception as e:
        logging.error(f"Error parsing webhook JSON payload: {e}")
        abort(400, description="Could not parse JSON payload.")

    try:
        current_patrons = load_patrons()
        patrons_changed = False

        member_data = payload.get('data', {})
        primary_user_id = member_data.get('relationships', {}).get('user', {}).get('data', {}).get('id')

        if event_type in ['members:pledge:create', 'members:pledge:update']:
            if not primary_user_id:
                logging.warning(f"Could not extract User ID from {event_type} event payload. Relationships: {json.dumps(payload.get('data', {}).get('relationships', {}))}")
            else:
                patron_status = member_data.get('attributes', {}).get('patron_status')
                user_name = _find_user_name_in_included(payload, primary_user_id)

                if patron_status == 'active_patron':
                    if user_name:
                        patron_entry = {"name": user_name}
                        if current_patrons.get(primary_user_id) != patron_entry:
                            logging.info(f"Pledge active for User ID: {primary_user_id}, Name: {user_name}. Adding/Updating patron.")
                            current_patrons[primary_user_id] = patron_entry
                            patrons_changed = True
                        else:
                            logging.info(f"Pledge active for User ID: {primary_user_id}, Name: {user_name}. Data unchanged, no update needed.")
                    else:
                        # Active patron, but name couldn't be found in this payload's 'included' data.
                        logging.warning(
                            f"User ID {primary_user_id} has 'active_patron' status but name could not be extracted from 'included' data. "
                            "Ensure webhook is configured to include user details (e.g., `fields[user]=full_name&include=user`)."
                        )
                        if primary_user_id not in current_patrons:
                            logging.warning(f"User ID {primary_user_id} (active, name unknown) is not in current patrons. Not adding without name.")
                        else:
                            # Already in patrons, and still active. Keep existing entry even if name was missing in this specific payload.
                            logging.info(f"User ID {primary_user_id} (active, name unknown in current payload) already in patrons. Keeping existing entry.")
                else: # Not 'active_patron' (e.g., 'declined_patron', 'former_patron', or other)
                    if primary_user_id in current_patrons:
                        logging.info(f"Patron User ID: {primary_user_id} no longer active (status: {patron_status}). Removing from patrons list.")
                        del current_patrons[primary_user_id]
                        patrons_changed = True
                    else:
                        logging.info(f"Received non-active status ({patron_status}) for User ID: {primary_user_id}, who was not in our active patrons list.")

        elif event_type == 'members:pledge:delete':
            # For delete, primary_user_id is extracted the same way from member_data
            if not primary_user_id:
                logging.warning(f"Could not extract User ID from {event_type} event payload. Relationships: {json.dumps(payload.get('data', {}).get('relationships', {}))}")
            else:
                if primary_user_id in current_patrons:
                    logging.info(f"Pledge deleted event for User ID: {primary_user_id}. Removing from patrons list.")
                    del current_patrons[primary_user_id]
                    patrons_changed = True
                else:
                    logging.info(f"Received {event_type} event for User ID: {primary_user_id}, who was not in our active patrons list.")
        else:
            logging.info(f"Ignoring unhandled event type: {event_type}")

        if patrons_changed:
            save_patrons(current_patrons)
            # Logging of save action is now inside save_patrons()

        return jsonify({"status": "success", "event_processed": event_type}), 200

    except KeyError as e:
        logging.error(f"KeyError accessing payload data for event {event_type}: {e} - Payload: {json.dumps(payload)}", exc_info=True)
        abort(400, description=f"Error processing payload structure for event {event_type}. Key: {e}")
    except Exception as e:
        logging.error(f"Unexpected error processing webhook event {event_type}: {e}", exc_info=True)
        abort(500, description=f"Internal server error processing webhook event {event_type}.")


# --- API Endpoint for Checking Patron Status ---

@app.route('/check_patron/<string:user_id_param>', methods=['GET'])
def check_patron(user_id_param): # Renamed param to avoid conflict with any module-level var named user_id
    """Checks if a given User ID belongs to an active patron and returns their name if so."""
    logging.debug(f"API request: Checking status for User ID: {user_id_param}")

    if not user_id_param:
        return jsonify({"error": "User ID cannot be empty"}), 400

    current_patrons = load_patrons() # Returns a dict
    patron_data = current_patrons.get(user_id_param)

    if patron_data:
        patron_name = patron_data.get("name", "N/A") # Provide a default if name key is somehow missing
        logging.info(f"API check result for User ID {user_id_param}: Patron, Name: {patron_name}")
        return jsonify({"user_id": user_id_param, "is_patron": True, "name": patron_name})
    else:
        logging.info(f"API check result for User ID {user_id_param}: Not Patron")
        return jsonify({"user_id": user_id_param, "is_patron": False})

# --- Health Check Endpoint (Good Practice) ---
@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "ok"}), 200

# --- Main Execution ---
if __name__ == '__main__':
    # This log is a reminder if the hardcoded secret was removed and not replaced by an env var
    if not PATREON_WEBHOOK_SECRET:
        logging.warning(
            "Reminder: PATREON_WEBHOOK_SECRET is not set or is empty. "
            "Webhook signature verification will fail. "
            "Ensure it's set (either hardcoded for demo or via environment variable for production)."
        )

    logging.info("Starting Flask development server on http://0.0.0.0:8080")
    port = int(os.environ.get("PORT", 8080)) # Read PORT env var
    app.run(host='0.0.0.0', port=port, debug=False)