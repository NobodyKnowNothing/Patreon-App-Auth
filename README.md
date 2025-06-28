# Patreon Authentication Backend - Username Migration

This document explains the changes made to migrate the authentication system from using Patreon User IDs to using Patreon usernames.

## Changes Made

### 1. Modified Authentication Backend (`app.py`)

The main application has been updated to use Patreon usernames instead of User IDs:

#### Key Changes:
- **Database Structure**: Changed from `user_id` as key to `username` as key
- **API Endpoint**: Changed from `/check_patron/<user_id>` to `/check_patron/<username>`
- **Webhook Processing**: Updated to extract and use usernames from Patreon API payloads
- **Data Storage**: Now stores `{"username": {"user_id": "...", "full_name": "..."}}`

#### Old Format:
```json
{
    "12345": {"name": "John Doe"},
    "67890": {"name": "Jane Smith"}
}
```

#### New Format:
```json
{
    "johndoe": {"user_id": "12345", "full_name": "John Doe"},
    "janesmith": {"user_id": "67890", "full_name": "Jane Smith"}
}
```

### 2. Updated Webhook Configuration Requirements

The Patreon webhook must now be configured to include user social connections:

```
fields[user]=full_name,social_connections&include=user
```

This ensures the webhook payload includes the username information needed for the new system.

### 3. API Response Changes

The `/check_patron/<username>` endpoint now returns:

```json
{
    "username": "johndoe",
    "is_patron": true,
    "full_name": "John Doe",
    "user_id": "12345"
}
```

## Database Conversion Script

### Overview

The `convert_database.py` script converts your existing database from the old format to the new format.

### Requirements

1. **Patreon API Access Token**: You need a valid Patreon API access token with user read permissions
2. **Environment Variable**: Set `PATREON_ACCESS_TOKEN` environment variable

### How to Get a Patreon API Access Token

1. Go to the [Patreon Developer Portal](https://www.patreon.com/portal/registration/register-clients)
2. Create a new client application
3. Generate an access token with the following scopes:
   - `identity`
   - `identity[email]`
   - `campaigns`
   - `campaigns.members`

### Running the Conversion Script

1. **Set the environment variable**:
   ```bash
   export PATREON_ACCESS_TOKEN="your_access_token_here"
   ```

2. **Run the conversion script**:
   ```bash
   python3 convert_database.py
   ```

3. **Follow the prompts**: The script will:
   - Load your existing data
   - Create a backup in cell B1
   - Fetch usernames from Patreon API for each user ID
   - Convert the data to the new format
   - Save the converted data back to cell A1
   - Verify the conversion

### What the Script Does

1. **Backup**: Creates a backup of your old data in Google Sheets cell B1
2. **API Calls**: For each user ID, makes an API call to Patreon to get the username
3. **Conversion**: Transforms the data structure to use usernames as keys
4. **Verification**: Checks that the converted data is in the correct format
5. **Rate Limiting**: Includes delays between API calls to avoid rate limits

### Error Handling

- If a username cannot be found for a user ID, the script will log the failure
- Failed conversions are reported at the end
- You can choose to proceed or cancel if there are failures
- The original data is always backed up before conversion

## Deployment Notes

### Environment Variables Required

- `PATREON_WEBHOOK_SECRET`: Your Patreon webhook secret
- `GOOGLE_APPLICATION_CREDENTIALS_JSON`: Google Sheets API credentials
- `PATREON_ACCESS_TOKEN`: Only needed for the conversion script

### Webhook Configuration

Update your Patreon webhook configuration to include:
```
fields[user]=full_name,social_connections&include=user
```

This ensures the webhook payload includes both the full name and username information.

## Testing

After conversion, test the new system by:

1. **API Testing**: Make requests to `/check_patron/<username>` instead of `/check_patron/<user_id>`
2. **Webhook Testing**: Trigger webhook events and verify they process correctly
3. **Data Verification**: Check that all patron data is correctly converted

## Rollback Plan

If you need to rollback to the old system:

1. The original data is backed up in Google Sheets cell B1
2. Copy the backup data from B1 back to A1
3. Revert to the original `app.py` file
4. Update your webhook configuration back to the original format

## Support

If you encounter issues during the conversion:

1. Check the logs for detailed error messages
2. Verify your Patreon API access token has the correct permissions
3. Ensure your webhook is configured with the required fields
4. The backup in cell B1 can be used to restore the original data if needed

## Files Modified/Added

- `app.py` - Modified to use usernames instead of user IDs
- `convert_database.py` - New script to convert existing data
- `README.md` - This documentation file

The `sheetsapi.py` file remains unchanged as it only handles Google Sheets operations.

