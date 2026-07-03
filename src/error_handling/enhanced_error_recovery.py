from typing import Dict, Any, Callable
import time
import smtplib
from email.mime.text import MIMEText

from src.workflow.logger import AppLogger
from src.error_handling.manual_review import ManualReviewInterface

class EnhancedErrorRecovery:
    """Provides enhanced error handling, retry mechanisms, and notifications."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = AppLogger(log_file=self.config.get("log_file")).get_logger()
        self.manual_review_interface = ManualReviewInterface(config)

        self.max_retries = self.config.get("error_recovery_max_retries", 3)
        self.retry_delay_seconds = self.config.get("error_recovery_retry_delay_seconds", 5)
        self.email_notifications_enabled = self.config.get("email_notifications_enabled", False)
        self.notification_email_address = self.config.get("notification_email_address")
        self.smtp_server = self.config.get("smtp_server")
        self.smtp_port = self.config.get("smtp_port")
        self.smtp_username = self.config.get("smtp_username")
        self.smtp_password = self.config.get("smtp_password")

    def handle_error(self, error: Exception, context: str, document_id: str = None):
        """Logs the error, sends notification, and adds to manual review if applicable."""
        error_message = f"Error in {context}: {str(error)}"
        self.logger.error(error_message, exc_info=True)

        if self.email_notifications_enabled and self.notification_email_address:
            self._send_email_notification(f"Automated Bookkeeping Error: {context}", error_message)

        if document_id:
            self.manual_review_interface.add_to_review_queue(document_id, "system_error", error_message)

    def retry_decorator(self, func: Callable) -> Callable:
        """A decorator to add retry logic to functions."""
        def wrapper(*args, **kwargs):
            for attempt in range(self.max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    self.logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay_seconds * (2 ** attempt)) # Exponential backoff
                    else:
                        self.handle_error(e, f"retry_failed_{func.__name__}")
                        raise # Re-raise the last exception if all retries fail
        return wrapper

    def execute_with_retry(self, action: Callable, operation_name: str) -> bool:
        """Runs an action with configured retries and returns success state."""
        for attempt in range(self.max_retries + 1):
            try:
                action()
                return True
            except Exception as exc:
                self.logger.warning(f"Attempt {attempt + 1} failed for {operation_name}: {exc}")
                if attempt >= self.max_retries:
                    self.handle_error(exc, operation_name)
                    return False
                time.sleep(self.retry_delay_seconds * (2 ** attempt))

    def _send_email_notification(self, subject: str, body: str):
        if not all([self.smtp_server, self.smtp_port, self.smtp_username, self.smtp_password, self.notification_email_address]):
            self.logger.warning("SMTP credentials or notification email not fully configured. Cannot send email notification.")
            return

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.smtp_username
        msg["To"] = self.notification_email_address

        try:
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            self.logger.info(f"Error notification email sent to {self.notification_email_address}")
        except Exception as e:
            self.logger.error(f"Failed to send error notification email: {e}")


