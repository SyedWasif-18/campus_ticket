from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser
from tickets.models import Department, Room, Ticket

class DashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.dept = Department.objects.create(name='Computer Science', code='CSE')
        self.room = Room.objects.create(room_number='101', floor='1', department=self.dept)
        
        self.faculty = CustomUser.objects.create_user(
            username='faculty_user', password='password123', role='FACULTY'
        )
        self.attender = CustomUser.objects.create_user(
            username='attender_user', password='password123', role='ATTENDER', department=self.dept
        )
        self.admin = CustomUser.objects.create_superuser(
            username='admin_user', password='password123', role='ADMIN'
        )
        
        self.ticket = Ticket.objects.create(
            faculty=self.faculty,
            room=self.room,
            category='TECHNICAL',
            sub_category='Projector',
            status='PENDING'
        )

    def test_redirect_index_faculty(self):
        self.client.login(username='faculty_user', password='password123')
        response = self.client.get(reverse('dashboard:index'))
        self.assertRedirects(response, reverse('dashboard:faculty_dashboard'))
        
    def test_redirect_index_attender(self):
        self.client.login(username='attender_user', password='password123')
        response = self.client.get(reverse('dashboard:index'))
        self.assertRedirects(response, reverse('dashboard:attender_dashboard'))

    def test_redirect_index_admin(self):
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(reverse('dashboard:index'))
        self.assertRedirects(response, reverse('dashboard:admin_dashboard'))

    def test_faculty_dashboard_access(self):
        self.client.login(username='faculty_user', password='password123')
        response = self.client.get(reverse('dashboard:faculty_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome back')
        
    def test_attender_dashboard_access(self):
        self.client.login(username='attender_user', password='password123')
        response = self.client.get(reverse('dashboard:attender_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Attender Dashboard')
        # Should see the pending ticket for their dept
        self.assertContains(response, '#1')

    def test_admin_dashboard_access(self):
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(reverse('dashboard:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Dashboard')

    def test_api_endpoints_admin_only(self):
        # Faculty should be denied
        self.client.login(username='faculty_user', password='password123')
        response = self.client.get(reverse('dashboard:api_status'))
        self.assertEqual(response.status_code, 302)  # Redirects due to admin_required
        
        # Admin should get JSON
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(reverse('dashboard:api_status'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('PENDING', response.json())
