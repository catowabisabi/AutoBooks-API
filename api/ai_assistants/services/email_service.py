"""AI helpers for Email Assistant.

Includes:
- AI summarization and reply generation
- SMTP email sending
- IMAP email receiving and synchronization
"""

from __future__ import annotations

import json
import logging
import smtplib
import imaplib
import email as email_module
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import parseaddr, formataddr
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from openai import OpenAI

from ai_assistants.models import Email, EmailAccount, EmailAttachment

logger = logging.getLogger(__name__)


def _get_client() -> OpenAI:
	api_key = getattr(settings, "OPENAI_API_KEY", None)
	if not api_key:
		raise RuntimeError("OPENAI_API_KEY is not configured")
	return OpenAI(api_key=api_key)


def summarize_email(email: Email) -> Dict[str, object]:
	"""Generate AI summary, action items, and sentiment for an email."""
	prompt = (
		"You are an email analysis assistant for an accounting and audit firm. "
		"Summarize the email in 2 sentences, extract up to 3 actionable next steps "
		"with deadlines if mentioned, and label the sentiment as positive, neutral, or negative. "
		"Respond in JSON with keys: summary (string), action_items (array of {action, deadline}), sentiment (string)."
	)

	body = email.body_text or email.body_html or ""
	email_context = (
		f"From: {email.from_name or ''} <{email.from_address}>\n"
		f"To: {', '.join(email.to_addresses or [])}\n"
		f"Subject: {email.subject}\n"
		f"Body: {body[:4000]}"
	)

	try:
		client = _get_client()
		completion = client.chat.completions.create(
			model="gpt-4o-mini",
			messages=[
				{"role": "system", "content": prompt},
				{"role": "user", "content": email_context},
			],
			response_format={"type": "json_object"},
			temperature=0.2,
			max_tokens=500,
		)
		raw_content = completion.choices[0].message.content or "{}"
		data = json.loads(raw_content)
	except RuntimeError as exc:
		logger.warning("Email summary skipped: %s", exc)
		return {
			"summary": "AI summarization unavailable (missing API key).",
			"action_items": [],
			"sentiment": "neutral",
		}
	except Exception as exc:  # pragma: no cover - defensive logging
		logger.error("Email summary failed: %s", exc, exc_info=True)
		raise

	return {
		"summary": data.get("summary") or "No summary provided.",
		"action_items": data.get("action_items") or [],
		"sentiment": data.get("sentiment") or "neutral",
	}


def generate_ai_reply(email: Email, tone: str = "professional", key_points: List[str] | None = None) -> Dict[str, str]:
	"""Generate an AI-crafted reply for an email."""
	key_points = key_points or []
	body = email.body_text or email.body_html or ""

	system_prompt = (
		"You are a helpful email drafting assistant for a professional services firm. "
		"Write a concise reply in the requested tone. Maintain a polite greeting and closing."
	)

	user_prompt = (
		f"Tone: {tone}\n"
		f"Key points to include: {', '.join(key_points) if key_points else 'N/A'}\n"
		f"From: {email.from_name or ''} <{email.from_address}>\n"
		f"Subject: {email.subject}\n"
		f"Body: {body[:4000]}"
	)

	try:
		client = _get_client()
		completion = client.chat.completions.create(
			model="gpt-4o-mini",
			messages=[
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": user_prompt},
			],
			temperature=0.4,
			max_tokens=500,
		)
		reply_text = (completion.choices[0].message.content or "").strip()
	except RuntimeError as exc:
		logger.warning("Email reply generation skipped: %s", exc)
		reply_text = (
			"Unable to generate an AI reply because no AI provider is configured. "
			"Please set OPENAI_API_KEY."
		)
	except Exception as exc:  # pragma: no cover - defensive logging
		logger.error("Email reply generation failed: %s", exc, exc_info=True)
		raise

	return {"suggested_reply": reply_text, "tone": tone}


# =================================================================
# SMTP Email Sending
# =================================================================

