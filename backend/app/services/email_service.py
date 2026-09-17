import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    def send_email(to_email: str, subject: str, html_content: str, text_content: str = "") -> bool:
        """Sends an email using either console logger or SMTP as configured."""
        if settings.EMAIL_PROVIDER == "console" or settings.ENVIRONMENT == "test":
            logger.info("=========================================")
            logger.info(f"EMAIL OUTBOX (PROVIDER: {settings.EMAIL_PROVIDER})")
            logger.info(f"To: {to_email}")
            logger.info(f"From: {settings.EMAIL_FROM}")
            logger.info(f"Subject: {subject}")
            logger.info("---- HTML CONTENT ----")
            logger.info(html_content)
            logger.info("=========================================")
            return True

        if settings.EMAIL_PROVIDER == "smtp":
            try:
                # Setup email message
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = settings.EMAIL_FROM
                msg["To"] = to_email

                if text_content:
                    msg.attach(MIMEText(text_content, "plain"))
                msg.attach(MIMEText(html_content, "html"))

                # SMTP Connection
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                    if settings.SMTP_USE_TLS:
                        server.starttls()
                    if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.send_message(msg)
                
                logger.info(f"Successfully sent email to {to_email} via SMTP")
                return True
            except Exception as e:
                logger.error(f"Failed to send email to {to_email} via SMTP: {str(e)}")
                raise e

        if settings.EMAIL_PROVIDER == "resend":
            if not settings.RESEND_API_KEY:
                logger.error("RESEND_API_KEY is not set in environment settings.")
                raise ValueError("RESEND_API_KEY must be configured for Resend email provider.")
            
            try:
                import httpx
                headers = {
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "from": settings.EMAIL_FROM,
                    "to": to_email,
                    "subject": subject,
                    "html": html_content,
                }
                if text_content:
                    payload["text"] = text_content
                
                with httpx.Client(timeout=15.0) as client:
                    response = client.post("https://api.resend.com/emails", json=payload, headers=headers)
                    response.raise_for_status()
                    
                logger.info(f"Successfully sent email to {to_email} via Resend REST API")
                return True
            except Exception as e:
                logger.error(f"Failed to send email to {to_email} via Resend: {str(e)}")
                raise e

        logger.warning(f"Unknown email provider: {settings.EMAIL_PROVIDER}. Email was not delivered.")
        return False

    @staticmethod
    def send_invitation_email(
        email: str, team_name: str, inviter_name: str, role_name: str, invite_url: str, expires_days: int = 7
    ) -> bool:
        """Helper to generate and send team invitation email templates."""
        subject = f"You are invited to join {team_name} on SocialPilot"
        role_label = role_name.replace("_", " ").title()
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #1e293b; line-height: 1.5; padding: 20px; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px;">
            <div style="text-align: center; margin-bottom: 24px;">
                <h2 style="color: #6d28d9; margin: 0;">SocialPilot</h2>
                <p style="font-size: 14px; color: #64748b; margin-top: 4px;">Collaborative Social Media Management</p>
            </div>
            <p>Hello,</p>
            <p><strong>{inviter_name}</strong> has invited you to join the workspace <strong>{team_name}</strong> as a <strong>{role_label}</strong>.</p>
            <p style="margin: 30px 0; text-align: center;">
                <a href="{invite_url}" style="background-color: #6d28d9; color: #ffffff; text-decoration: none; padding: 12px 24px; font-weight: bold; border-radius: 8px; display: inline-block;">Accept Invitation</a>
            </p>
            <p style="font-size: 13px; color: #64748b;">
                This invitation link will expire in {expires_days} days. If you do not have a SocialPilot account, you will need to register using this email address: <strong>{email}</strong>.
            </p>
            <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 24px 0;" />
            <p style="font-size: 11px; color: #94a3b8; text-align: center;">
                If you did not expect this invitation, you can safely ignore this email.
            </p>
        </body>
        </html>
        """
        text_content = f"You are invited to join {team_name} on SocialPilot as a {role_label}.\nAccept invitation here: {invite_url}\nThis link expires in {expires_days} days."
        
        return EmailService.send_email(
            to_email=email, subject=subject, html_content=html_content, text_content=text_content
        )
