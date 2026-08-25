import logging
import asyncio
import httpx
from typing import Dict, Any

logger = logging.getLogger("notification_service")

# Global toggle to simulate service failures (Probe 5)
SIMULATE_NOTIFICATION_FAILURE = False

async def trigger_webhook(url: str, payload: Dict[str, Any], retries: int = 3, delay: float = 1.0):
    """
    Attempts to trigger an external webhook with a simple retry mechanism.
    If it fails, it logs the error but does not raise (safe side-effect).
    """
    global SIMULATE_NOTIFICATION_FAILURE
    if SIMULATE_NOTIFICATION_FAILURE:
        logger.error("Webhook side-effect failed (simulated failure).")
        raise RuntimeError("Simulated notification service failure")

    async with httpx.AsyncClient(timeout=3.0) as client:
        for attempt in range(retries):
            try:
                response = await client.post(url, json=payload)
                if response.status_code in (200, 201, 204):
                    logger.info(f"Webhook triggered successfully: {url} (status: {response.status_code})")
                    return
                else:
                    logger.warning(f"Webhook returned status {response.status_code} (attempt {attempt+1}/{retries})")
            except Exception as e:
                logger.warning(f"Webhook failed with error: {str(e)} (attempt {attempt+1}/{retries})")
            
            await asyncio.sleep(delay)
        
        logger.error(f"Webhook failed after {retries} attempts.")

async def send_confirmation_email(email_address: str, widget_title: str, payload: Dict[str, Any]):
    """
    Simulates sending an email by writing logs to console and a local file.
    Failure here does not block the API response.
    """
    global SIMULATE_NOTIFICATION_FAILURE
    if SIMULATE_NOTIFICATION_FAILURE:
        logger.error("Email side-effect failed (simulated failure).")
        raise RuntimeError("Simulated notification service failure")

    # Simulate network delay for a real email server
    await asyncio.sleep(0.5)

    email_log_message = (
        f"\n========================================\n"
        f"EMAIL SENT TO: {email_address}\n"
        f"SUBJECT: New Submission on Widget '{widget_title}'\n"
        f"CONTENT:\n"
        f"Thank you for your submission. Here is the received data:\n"
        f"{payload}\n"
        f"========================================\n"
    )
    print(email_log_message)
    logger.info(f"Notification email successfully 'sent' (logged) to {email_address}")

def process_submission_side_effects(widget: Any, submission_payload: Dict[str, Any]):
    """
    Dispatches side effects in the background. Wraps execution in safety checks
    so errors are logged but never propagate back to the HTTP response.
    """
    # 1. Email Notification
    # Find if there is an email field in the payload or send to widget owner
    email_target = submission_payload.get("email")
    if not email_target:
        # Fallback to widget name / owner placeholder
        email_target = "owner@tenant.local"

    try:
        # Run email task asynchronously
        asyncio.create_task(send_confirmation_email(
            email_address=email_target,
            widget_title=widget.title or widget.name,
            payload=submission_payload
        ))
    except Exception as e:
        logger.error(f"Failed to queue email notification task: {str(e)}")

    # 2. Webhook Notification (if configured in widget display settings/options)
    webhook_url = widget.display_settings.get("webhook_url")
    if webhook_url:
        try:
            # Run webhook task asynchronously with retries
            asyncio.create_task(trigger_webhook(
                url=webhook_url,
                payload={"widget_id": widget.id, "submission": submission_payload}
            ))
        except Exception as e:
            logger.error(f"Failed to queue webhook task: {str(e)}")
