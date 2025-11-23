# -*- coding: utf-8 -*-
"""
Services for handling donation-related operations, notifications, and PayMongo integration.
"""
from django.conf import settings
from notifications.services import NotificationService, send_realtime_notification
from accounts.models import User
import logging

logger = logging.getLogger(__name__)


def send_new_campaign_notification(campaign):
    """
    Send notification to all users when a new donation campaign is created.
    """
    try:
        # Get all active users (scouts and teachers)
        users = User.objects.filter(is_active=True)
        
        notification_data = {
            'title': 'New Donation Campaign',
            'message': f'A new donation campaign "{campaign.title}" has been created. Check it out!',
            'type': 'donation_campaign',
            'link': f'/donations/campaign/{campaign.id}/',
        }
        
        for user in users:
            # Create notification
            NotificationService.create_notification(
                user=user,
                title=notification_data['title'],
                message=notification_data['message'],
                notification_type='donation_campaign',
                link=notification_data['link']
            )
            
            # Send realtime notification
            send_realtime_notification(
                user_id=user.id,
                notification=notification_data
            )
        
        logger.info(f"Sent new campaign notifications for: {campaign.title}")
        
    except Exception as e:
        logger.error(f"Error sending new campaign notifications: {str(e)}")


def send_goal_reached_notification(campaign):
    """
    Send notification to all users when a campaign reaches its goal.
    """
    try:
        # Get all active users
        users = User.objects.filter(is_active=True)
        
        notification_data = {
            'title': 'Campaign Goal Reached! 🎉',
            'message': f'The "{campaign.title}" campaign has reached its fundraising goal of ₱{campaign.goal_amount}!',
            'type': 'goal_reached',
            'link': f'/donations/campaign/{campaign.id}/',
        }
        
        for user in users:
            # Create notification
            NotificationService.create_notification(
                user=user,
                title=notification_data['title'],
                message=notification_data['message'],
                notification_type='goal_reached',
                link=notification_data['link']
            )
            
            # Send realtime notification
            send_realtime_notification(
                user_id=user.id,
                notification=notification_data
            )
        
        logger.info(f"Sent goal reached notifications for: {campaign.title}")
        
    except Exception as e:
        logger.error(f"Error sending goal reached notifications: {str(e)}")


def send_donation_verified_notification(donation):
    """
    Send notification to donor when their donation is verified.
    """
    try:
        notification_data = {
            'title': 'Donation Verified',
            'message': f'Your donation of ₱{donation.amount} to "{donation.campaign.title}" has been verified. Thank you for your support!',
            'type': 'donation_verified',
            'link': f'/donations/history/',
        }
        
        # Create notification
        NotificationService.create_notification(
            user=donation.user,
            title=notification_data['title'],
            message=notification_data['message'],
            notification_type='donation_verified',
            link=notification_data['link']
        )
        
        # Send realtime notification
        send_realtime_notification(
            user_id=donation.user.id,
            notification=notification_data
        )
        
        logger.info(f"Sent donation verified notification to: {donation.user.email}")
        
    except Exception as e:
        logger.error(f"Error sending donation verified notification: {str(e)}")
