from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from datetime import timedelta
import csv
import json
from datetime import datetime
from .models import AnalyticsEvent, AuditLog
from django.db.models.functions import TruncDate, TruncMonth
from payments.models import Payment
from accounts.models import User
from boyscout_system.utils import render_to_pdf
from announcements.models import Announcement
from events.models import Event
from django.core.paginator import Paginator

@login_required
def export_analytics(request, format):
    """
    Export analytics data in the specified format (csv or json)
    Supports filtering by date range and event type
    """
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    event_type = request.GET.get('event_type')

    # Base queryset
    queryset = AnalyticsEvent.objects.all()

    # Apply filters
    if start_date:
        queryset = queryset.filter(timestamp__gte=start_date)
    if end_date:
        queryset = queryset.filter(timestamp__lte=end_date)
    if event_type:
        queryset = queryset.filter(event_type=event_type)

    # Get the data
    data = []
    for event in queryset:
        data.append({
            'timestamp': event.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'event_type': event.event_type,
            'user': event.user.username if event.user else 'Anonymous',
            'page_url': event.page_url,
            'ip_address': str(event.ip_address) if event.ip_address else '',
            'metadata': json.dumps(event.metadata)
        })

    # Generate summary statistics
    summary = {
        'total_events': queryset.count(),
        'events_by_type': dict(queryset.values_list('event_type').annotate(count=Count('id'))),
        'unique_users': queryset.values('user').distinct().count(),
    }

    if format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="analytics_{datetime.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.DictWriter(response, fieldnames=['timestamp', 'event_type', 'user', 'page_url', 'ip_address', 'metadata'])
        writer.writeheader()
        writer.writerows(data)
        
    elif format == 'json':
        response_data = {
            'data': data,
            'summary': summary
        }
        response = HttpResponse(json.dumps(response_data, indent=2), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="analytics_{datetime.now().strftime("%Y%m%d")}.json"'
    
    elif format == 'pdf':
        response = render_to_pdf(
            'analytics/report_template.html',
            {
                'data': data,
                'summary': summary
            }
        )
        if response:
            filename = f"analytics_{datetime.now().strftime('%Y%m%d')}.pdf"
            content = f"attachment; filename={filename}"
            response['Content-Disposition'] = content
            return response
        else:
            return HttpResponse("Error generating PDF", status=500)

    else:
        return HttpResponse('Unsupported format', status=400)
    
    return response 

@user_passes_test(lambda u: u.is_staff)
@login_required
def analytics_dashboard(request):
    # Filtering
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    event_type = request.GET.get('event_type')
    queryset = AnalyticsEvent.objects.all()
    if start_date:
        queryset = queryset.filter(timestamp__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(timestamp__date__lte=end_date)
    if event_type:
        queryset = queryset.filter(event_type=event_type)
    # Summary statistics
    total_events = queryset.count()
    events_by_type = queryset.values('event_type').annotate(count=Count('id'))
    unique_users = queryset.values('user').distinct().count()
    recent_events = queryset.order_by('-timestamp')[:20]
    # Data for advanced charts
    # Pie chart: event type distribution
    pie_data = list(events_by_type)
    # Stacked bar: events by type over time (last 14 days)
    from datetime import timedelta, date
    today = date.today()
    days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    day_labels = [d.strftime('%Y-%m-%d') for d in days]
    types = [et['event_type'] for et in events_by_type]
    stacked_data = {t: [0]*14 for t in types}
    events_by_day = queryset.annotate(day=TruncDate('timestamp')).values('day', 'event_type').annotate(count=Count('id'))
    day_index = {d: i for i, d in enumerate(day_labels)}
    for row in events_by_day:
        day_str = row['day'].strftime('%Y-%m-%d')
        if row['event_type'] in stacked_data and day_str in day_index:
            stacked_data[row['event_type']][day_index[day_str]] = row['count']
    return render(request, 'analytics/dashboard.html', {
        'total_events': total_events,
        'events_by_type': events_by_type,
        'unique_users': unique_users,
        'recent_events': recent_events,
        'pie_data': pie_data,
        'stacked_data': stacked_data,
        'day_labels': day_labels,
        'types': types,
        'filter_start_date': start_date or '',
        'filter_end_date': end_date or '',
        'filter_event_type': event_type or '',
    }) 

def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_admin())(view_func)

@admin_required
def financial_dashboard(request):
    # Get date range
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    # Monthly payment trends
    monthly_payments = (
        Payment.objects.filter(
            date__gte=start_date,
            status='verified'
        )
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        .order_by('month')
    )
    
    # Payment status distribution
    status_distribution = (
        Payment.objects.filter(date__gte=start_date)
        .values('status')
        .annotate(count=Count('id'))
    )
    
    # Top paying members
    top_payers = (
        User.objects.filter(
            payments__date__gte=start_date,
            payments__status='verified'
        )
        .annotate(total_paid=Sum('payments__amount'))
        .order_by('-total_paid')[:5]
    )
    
    # Payment verification time
    verification_times = (
        Payment.objects.filter(
            date__gte=start_date,
            status__in=['verified', 'rejected'],
            verification_date__isnull=False
        )
        .annotate(
            verification_time=timezone.now() - timezone.timedelta(days=1)
        )
    )
    
    context = {
        'monthly_payments': json.dumps(list(monthly_payments)),
        'status_distribution': json.dumps(list(status_distribution)),
        'top_payers': top_payers,
        'verification_times': verification_times,
        'total_revenue': Payment.objects.filter(
            date__gte=start_date,
            status='verified'
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'pending_amount': Payment.objects.filter(
            date__gte=start_date,
            status='pending'
        ).aggregate(total=Sum('amount'))['total'] or 0,
    }
    
    return render(request, 'analytics/financial_dashboard.html', context)

@admin_required
def payment_report(request):
    # Get date range from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Base queryset
    payments = Payment.objects.all()
    
    if start_date:
        payments = payments.filter(date__gte=start_date)
    if end_date:
        payments = payments.filter(date__lte=end_date)
    
    # Group by status
    status_summary = (
        payments
        .values('status')
        .annotate(
            count=Count('id'),
            total=Sum('amount')
        )
    )
    
    # Group by month
    monthly_summary = (
        payments
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(
            count=Count('id'),
            total=Sum('amount')
        )
        .order_by('month')
    )
    
    context = {
        'status_summary': status_summary,
        'monthly_summary': monthly_summary,
        'total_amount': payments.aggregate(total=Sum('amount'))['total'] or 0,
        'total_count': payments.count(),
    }
    
    return render(request, 'analytics/payment_report.html', context)

@admin_required
def engagement_dashboard(request):
    # Announcement engagement
    announcement_engagement = (
        Announcement.objects.annotate(
            reads=Count('read_by'),
            recipients_count=Count('recipients')
        )
        .order_by('-date_posted')[:10]
    )

    # Event participation
    event_participation = (
        Event.objects.annotate(
            participant_count=Count('participants')
        )
        .order_by('-date')[:10]
    )

    # User engagement score (example metric)
    user_engagement = (
        User.objects.annotate(
            payments_made=Count('payments', filter=models.Q(payments__status='verified')),
            announcements_read=Count('read_announcements'),
            events_attended=Count('attended_events')
        )
        .annotate(
            engagement_score=(
                models.F('payments_made') * 3 +
                models.F('announcements_read') * 1 +
                models.F('events_attended') * 2
            )
        )
        .order_by('-engagement_score')[:10]
    )

    context = {
        'announcement_engagement': announcement_engagement,
        'event_participation': event_participation,
        'user_engagement': user_engagement,
    }
    return render(request, 'analytics/engagement_dashboard.html', context)

@admin_required
def audit_log_view(request):
    logs = AuditLog.objects.all()
    paginator = Paginator(logs, 20)  # Show 20 logs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'analytics/audit_log.html', {'page_obj': page_obj}) 