def send_email_smtp(
    account: EmailAccount,
    to_addresses: List[str],
    subject: str,
    body_text: str,
    body_html: str = "",
    cc_addresses: List[str] = None,
    bcc_addresses: List[str] = None,
    attachments: List[Dict] = None,
    reply_to: str = None,
) -> Dict[str, any]:
    """
    Send email via SMTP using the provided EmailAccount configuration.
    
    Args:
        account: EmailAccount with SMTP settings
        to_addresses: List of recipient email addresses
        subject: Email subject
        body_text: Plain text body
        body_html: HTML body (optional)
        cc_addresses: CC recipients
        bcc_addresses: BCC recipients
        attachments: List of dicts with 'filename', 'content', 'content_type'
        reply_to: Reply-to address
    
    Returns:
        Dict with 'success', 'message_id', 'error' keys
    """
    if account.is_demo:
        logger.info("Demo mode - email not actually sent via SMTP")
        return {
            "success": True,
            "message_id": f"demo-{timezone.now().timestamp()}",
            "demo": True
        }
    
    cc_addresses = cc_addresses or []
    bcc_addresses = bcc_addresses or []
    attachments = attachments or []
    
    try:
        # Create message
        if body_html:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
            msg.attach(MIMEText(body_html, "html", "utf-8"))
        else:
            msg = MIMEMultipart()
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
        
        # Set headers
        msg["Subject"] = subject
        msg["From"] = formataddr((account.display_name, account.email_address))
        msg["To"] = ", ".join(to_addresses)
        if cc_addresses:
            msg["Cc"] = ", ".join(cc_addresses)
        if reply_to:
            msg["Reply-To"] = reply_to
        
        # Add attachments
        for attachment in attachments:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.get("content", b""))
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{attachment.get("filename", "attachment")}"'
            )
            msg.attach(part)
        
        # All recipients
        all_recipients = to_addresses + cc_addresses + bcc_addresses
        
        # Connect and send
        if account.use_tls:
            server = smtplib.SMTP(account.smtp_host, account.smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(account.smtp_host, account.smtp_port)
        
        if account.smtp_user and account.smtp_password:
            server.login(account.smtp_user, account.smtp_password)
        
        server.sendmail(account.email_address, all_recipients, msg.as_string())
        server.quit()
        
        logger.info(f"Email sent successfully to {all_recipients}")
        return {
            "success": True,
            "message_id": msg.get("Message-ID"),
        }
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}")
        return {"success": False, "error": f"Authentication failed: {e}"}
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        return {"success": False, "error": f"SMTP error: {e}"}
    except Exception as e:
        logger.error(f"Failed to send email: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# =================================================================
# IMAP Email Receiving
# =================================================================

def fetch_emails_imap(
    account: EmailAccount,
    folder: str = "INBOX",
    limit: int = 50,
    since_date: datetime = None,
    unseen_only: bool = False,
) -> List[Dict]:
    """
    Fetch emails from IMAP server.
    
    Args:
        account: EmailAccount with IMAP settings
        folder: IMAP folder to fetch from
        limit: Maximum number of emails to fetch
        since_date: Only fetch emails since this date
        unseen_only: Only fetch unread emails
    
    Returns:
        List of email dictionaries
    """
    if account.is_demo:
        logger.info("Demo mode - returning mock emails")
        return _get_demo_emails()
    
    if not account.imap_host:
        logger.warning("IMAP host not configured for account %s", account.email_address)
        return []
    
    try:
        # Connect to IMAP
        mail = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
        mail.login(account.smtp_user or account.email_address, account.smtp_password)
        mail.select(folder)
        
        # Build search criteria
        search_criteria = []
        if unseen_only:
            search_criteria.append("UNSEEN")
        if since_date:
            date_str = since_date.strftime("%d-%b-%Y")
            search_criteria.append(f'SINCE {date_str}')
        
        if not search_criteria:
            search_criteria = ["ALL"]
        
        # Search emails
        status, messages = mail.search(None, *search_criteria)
        if status != "OK":
            logger.error("IMAP search failed")
            return []
        
        email_ids = messages[0].split()
        # Get latest emails first
        email_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids
        email_ids.reverse()
        
        emails = []
        for email_id in email_ids:
            try:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    continue
                
                raw_email = msg_data[0][1]
                parsed_email = _parse_email(raw_email)
                if parsed_email:
                    emails.append(parsed_email)
            except Exception as e:
                logger.error(f"Failed to fetch email {email_id}: {e}")
                continue
        
        mail.logout()
        return emails
        
    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP error: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to fetch emails: {e}", exc_info=True)
        return []


def _parse_email(raw_email: bytes) -> Optional[Dict]:
    """Parse raw email bytes into a dictionary."""
    try:
        msg = email_module.message_from_bytes(raw_email)
        
        # Parse headers
        from_addr = msg.get("From", "")
        from_name, from_email = parseaddr(from_addr)
        
        to_addrs = msg.get("To", "")
        to_list = [parseaddr(addr)[1] for addr in to_addrs.split(",") if addr.strip()]
        
        cc_addrs = msg.get("Cc", "")
        cc_list = [parseaddr(addr)[1] for addr in cc_addrs.split(",") if addr.strip()] if cc_addrs else []
        
        # Parse date
        date_str = msg.get("Date", "")
        received_at = None
        if date_str:
            try:
                from email.utils import parsedate_to_datetime
                received_at = parsedate_to_datetime(date_str)
            except:
                pass
        
        # Parse body
        body_text = ""
        body_html = ""
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                if "attachment" in content_disposition:
                    attachments.append({
                        "filename": part.get_filename() or "attachment",
                        "content_type": content_type,
                        "content": part.get_payload(decode=True),
                    })
                elif content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode("utf-8", errors="ignore")
                elif content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_html = payload.decode("utf-8", errors="ignore")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                if msg.get_content_type() == "text/html":
                    body_html = payload.decode("utf-8", errors="ignore")
                else:
                    body_text = payload.decode("utf-8", errors="ignore")
        
        return {
            "message_id": msg.get("Message-ID", ""),
            "from_address": from_email,
            "from_name": from_name,
            "to_addresses": to_list,
            "cc_addresses": cc_list,
            "subject": msg.get("Subject", "(No Subject)"),
            "body_text": body_text,
            "body_html": body_html,
            "received_at": received_at,
            "attachments": attachments,
            "in_reply_to": msg.get("In-Reply-To", ""),
            "references": msg.get("References", ""),
        }
    except Exception as e:
        logger.error(f"Failed to parse email: {e}")
        return None


def sync_emails_for_account(account: EmailAccount, limit: int = 100) -> Dict:
    """
    Synchronize emails from IMAP server to database.
    
    Args:
        account: EmailAccount to sync
        limit: Maximum emails to fetch
    
    Returns:
        Dict with sync statistics
    """
    fetched_emails = fetch_emails_imap(account, limit=limit)
    
    created = 0
    updated = 0
    errors = 0
    
    for email_data in fetched_emails:
        try:
            # Check if email already exists by message_id
            message_id = email_data.get("message_id", "")
            existing = None
            if message_id:
                existing = Email.objects.filter(
                    account=account,
                    thread_id=message_id
                ).first()
            
            if existing:
                # Update existing email
                updated += 1
            else:
                # Create new email
                email_obj = Email.objects.create(
                    account=account,
                    from_address=email_data["from_address"],
                    from_name=email_data.get("from_name", ""),
                    to_addresses=email_data.get("to_addresses", []),
                    cc_addresses=email_data.get("cc_addresses", []),
                    subject=email_data.get("subject", ""),
                    body_text=email_data.get("body_text", ""),
                    body_html=email_data.get("body_html", ""),
                    thread_id=message_id,
                    received_at=email_data.get("received_at") or timezone.now(),
                    status="RECEIVED",
                    is_read=False,
                    has_attachments=bool(email_data.get("attachments")),
                )
                
                # Save attachments
                for att_data in email_data.get("attachments", []):
                    EmailAttachment.objects.create(
                        email=email_obj,
                        filename=att_data.get("filename", "attachment"),
                        content_type=att_data.get("content_type", "application/octet-stream"),
                        file=ContentFile(att_data.get("content", b""), name=att_data.get("filename", "attachment")),
                        size=len(att_data.get("content", b"")),
                    )
                
                created += 1
                
        except Exception as e:
            logger.error(f"Failed to sync email: {e}")
            errors += 1
    
    return {
        "fetched": len(fetched_emails),
        "created": created,
        "updated": updated,
        "errors": errors,
    }


def _get_demo_emails() -> List[Dict]:
    """Return demo emails for testing."""
    return [
        {
            "message_id": "demo-1",
            "from_address": "client@example.com",
            "from_name": "John Client",
            "to_addresses": ["demo@wisematic.com"],
            "cc_addresses": [],
            "subject": "Tax Document Request - Q4 2024",
            "body_text": "Dear Team,\n\nPlease find attached the tax documents for Q4 2024. Could you review them by next Friday?\n\nBest regards,\nJohn",
            "body_html": "",
            "received_at": timezone.now(),
            "attachments": [],
        },
        {
            "message_id": "demo-2",
            "from_address": "finance@acme.com",
            "from_name": "ACME Finance",
            "to_addresses": ["demo@wisematic.com"],
            "cc_addresses": [],
            "subject": "Invoice #2024-1234 Payment Reminder",
            "body_text": "Hi,\n\nThis is a friendly reminder that invoice #2024-1234 is due in 3 days. Please process the payment.\n\nThank you,\nACME Finance Team",
            "body_html": "",
            "received_at": timezone.now(),
            "attachments": [],
        },
    ]


def test_smtp_connection(account: EmailAccount) -> Dict:
    """Test SMTP connection for an account."""
    if account.is_demo:
        return {"success": True, "message": "Demo mode - connection not tested"}
    
    try:
        if account.use_tls:
            server = smtplib.SMTP(account.smtp_host, account.smtp_port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(account.smtp_host, account.smtp_port, timeout=10)
        
        if account.smtp_user and account.smtp_password:
            server.login(account.smtp_user, account.smtp_password)
        
        server.quit()
        return {"success": True, "message": "SMTP connection successful"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_imap_connection(account: EmailAccount) -> Dict:
    """Test IMAP connection for an account."""
    if account.is_demo:
        return {"success": True, "message": "Demo mode - connection not tested"}
    
    if not account.imap_host:
        return {"success": False, "error": "IMAP host not configured"}
    
    try:
        mail = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
        mail.login(account.smtp_user or account.email_address, account.smtp_password)
        mail.logout()
        return {"success": True, "message": "IMAP connection successful"}
    except Exception as e:
        return {"success": False, "error": str(e)}
