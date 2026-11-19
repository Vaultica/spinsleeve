"""
SpinSleeve V2 Notifications Service (`services/notifications.py`)
---------------------------------------------------------------
Handles transactional admin email notifications via Resend API (`OPS-03`).
"""
import os
import requests
from app_config import logger, get_secret

def send_admin_join_alert(user_name, user_email, spotify_id):
    """Sends a real-time email alert to the admin via Resend when a new user registers."""
    api_key = get_secret("RESEND_API_KEY") or os.getenv("RESEND_API_KEY")
    if not api_key:
        logger.warning("RESEND_API_KEY not configured. Skipping admin join notification.")
        return False

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": "SpinSleeve <notifications@spinsleeve.cc>",
        "to": ["serge.bouschet@gmail.com"],
        "subject": f"🔔 New SpinSleeve Collector Request: {user_name}",
        "html": f"""
            <div style="font-family: sans-serif; background: #0c0f12; color: #e5e7eb; padding: 20px; border-radius: 10px;">
                <h2 style="color: #1DB954; margin-top: 0;">🔔 New SpinSleeve Collector Request</h2>
                <p>A new user has signed in and is awaiting approval:</p>
                <ul>
                    <li><b>Display Name:</b> {user_name}</li>
                    <li><b>Spotify ID:</b> {spotify_id}</li>
                    <li><b>Email:</b> {user_email or 'Not provided'}</li>
                </ul>
                <p style="margin-top: 20px;">
                    <a href="https://spinsleeve.cc/admin" style="background: #1DB954; color: black; padding: 10px 20px; text-decoration: none; font-weight: bold; border-radius: 6px; display: inline-block;">1-Click Approval Portal</a>
                </p>
            </div>
        """
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code in (200, 201):
            logger.info("Successfully sent admin join alert for user %s (%s)", user_name, spotify_id)
            return True
        else:
            logger.error("Failed to send Resend notification: status=%s, body=%s", res.status_code, res.text)
            return False
    except Exception as e:
        logger.error("Error dispatching admin notification email: %s", e, exc_info=True)
        return False
