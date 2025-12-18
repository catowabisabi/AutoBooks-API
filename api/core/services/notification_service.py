"""
Notification Service
====================
Service layer for creating and sending notifications.
"""
from typing import List, Optional, Dict, Any
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model

from core.models_notifications import (
    Notification, NotificationPreference, NotificationLog,
    NotificationType, NotificationCategory, NotificationPriority
)

User = get_user_model()


class NotificationService:
    """
    Service for creating and managing notifications
    """
    
    @classmethod
    def create_notification(
        cls,
        user,
        title: str,
        message: str,
        notification_type: str = NotificationType.INFO,
        category: str = NotificationCategory.SYSTEM,
        priority: str = NotificationPriority.NORMAL,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        related_object_type: Optional[str] = None,
        related_object_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at=None,
        send_email: bool = False,
        send_push: bool = False,
    ) -> Notification:
        """
        Create a new notification for a user
        """
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            category=category,
            priority=priority,
            action_url=action_url,
            action_label=action_label,
            related_object_type=related_object_type,
            related_object_id=related_object_id,
            metadata=metadata or {},
            expires_at=expires_at,
        )
        
        # Log in-app notification
        NotificationLog.objects.create(
            notification=notification,
            user=user,
            channel='IN_APP',
            status='DELIVERED',
            recipient=str(user.id),
            content=message,
            delivered_at=timezone.now()
        )
        
        # Check user preferences and send via additional channels
        preferences = cls.get_user_preferences(user)
        
        if send_email and preferences.email_enabled:
            cls.send_email_notification(notification, user)
        
        if send_push and preferences.push_enabled:
            cls.send_push_notification(notification, user)
        
        return notification
    
    @classmethod
    def create_bulk_notification(
        cls,
        users: List,
        title: str,
        message: str,
        **kwargs
    ) -> List[Notification]:
        """
        Create notifications for multiple users
        """
        notifications = []
        for user in users:
            notification = cls.create_notification(
                user=user,
                title=title,
                message=message,
                **kwargs
            )
            notifications.append(notification)
        return notifications
    
    @classmethod
    def get_user_preferences(cls, user) -> NotificationPreference:
        """
        Get or create notification preferences for a user
        """
        preferences, _ = NotificationPreference.objects.get_or_create(user=user)
        return preferences
    
    @classmethod
    def send_email_notification(cls, notification: Notification, user) -> bool:
        """
        Send notification via email
        """
        try:
            subject = f"[{notification.category}] {notification.title}"
            
            # Simple HTML email
            html_message = f"""
            <html>
            <body>
                <h2>{notification.title}</h2>
                <p>{notification.message}</p>
                {f'<p><a href="{notification.action_url}">{notification.action_label or "View Details"}</a></p>' if notification.action_url else ''}
                <hr>
                <p style="color: #666; font-size: 12px;">
                    This is an automated notification from AutoBooks.
                </p>
            </body>
            </html>
            """
            
            plain_message = f"{notification.title}\n\n{notification.message}"
            if notification.action_url:
                plain_message += f"\n\nView: {notification.action_url}"
            
            # Create log entry
            log = NotificationLog.objects.create(
                notification=notification,
                user=user,
                channel='EMAIL',
                status='PENDING',
                recipient=user.email,
                subject=subject,
                content=plain_message,
            )
            
            # Send email
            sent = send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@autobooks.com'),
                recipient_list=[user.email],
                fail_silently=True,
            )
            
            # Update log
            if sent:
                log.status = 'SENT'
                log.sent_at = timezone.now()
            else:
                log.status = 'FAILED'
                log.error_message = 'Email sending failed'
            log.save()
            
            return bool(sent)
            
        except Exception as e:
            # Log the error
            NotificationLog.objects.create(
                notification=notification,
                user=user,
                channel='EMAIL',
                status='FAILED',
                recipient=user.email,
                content=notification.message,
                error_message=str(e)
            )
            return False
    
    @classmethod
    def send_push_notification(cls, notification: Notification, user) -> bool:
        """
        Send push notification (placeholder for future implementation)
        """
        # Create log entry
        log = NotificationLog.objects.create(
            notification=notification,
            user=user,
            channel='PUSH',
            status='PENDING',
            recipient=str(user.id),
            subject=notification.title,
            content=notification.message,
        )
        
        # TODO: Implement actual push notification via Firebase/OneSignal/etc.
        # For now, just log it as sent
        log.status = 'SENT'
        log.sent_at = timezone.now()
        log.save()
        
        return True
    
    @classmethod
    def mark_as_read(cls, notification_ids: List[str], user) -> int:
        """
        Mark notifications as read
        Returns count of updated notifications
        """
        return Notification.objects.filter(
            id__in=notification_ids,
            user=user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
    
    @classmethod
    def mark_all_as_read(cls, user) -> int:
        """
        Mark all notifications as read for a user
        """
        return Notification.objects.filter(
            user=user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
    
    @classmethod
    def get_unread_count(cls, user) -> int:
        """
        Get count of unread notifications
        """
        return Notification.objects.filter(
            user=user,
            is_read=False
        ).count()
    
    @classmethod
    def get_notification_counts(cls, user) -> Dict[str, Any]:
        """
        Get notification counts by category and type
        """
        from django.db.models import Count
        
        notifications = Notification.objects.filter(user=user)
        
        total = notifications.count()
        unread = notifications.filter(is_read=False).count()
        
        by_category = dict(
            notifications.values('category').annotate(count=Count('id')).values_list('category', 'count')
        )
        
        by_type = dict(
            notifications.values('notification_type').annotate(count=Count('id')).values_list('notification_type', 'count')
        )
        
        return {
            'total': total,
            'unread': unread,
            'by_category': by_category,
            'by_type': by_type,
        }
    
    @classmethod
    def delete_old_notifications(cls, days: int = 30) -> int:
        """
        Delete notifications older than specified days
        """
        cutoff = timezone.now() - timezone.timedelta(days=days)
        count, _ = Notification.objects.filter(
            created_at__lt=cutoff,
            is_read=True
        ).delete()
        return count
    
    # Convenience methods for common notification types
    
    @classmethod
    def notify_invoice_paid(cls, user, invoice):
        """Notify user that an invoice has been paid"""
        return cls.create_notification(
            user=user,
            title="Invoice Paid",
            message=f"Invoice #{invoice.invoice_number} has been paid in full.",
            notification_type=NotificationType.SUCCESS,
            category=NotificationCategory.INVOICES,
            related_object_type='Invoice',
            related_object_id=str(invoice.id),
            action_url=f"/dashboard/accounting/invoices/{invoice.id}",
            action_label="View Invoice",
            send_email=True,
        )
    
    @classmethod
    def notify_expense_approved(cls, user, expense):
        """Notify user that an expense has been approved"""
        return cls.create_notification(
            user=user,
            title="Expense Approved",
            message=f"Your expense '{expense.description}' has been approved.",
            notification_type=NotificationType.SUCCESS,
            category=NotificationCategory.EXPENSES,
            related_object_type='Expense',
            related_object_id=str(expense.id),
        )
    
    @classmethod
    def notify_expense_rejected(cls, user, expense, reason: str = None):
        """Notify user that an expense has been rejected"""
        message = f"Your expense '{expense.description}' has been rejected."
        if reason:
            message += f" Reason: {reason}"
        
        return cls.create_notification(
            user=user,
            title="Expense Rejected",
            message=message,
            notification_type=NotificationType.WARNING,
            category=NotificationCategory.EXPENSES,
            related_object_type='Expense',
            related_object_id=str(expense.id),
        )
    
    @classmethod
    def notify_payment_reminder(cls, user, invoice, days_overdue: int):
        """Send payment reminder notification"""
        return cls.create_notification(
            user=user,
            title="Payment Reminder",
            message=f"Invoice #{invoice.invoice_number} is {days_overdue} days overdue. Amount due: ${invoice.amount_due}",
            notification_type=NotificationType.REMINDER,
            category=NotificationCategory.INVOICES,
            priority=NotificationPriority.HIGH,
            related_object_type='Invoice',
            related_object_id=str(invoice.id),
            action_url=f"/dashboard/accounting/invoices/{invoice.id}",
            action_label="View Invoice",
            send_email=True,
        )
    
    @classmethod
    def notify_deadline_approaching(cls, user, task, days_until: int):
        """Notify about approaching deadline"""
        return cls.create_notification(
            user=user,
            title="Deadline Approaching",
            message=f"Task '{task.title}' is due in {days_until} day(s).",
            notification_type=NotificationType.DEADLINE,
            category=NotificationCategory.TASKS,
            priority=NotificationPriority.HIGH if days_until <= 1 else NotificationPriority.NORMAL,
            related_object_type='Task',
            related_object_id=str(task.id),
        )
    
    @classmethod
    def notify_approval_request(cls, user, item_type: str, item_id: str, requester_name: str):
        """Notify about approval request"""
        return cls.create_notification(
            user=user,
            title="Approval Required",
            message=f"{requester_name} has submitted a {item_type} for your approval.",
            notification_type=NotificationType.APPROVAL,
            category=NotificationCategory.ACCOUNTING,
            priority=NotificationPriority.HIGH,
            related_object_type=item_type,
            related_object_id=item_id,
            action_url=f"/dashboard/finance/approvals",
            action_label="Review",
        )
