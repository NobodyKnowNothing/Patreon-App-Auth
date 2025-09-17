# Patreon Webhook Handler

This is a FastAPI application that handles Patreon webhooks to manage a list of patrons in a Google Sheet. Designed for small scale quick authentication refrences without needing an end user to Login and do an Oauth for Patreon authentication. Useful for small scale Patreon funded applications who want to minimize upkeep costs.

## Features

-   Receives `members:pledge:create` and `members:pledge:delete` webhooks from Patreon.
-   Verifies webhook signatures for security.
-   Adds new patrons to a Google Sheet.
-   Removes patrons who delete their pledge.

## Setup for Local Development

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd Patreon-App-Auth
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    .\.venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    -   Copy the example environment file: `copy .env.example .env`
    -   Edit `.env` and set `ENV=dev`.

5.  **Run the application:**
    ```bash
    python main.py
    ```
    The server will be running at `http://localhost:8080`.

## Deployment

This application is designed for deployment on Google Cloud Run. The deployment process is managed by the `fastapi_app/deploy.ps1` script.

### Required Environment Variables for Production:

-   `ENV`: Set to `prod` or any value other than `dev`.
-   `SHEET_ID`: The ID of the target Google Sheet.
-   `GOOGLE_CREDS_JSON`: The JSON content of your Google service account credentials.
-   `WEBHOOK_SECRET`: The secret key for your Patreon webhook.