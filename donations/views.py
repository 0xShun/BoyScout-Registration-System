# -*- coding: utf-8 -*-
"""
Views for the donations app.
Handles campaign listing, donations, admin management, and PayMongo integration.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from decimal import Decimal
import json
import logging
import base64
import requests

from .models import DonationCampaign, Donation
from .forms import DonationCampaignForm, DonationForm
from .services import send_new_campaign_notification, send_donation_verified_notification
from django.conf import settings

logger = logging.getLogger(__name__)


def admin_required(view_func):
    """Decorator to require admin access"""
    return user_passes_test(lambda u: u.is_authenticated and u.is_admin())(view_func)


# ============================================================================
# PUBLIC/SCOUT/TEACHER VIEWS
# ============================================================================

@login_required
def campaign_list(request):
    """
    Display list of donation campaigns for scouts and teachers.
    Active campaigns shown first, then inactive.
    """
    # Get filter from query params
    status_filter = request.GET.get('status', 'all')
    
    # Base queryset
    campaigns = DonationCampaign.objects.all()
    
    # Apply status filter
    if status_filter == 'active':
        campaigns = campaigns.filter(status='active')
    elif status_filter == 'inactive':
        campaigns = campaigns.filter(status='inactive')
    
    # For better ordering, let's manually sort
    active_campaigns = list(campaigns.filter(status='active').order_by('-created_at'))
    inactive_campaigns = list(campaigns.filter(status='inactive').order_by('-created_at'))
    campaigns = active_campaigns + inactive_campaigns
    
    context = {
        'campaigns': campaigns,
        'status_filter': status_filter,
    }
    
    return render(request, 'donations/campaign_list.html', context)


@login_required
def campaign_detail(request, pk):
    """
    Display detailed view of a donation campaign.
    Shows campaign info, progress, and donation form.
    """
    campaign = get_object_or_404(DonationCampaign, pk=pk)
    
    # Get recent donations (non-anonymous or user's own)
    recent_donations = campaign.donations.filter(
        status='verified'
    ).filter(
        Q(is_anonymous=False) | Q(user=request.user)
    ).select_related('user').order_by('-created_at')[:10]
    
    # Calculate statistics
    total_donors = campaign.donations.filter(status='verified').values('user').distinct().count()
    
    context = {
        'campaign': campaign,
        'recent_donations': recent_donations,
        'total_donors': total_donors,
        'donation_form': DonationForm(),
    }
    
    return render(request, 'donations/campaign_detail.html', context)


@login_required
@require_POST
def initiate_donation(request, pk):
    """
    Initiate a donation to a campaign.
    Creates PayMongo source and returns QR code for scanning.
    """
    campaign = get_object_or_404(DonationCampaign, pk=pk)
    
    # Check if campaign is active
    if not campaign.is_active:
        messages.error(request, "This campaign is not currently active.")
        return redirect('donations:campaign_detail', pk=pk)
    
    form = DonationForm(request.POST)
    
    if form.is_valid():
        try:
            # Create donation record
            donation = form.save(commit=False)
            donation.campaign = campaign
            donation.user = request.user
            donation.status = 'pending'
            donation.save()
            
            logger.info(f"Donation created: ID={donation.id}, User={request.user.email}, Campaign={campaign.title}, Amount=P{donation.amount}")
            
            messages.success(request, "Donation initiated! You will be redirected to the payment page.")
            return redirect('donations:donation_payment', donation_id=donation.id)
                
        except Exception as e:
            logger.error(f"Error initiating donation: {str(e)}")
            messages.error(request, f"An error occurred: {str(e)}")
    
    else:
        for error in form.errors.values():
            messages.error(request, error)
    
    return redirect('donations:campaign_detail', pk=pk)


@login_required
def donation_payment(request, donation_id):
    """
    Display payment page with PayMongo QR code.
    """
    donation = get_object_or_404(Donation, pk=donation_id, user=request.user)
    
    # Only show payment page for pending donations
    if donation.status != 'pending':
        messages.info(request, "This donation has already been processed.")
        return redirect('donations:donation_history')
    
    # Create PayMongo source if not already created
    if not donation.paymongo_source_id:
        try:
            from payments.services.paymongo_service import PayMongoService
            paymongo = PayMongoService()
            
            logger.info(f"Creating PayMongo source for donation {donation.id}, amount=P{donation.amount}")
            
            # Build redirect URLs
            from django.urls import reverse
            success_url = request.build_absolute_uri(reverse('donations:donation_history'))
            failed_url = request.build_absolute_uri(reverse('donations:campaign_detail', args=[donation.campaign.pk]))
            
            success, source_response = paymongo.create_source(
                amount=float(donation.amount),
                description=f"Donation to {donation.campaign.title}",
                redirect_success=success_url,
                redirect_failed=failed_url,
                metadata={
                    'donation_id': str(donation.id),
                    'campaign_id': str(donation.campaign.id),
                    'user_id': str(request.user.id)
                }
            )
            
            if success and source_response:
                source_data = source_response.get('data', {})
                donation.paymongo_source_id = source_data.get('id')
                donation.gateway_response = source_response
                donation.save()
                logger.info(f"PayMongo source created: {donation.paymongo_source_id}")
            else:
                logger.error(f"PayMongo source creation failed: {source_response}")
                messages.error(request, "Failed to generate payment link. Please try again.")
                return redirect('donations:campaign_detail', pk=donation.campaign.pk)
        except Exception as e:
            logger.error(f"Error creating PayMongo source: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, "Failed to generate payment QR code. Please try again.")
            return redirect('donations:campaign_detail', pk=donation.campaign.pk)
    
    context = {
        'donation': donation,
        'campaign': donation.campaign,
    }
    
    return render(request, 'donations/donation_payment.html', context)


@login_required
def donation_history(request):
    """
    Show donation history for the logged-in user.
    """
    donations = Donation.objects.filter(
        user=request.user
    ).select_related('campaign').order_by('-created_at')
    
    # Calculate total donated
    total_donated = donations.filter(status='verified').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    # Pagination
    paginator = Paginator(donations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'donations': page_obj,
        'total_donated': total_donated,
    }
    
    return render(request, 'donations/donation_history.html', context)


# ============================================================================
# ADMIN VIEWS
# ============================================================================

@login_required
@admin_required
def admin_campaign_list(request):
    """
    Admin view to list and manage all campaigns.
    """
    # Get filter from query params
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    campaigns = DonationCampaign.objects.all()
    
    # Apply search
    if search_query:
        campaigns = campaigns.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Apply status filter
    if status_filter == 'active':
        campaigns = campaigns.filter(status='active')
    elif status_filter == 'inactive':
        campaigns = campaigns.filter(status='inactive')
    
    # Order
    campaigns = campaigns.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(campaigns, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'campaigns': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'donations/admin/campaign_list.html', context)


@login_required
@admin_required
def admin_campaign_create(request):
    """
    Admin view to create a new donation campaign.
    """
    if request.method == 'POST':
        form = DonationCampaignForm(request.POST, request.FILES)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.created_by = request.user
            campaign.save()
            
            messages.success(request, f'Campaign "{campaign.title}" created successfully!')
            
            # Send notifications to all users
            send_new_campaign_notification(campaign)
            
            return redirect('donations:admin_campaign_list')
    else:
        form = DonationCampaignForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    
    return render(request, 'donations/admin/campaign_form.html', context)


@login_required
@admin_required
def admin_campaign_edit(request, pk):
    """
    Admin view to edit an existing campaign.
    """
    campaign = get_object_or_404(DonationCampaign, pk=pk)
    
    if request.method == 'POST':
        form = DonationCampaignForm(request.POST, request.FILES, instance=campaign)
        if form.is_valid():
            form.save()
            messages.success(request, f'Campaign "{campaign.title}" updated successfully!')
            return redirect('donations:admin_campaign_list')
    else:
        form = DonationCampaignForm(instance=campaign)
    
    context = {
        'form': form,
        'campaign': campaign,
        'action': 'Edit',
    }
    
    return render(request, 'donations/admin/campaign_form.html', context)


@login_required
@admin_required
def admin_campaign_delete(request, pk):
    """
    Admin view to delete a campaign.
    """
    campaign = get_object_or_404(DonationCampaign, pk=pk)
    
    if request.method == 'POST':
        title = campaign.title
        campaign.delete()
        messages.success(request, f'Campaign "{title}" deleted successfully!')
        return redirect('donations:admin_campaign_list')
    
    context = {
        'campaign': campaign,
    }
    
    return render(request, 'donations/admin/campaign_delete_confirm.html', context)


@login_required
@admin_required
def admin_campaign_donations(request, pk):
    """
    Admin view to see all donations for a specific campaign.
    """
    campaign = get_object_or_404(DonationCampaign, pk=pk)
    
    # Get all donations for this campaign
    donations = campaign.donations.all().select_related('user').order_by('-created_at')
    
    # Get filter
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        donations = donations.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(donations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate stats
    total_raised = campaign.donations.filter(status='verified').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    total_donors = campaign.donations.filter(status='verified').values('user').distinct().count()
    
    context = {
        'campaign': campaign,
        'donations': page_obj,
        'status_filter': status_filter,
        'total_raised': total_raised,
        'total_donors': total_donors,
    }
    
    return render(request, 'donations/admin/campaign_donations.html', context)


@login_required
@admin_required
def admin_all_donations(request):
    """
    Admin view to see all donations across all campaigns.
    """
    # Get filters
    status_filter = request.GET.get('status', 'all')
    campaign_filter = request.GET.get('campaign', 'all')
    
    # Base queryset
    donations = Donation.objects.all().select_related('user', 'campaign')
    
    # Apply filters
    if status_filter != 'all':
        donations = donations.filter(status=status_filter)
    
    if campaign_filter != 'all':
        donations = donations.filter(campaign_id=campaign_filter)
    
    # Order
    donations = donations.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(donations, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all campaigns for filter dropdown
    campaigns = DonationCampaign.objects.all().order_by('title')
    
    # Calculate stats
    total_raised = Donation.objects.filter(status='verified').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    context = {
        'donations': page_obj,
        'campaigns': campaigns,
        'status_filter': status_filter,
        'campaign_filter': campaign_filter,
        'total_raised': total_raised,
    }
    
    return render(request, 'donations/admin/all_donations.html', context)


@login_required
@admin_required
def admin_donations_report(request):
    """
    Generate CSV report of all donations.
    """
    import csv
    from django.utils.text import slugify
    
    # Get all verified donations
    donations = Donation.objects.filter(status='verified').select_related('user', 'campaign').order_by('-created_at')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    today = timezone.now().strftime('%Y-%m-%d')
    response['Content-Disposition'] = f'attachment; filename="donations_report_all_{today}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Donor Name', 'Email', 'Campaign', 'Amount', 'Date', 'Payment Method', 'Anonymous'])
    
    for donation in donations:
        donor_name = "Anonymous" if donation.is_anonymous else donation.user.get_full_name()
        writer.writerow([
            donor_name,
            donation.user.email if not donation.is_anonymous else 'Hidden',
            donation.campaign.title,
            f"₱{donation.amount:.2f}",
            donation.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            donation.payment_method,
            'Yes' if donation.is_anonymous else 'No',
        ])
    
    return response


@login_required
@admin_required
def admin_campaign_report(request, pk):
    """
    Generate CSV report for a specific campaign.
    """
    import csv
    from django.utils.text import slugify
    
    campaign = get_object_or_404(DonationCampaign, pk=pk)
    
    # Get all verified donations for this campaign
    donations = campaign.donations.filter(status='verified').select_related('user').order_by('-created_at')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    today = timezone.now().strftime('%Y-%m-%d')
    campaign_slug = slugify(campaign.title)
    response['Content-Disposition'] = f'attachment; filename="donations_report_{campaign_slug}_{today}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Donor Name', 'Email', 'Amount', 'Date', 'Payment Method', 'Message', 'Anonymous'])
    
    for donation in donations:
        donor_name = "Anonymous" if donation.is_anonymous else donation.user.get_full_name()
        writer.writerow([
            donor_name,
            donation.user.email if not donation.is_anonymous else 'Hidden',
            f"₱{donation.amount:.2f}",
            donation.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            donation.payment_method,
            donation.message[:100] if donation.message else '',
            'Yes' if donation.is_anonymous else 'No',
        ])
    
    return response


# ============================================================================
# WEBHOOK
# ============================================================================

@csrf_exempt
@require_POST
def donation_webhook(request):
    """
    Handle PayMongo webhooks for donation payments.
    Auto-verify donations when payment is confirmed.
    """
    try:
        payload = json.loads(request.body)
        event_type = payload.get('data', {}).get('attributes', {}).get('type')
        
        logger.info(f"Received donation webhook: {event_type}")
        
        if event_type == 'source.chargeable':
            # Payment is ready to be charged
            source_data = payload['data']['attributes']['data']
            source_id = source_data['id']
            source_attrs = source_data.get('attributes', {})
            source_amount_centavos = source_attrs.get('amount', 0)
            source_amount = Decimal(str(source_amount_centavos / 100.0))
            
            logger.info(f"💰 [DONATION WEBHOOK] source.chargeable: {source_id} | Amount: ₱{source_amount}")
            
            # Find donation with this source_id
            try:
                donation = Donation.objects.get(paymongo_source_id=source_id)
                
                # Mark as verified and set verified timestamp
                donation.status = 'verified'
                donation.verified_at = timezone.now()
                donation.save()
                
                # Update campaign's current_amount from verified donations
                campaign = donation.campaign
                goal_just_reached = campaign.update_current_amount()
                
                logger.info(f"✅ Donation {donation.id} verified | Campaign '{campaign.title}' now at ₱{campaign.current_amount}/{campaign.goal_amount or 'No Goal'}")
                
                if goal_just_reached:
                    logger.info(f"🎯 Campaign '{campaign.title}' just reached its goal!")
                
                # Send notification to donor
                send_donation_verified_notification(donation)
                
                # Send notification to admins
                from accounts.models import User
                admin_users = User.objects.filter(role='admin', is_active=True)
                for admin in admin_users:
                    try:
                        from notifications.services import send_realtime_notification
                        send_realtime_notification(
                            user_id=admin.id,
                            message=f'New donation: ₱{donation.amount} to {campaign.title} from {donation.user.get_full_name()}',
                            notification_type='donation_received'
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify admin {admin.id}: {str(e)}")
                
            except Donation.DoesNotExist:
                logger.warning(f"❌ Donation not found for source_id: {source_id}")
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
