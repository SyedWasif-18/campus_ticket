from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Smart redirect index
    path('', views.index, name='index'),

    # Role-based dashboards
    path('faculty/', views.faculty_dashboard, name='faculty_dashboard'),
    path('attender/', views.attender_dashboard, name='attender_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/read/<int:notif_id>/', views.mark_notification_read, name='mark_read'),

    # AJAX / Chart.js API
    path('api/tickets/status/', views.api_tickets_by_status, name='api_status'),
    path('api/tickets/timeline/', views.api_tickets_over_time, name='api_timeline'),
    path('api/tickets/category/', views.api_tickets_by_category, name='api_category'),
    path('api/ratings/', views.api_rating_distribution, name='api_ratings'),

    # CSV Export
    path('export/tickets/', views.export_tickets_csv, name='export_tickets'),
]
