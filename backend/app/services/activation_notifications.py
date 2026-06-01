"""ActivationNotificationService — send email and WhatsApp confirmations when activations complete."""

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


class ActivationNotificationService:
    """Send activation success/failure notifications via email and WhatsApp."""

    async def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send email notification.

        Stub implementation that logs the email. In production, this will
        connect to an email provider (e.g., SendGrid, AWS SES).

        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body content

        Returns:
            True if email send succeeds, False otherwise
        """
        try:
            logger.info(
                f"Sending email to {to_email}",
                extra={"subject": subject, "body_length": len(body)}
            )
            # TODO: Integrate with email provider
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    async def send_whatsapp(self, to_phone: str, message: str) -> bool:
        """Send WhatsApp notification.

        Stub implementation that logs the message. In production, this will
        connect to WhatsApp Business API or Twilio.

        Args:
            to_phone: Recipient phone number in E.164 format (e.g., +1234567890)
            message: Message content

        Returns:
            True if WhatsApp send succeeds, False otherwise
        """
        try:
            logger.info(
                f"Sending WhatsApp to {to_phone}",
                extra={"message_length": len(message)}
            )
            # TODO: Integrate with WhatsApp API
            return True
        except Exception as e:
            logger.error(f"Failed to send WhatsApp to {to_phone}: {str(e)}")
            return False

    async def send_activation_success(
        self,
        activation_id: UUID,
        activation_name: str,
        campaign_manager_email: str,
        campaign_manager_phone: str,
        platforms_live: list[str],
        budget_spent: float
    ) -> bool:
        """Send success notification when activation completes successfully.

        Builds formatted email and WhatsApp messages with activation details
        and sends them to the campaign manager.

        Args:
            activation_id: UUID of the activation
            activation_name: Human-readable activation name
            campaign_manager_email: Email address to send notification to
            campaign_manager_phone: Phone number to send WhatsApp to
            platforms_live: List of platforms that are now live
            budget_spent: Total budget spent on activation

        Returns:
            True if both email and WhatsApp sent successfully, False otherwise
        """
        try:
            # Build email content
            platforms_str = ", ".join(platforms_live)
            email_subject = f"Campaign Activation Complete: {activation_name}"
            email_body = f"""
Your campaign activation has been completed successfully.

Campaign: {activation_name}
Activation ID: {activation_id}
Status: LIVE

Platforms Active:
{chr(10).join(f"• {p}" for p in platforms_live)}

Budget Spent: ${budget_spent:,.2f}

Your campaign is now live on all configured platforms.
Monitor performance in your dashboard.

Thank you for using our platform.
            """

            # Build WhatsApp message
            whatsapp_message = f"""
Your campaign "{activation_name}" is now LIVE!

Platforms: {platforms_str}
Budget: ${budget_spent:,.2f}

Monitor your campaigns in the dashboard.
            """

            # Send both notifications
            email_result = await self.send_email(
                to_email=campaign_manager_email,
                subject=email_subject,
                body=email_body
            )

            whatsapp_result = await self.send_whatsapp(
                to_phone=campaign_manager_phone,
                message=whatsapp_message
            )

            success = email_result and whatsapp_result

            if success:
                logger.info(
                    f"Activation success notification sent for {activation_id}",
                    extra={
                        "activation_name": activation_name,
                        "platforms": platforms_live,
                        "budget_spent": budget_spent
                    }
                )
            else:
                logger.warning(
                    f"Some notifications failed for activation {activation_id}",
                    extra={
                        "email_sent": email_result,
                        "whatsapp_sent": whatsapp_result
                    }
                )

            return success

        except Exception as e:
            logger.error(
                f"Error sending activation success notification for {activation_id}: {str(e)}",
                exc_info=True
            )
            return False

    async def send_activation_failure(
        self,
        activation_id: UUID,
        activation_name: str,
        campaign_manager_email: str,
        campaign_manager_phone: str,
        failed_platforms: dict[str, str],
        partial_success: dict[str, str] | None = None
    ) -> bool:
        """Send failure notification when activation encounters errors.

        Builds formatted email and WhatsApp messages with failure details
        and sends them to the campaign manager.

        Args:
            activation_id: UUID of the activation
            activation_name: Human-readable activation name
            campaign_manager_email: Email address to send notification to
            campaign_manager_phone: Phone number to send WhatsApp to
            failed_platforms: Dict mapping platform names to error messages
            partial_success: Optional dict of platforms that succeeded

        Returns:
            True if both email and WhatsApp sent successfully, False otherwise
        """
        try:
            # Build email content
            email_subject = f"Campaign Activation Partial Failure: {activation_name}"

            failed_platforms_str = "\n".join(
                f"• {platform}: {reason}"
                for platform, reason in failed_platforms.items()
            )

            email_body = f"""
Your campaign activation encountered some issues.

Campaign: {activation_name}
Activation ID: {activation_id}
Status: PARTIAL FAILURE

Failed Platforms:
{failed_platforms_str}
"""

            if partial_success:
                successful_platforms_str = "\n".join(
                    f"• {platform}: {status}"
                    for platform, status in partial_success.items()
                )
                email_body += f"""
Successfully Active Platforms:
{successful_platforms_str}
"""

            email_body += """
Please review the errors above and take corrective action.
Contact support if you need assistance.

Thank you for using our platform.
            """

            # Build WhatsApp message
            failed_count = len(failed_platforms)
            whatsapp_message = f"""
Campaign "{activation_name}" encountered issues.

{failed_count} platform(s) failed to activate.
Failed: {', '.join(failed_platforms.keys())}
"""

            if partial_success:
                whatsapp_message += f"Active: {', '.join(partial_success.keys())}"

            whatsapp_message += "\nCheck dashboard for details."

            # Send both notifications
            email_result = await self.send_email(
                to_email=campaign_manager_email,
                subject=email_subject,
                body=email_body
            )

            whatsapp_result = await self.send_whatsapp(
                to_phone=campaign_manager_phone,
                message=whatsapp_message
            )

            success = email_result and whatsapp_result

            if success:
                logger.info(
                    f"Activation failure notification sent for {activation_id}",
                    extra={
                        "activation_name": activation_name,
                        "failed_platforms": list(failed_platforms.keys()),
                        "partial_success": list(partial_success.keys()) if partial_success else []
                    }
                )
            else:
                logger.warning(
                    f"Some notifications failed for activation {activation_id}",
                    extra={
                        "email_sent": email_result,
                        "whatsapp_sent": whatsapp_result
                    }
                )

            return success

        except Exception as e:
            logger.error(
                f"Error sending activation failure notification for {activation_id}: {str(e)}",
                exc_info=True
            )
            return False
