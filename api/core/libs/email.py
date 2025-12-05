import smtplib
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

@dataclass
class EmailContent:
    subject: str
    body: str
    from_email: str
    from_password: str
    to_emails: List[str]
    cc_emails: Optional[List[str]] = None
    bcc_emails: Optional[List[str]] = None
    mime_type: str = ''

    def __init__(self, **kwargs: Dict[str, Any]):
        self.subject = kwargs.get('subject', '')
        self.body = kwargs.get('body', '')
        self.from_email = kwargs.get('from_email', '')
        self.from_password = kwargs.get('from_password', '')
        self.to_emails = kwargs.get('to_emails', [])
        self.cc_emails = kwargs.get('cc_emails', None)
        self.bcc_emails = kwargs.get('bcc_emails', None)
        self.mime_type = kwargs.get('mime_type', 'plain')

        if not self.from_email or not self.from_password or not self.to_emails:
            raise ValueError("`from_email`, `from_password`, and `to_emails` are required fields.")

    def get_receiver_emails(self) -> str:
        return ', '.join(self.to_emails)

def send_email(content: EmailContent):
    msg = MIMEMultipart()
    msg['From'] = content.from_email
    msg['To'] = content.get_receiver_emails()
    msg['Subject'] = content.subject
    msg.attach(MIMEText(content.body, content.mime_type))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(content.from_email, content.from_password)
        server.sendmail(content.from_email, content.get_receiver_emails(), msg.as_string())
        server.quit()
        return 0
    except smtplib.SMTPAuthenticationError:
        print("Authentication failed: Invalid email or app password.")
    except smtplib.SMTPException as e:
        print(f"SMTP error: {e}")
    except Exception as e:
        print(f"General error: {e}")
    return 1
