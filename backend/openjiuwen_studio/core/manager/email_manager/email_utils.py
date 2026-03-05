import ssl
import socket
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.manager.model_manager.utils.security_utils import SecurityUtils
from openjiuwen_studio.core.config import settings
from openjiuwen_studio.core.manager.email_manager import EmailTemplates


class EmailUtils:
    """邮件发送工具类"""
    @staticmethod
    def _send_base_html_email(recipient_email: str, subject: str, html_content: str):
        sender = settings.smtp_user
        sender_alias = settings.smtp_alias
        smtp_password = SecurityUtils.get_decrypted_secret("SMTP_PASSWORD", settings.smtp_password)
        sender_pwd = smtp_password
        host = settings.smtp_host
        port = settings.smtp_port

        try:
            message = MIMEMultipart('alternative')
            message['Subject'] = Header(subject, 'UTF-8')
            message['From'] = formataddr([sender_alias, sender])
            message['To'] = recipient_email
            message.attach(MIMEText(html_content, 'html', 'UTF-8'))
            context = ssl.create_default_context()
            
            with smtplib.SMTP_SSL(host, port, context=context, timeout=10) as client:
                client.login(sender, sender_pwd)
                client.sendmail(sender, [recipient_email], message.as_string())
            
            logger.info(f"Email successfully sent to {recipient_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed: check auth code")
            return False

        except (socket.timeout, TimeoutError, smtplib.SMTPConnectError):
            logger.error("SMTP connection failed or timed out")
            return False

        except Exception:
            logger.exception(f"Failed to send email to {recipient_email}")
            return False

    @classmethod
    def send_verification_code(cls, recipient_email: str, code: str):
        """发送注册验证码"""
        subject = "【openJiuwen】注册验证码"
        html_content = EmailTemplates.get_register_template(code)
        return cls._send_base_html_email(recipient_email, subject, html_content)

    @classmethod
    def send_reset_code(cls, recipient_email: str, code: str):
        """发送重置密码验证码"""
        subject = "【openJiuwen】重置密码验证码"
        html_content = EmailTemplates.get_reset_password_template(code)
        return cls._send_base_html_email(recipient_email, subject, html_content)
