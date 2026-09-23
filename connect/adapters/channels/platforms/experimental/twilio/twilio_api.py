"""
Twilio SMS utilities — parse inbound webhook, send SMS via REST API.
Uses only stdlib (urllib) — no Twilio SDK required.
"""
import base64
import hashlib
import hmac
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass
class TwilioConfig:
    account_sid: str
    auth_token: str
    from_number: str


@dataclass
class InboundSMS:
    from_number: str   # sender phone — used as user_id
    to_number: str
    body: str


def parse_inbound(form_data: dict) -> InboundSMS:
    return InboundSMS(
        from_number=form_data.get("From", "").strip(),
        to_number=form_data.get("To", "").strip(),
        body=form_data.get("Body", "").strip(),
    )


def verify_twilio_signature(config: TwilioConfig, url: str, params: dict, signature: str) -> bool:
    """Validate X-Twilio-Signature on an inbound request."""
    s = url + "".join(k + params[k] for k in sorted(params))
    mac = hmac.new(config.auth_token.encode(), s.encode(), hashlib.sha1)
    expected = base64.b64encode(mac.digest()).decode()
    return hmac.compare_digest(expected, signature or "")


def send_sms(config: TwilioConfig, to_number: str, body: str) -> None:
    """Send an SMS via Twilio REST API (stdlib only). Truncates to 1600 chars."""
    body = body[:1600]
    url = f"https://api.twilio.com/2010-04-01/Accounts/{config.account_sid}/Messages.json"
    data = urllib.parse.urlencode({
        "From": config.from_number,
        "To": to_number,
        "Body": body,
    }).encode()
    creds = base64.b64encode(f"{config.account_sid}:{config.auth_token}".encode()).decode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Basic {creds}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=10):
        pass


def strip_markdown(text: str) -> str:
    """Remove markdown formatting — SMS clients display raw text."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\*(.+?)\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"_(.+?)_", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"`(.+?)`", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    return text.strip()
