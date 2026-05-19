"""
Email I/O helpers — IMAP inbox polling and SMTP reply sending.

Uses only Python standard library (imaplib, smtplib, email).
"""
import imaplib
import smtplib
import email as email_lib
import email.utils
import re
from dataclasses import dataclass
from email.mime.text import MIMEText
from typing import List, Optional

from openjiuwen.core.common.logging import logger


@dataclass
class InboundEmail:
    """A parsed inbound email message."""
    from_address: str
    subject: str
    body: str
    message_id: str
    uid: str


@dataclass
class IMAPConfig:
    host: str
    port: int
    username: str
    password: str


@dataclass
class SMTPConfig:
    host: str
    port: int
    username: str
    password: str
    from_address: str


# ── IMAP ─────────────────────────────────────────────────────────────────────

def fetch_unread_messages(config: IMAPConfig) -> List[InboundEmail]:
    """Connect to IMAP, fetch all UNSEEN messages, return parsed list."""
    results: List[InboundEmail] = []
    try:
        with imaplib.IMAP4_SSL(config.host, config.port) as imap:
            imap.login(config.username, config.password)
            imap.select("INBOX")

            _, data = imap.uid("search", None, "UNSEEN")
            uids = data[0].split() if data[0] else []

            for uid in uids:
                try:
                    _, msg_data = imap.uid("fetch", uid, "(RFC822)")
                    raw = msg_data[0][1]
                    msg = email_lib.message_from_bytes(raw)

                    from_header = msg.get("From", "")
                    _, from_address = email.utils.parseaddr(from_header)
                    subject = _decode_header(msg.get("Subject", "(no subject)"))
                    message_id = msg.get("Message-ID", "")
                    body = _extract_body(msg)

                    results.append(InboundEmail(
                        from_address=from_address.lower().strip(),
                        subject=subject,
                        body=body,
                        message_id=message_id,
                        uid=uid.decode(),
                    ))
                except Exception as e:
                    logger.warning("Failed to parse email uid=%s: %s", uid, e)
    except Exception as e:
        logger.error("IMAP error: %s", e)
    return results


def _decode_header(value: str) -> str:
    """Decode a possibly RFC 2047-encoded header value."""
    try:
        parts = email_lib.header.decode_header(value)
        decoded = []
        for part, charset in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                decoded.append(part)
        return "".join(decoded)
    except Exception:
        return value


def _extract_body(msg) -> str:
    """Extract plain-text body from a (possibly multipart) email."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in disp:
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
    else:
        charset = msg.get_content_charset() or "utf-8"
        return msg.get_payload(decode=True).decode(charset, errors="replace")
    return ""


# ── Command extraction ────────────────────────────────────────────────────────

def extract_command(body: str) -> Optional[str]:
    """Return the first non-quoted, non-empty line from the email body.

    Skips lines starting with ">" (quoted replies) and common reply
    separators like "On ... wrote:".
    """
    separator_re = re.compile(
        r"^(>|On .+ wrote:|From:|-----Original Message-----|_{5,}|-{5,})",
        re.IGNORECASE,
    )
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if separator_re.match(stripped):
            break  # everything after this is quoted reply — stop
        return stripped
    return None


# ── SMTP ─────────────────────────────────────────────────────────────────────

def send_reply(
    config: SMTPConfig,
    to_address: str,
    original_subject: str,
    body: str,
    in_reply_to: str = "",
) -> None:
    """Send a plain-text reply email via SMTP."""
    subject = original_subject if original_subject.lower().startswith("re:") else f"Re: {original_subject}"

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = config.from_address
    msg["To"] = to_address
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to

    try:
        with smtplib.SMTP(config.host, config.port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()  # re-identify after TLS upgrade (required by RFC 3207)
            smtp.login(config.username, config.password)
            smtp.sendmail(config.from_address, [to_address], msg.as_string())
        logger.info("Reply sent to %s", to_address)
    except Exception as e:
        logger.error("SMTP error sending to %s: %s", to_address, e)


# ── Markdown stripper ────────────────────────────────────────────────────────

def strip_markdown(text: str) -> str:
    """Remove common markdown formatting for plain-text email output."""
    # Bold/italic: **text**, *text*, __text__, _text_
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)

    # Inline code: `text`
    text = re.sub(r"`(.+?)`", r"\1", text)

    return text
