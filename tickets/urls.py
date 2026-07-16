from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('raise/', views.raise_ticket, name='raise_ticket'),
    path('list/', views.ticket_list, name='ticket_list'),
    path('<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('<int:ticket_id>/cancel/', views.cancel_ticket, name='cancel_ticket'),
    path('<int:ticket_id>/accept/', views.accept_ticket, name='accept_ticket'),
    path('<int:ticket_id>/status/', views.update_ticket_status, name='update_ticket_status'),
    path('<int:ticket_id>/rate/', views.submit_rating, name='submit_rating'),
    
    # Department Management (Admin)
    path('departments/', views.manage_departments, name='manage_departments'),
    path('departments/<int:dept_id>/edit/', views.edit_department, name='edit_department'),
    path('departments/<int:dept_id>/delete/', views.delete_department, name='delete_department'),
    
    # Room Management (Admin)
    path('rooms/', views.manage_rooms, name='manage_rooms'),
    path('rooms/<int:room_id>/edit/', views.edit_room, name='edit_room'),
    path('rooms/<int:room_id>/delete/', views.delete_room, name='delete_room'),
    path('rooms/<int:room_id>/qr/', views.download_qr, name='download_qr'),
    path('rooms/qr/all/', views.download_all_qrs, name='download_all_qrs'),
]

