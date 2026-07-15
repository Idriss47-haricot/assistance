from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from .models import Ticket, Comment, Attachment
from .services import TicketWorkflowService, TicketAssignmentService

User = get_user_model()


class TicketModelTest(TestCase):
    """Tests du modèle Ticket"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.technician = User.objects.create_user(
            username='tech',
            email='tech@example.com',
            password='techpass123',
            role='TECHNICIAN'
        )
        self.ticket = Ticket.objects.create(
            title='Test Ticket',
            description='Test Description',
            priority='MEDIUM',
            created_by=self.user,
            assigned_to=self.technician
        )
    
    def test_ticket_creation(self):
        """Test la création d'un ticket"""
        self.assertEqual(self.ticket.title, 'Test Ticket')
        self.assertEqual(self.ticket.status, 'OPEN')
        self.assertIsNotNone(self.ticket.reference)
    
    def test_ticket_reference_generation(self):
        """Test la génération automatique de référence"""
        ticket2 = Ticket.objects.create(
            title='Ticket 2',
            description='Test',
            created_by=self.user
        )
        self.assertIsNotNone(ticket2.reference)
        self.assertTrue(ticket2.reference.startswith('T'))
    
    def test_ticket_change_status(self):
        """Test le changement de statut"""
        self.ticket.change_status('IN_PROGRESS', self.technician)
        self.assertEqual(self.ticket.status, 'IN_PROGRESS')
        
        self.ticket.change_status('RESOLVED', self.technician)
        self.assertEqual(self.ticket.status, 'RESOLVED')
        self.assertIsNotNone(self.ticket.resolved_at)
    
    def test_ticket_assign(self):
        """Test l'assignation d'un ticket"""
        self.ticket.assigned_to = None
        self.ticket.save()
        
        assigned = self.ticket.assign_technician(auto=True)
        self.assertEqual(assigned, self.technician)
    
    def test_invalid_status_transition(self):
        """Test les transitions invalides"""
        with self.assertRaises(ValueError):
            self.ticket.change_status('CLOSED', self.technician)  # OPEN -> CLOSED invalide


class TicketWorkflowServiceTest(TestCase):
    """Tests du service de workflow"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.tech = User.objects.create_user(
            username='tech',
            password='pass123',
            role='TECHNICIAN'
        )
        self.ticket = Ticket.objects.create(
            title='Test',
            description='Test',
            created_by=self.user,
            assigned_to=self.tech
        )
    
    def test_valid_transition(self):
        """Test une transition valide"""
        validation = TicketWorkflowService.validate_transition(
            self.ticket, 'IN_PROGRESS', self.tech
        )
        self.assertTrue(validation['valid'])
    
    def test_invalid_transition_permission(self):
        """Test une transition sans permission"""
        user2 = User.objects.create_user(username='user2', password='pass123')
        validation = TicketWorkflowService.validate_transition(
            self.ticket, 'RESOLVED', user2
        )
        self.assertFalse(validation['valid'])
        self.assertIn('permission', validation['error'].lower())
    
    def test_invalid_transition_status(self):
        """Test une transition de statut invalide"""
        validation = TicketWorkflowService.validate_transition(
            self.ticket, 'CLOSED', self.tech
        )
        self.assertFalse(validation['valid'])
    
    def test_change_status_with_comment(self):
        """Test le changement de statut avec commentaire"""
        TicketWorkflowService.change_status(
            self.ticket, 'RESOLVED', self.tech, 'Solution trouvée'
        )
        self.assertEqual(self.ticket.status, 'RESOLVED')
        self.assertTrue(
            self.ticket.comments.filter(content__icontains='Solution').exists()
        )


class TicketAPITest(TestCase):
    """Tests de l'API REST"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.token = self.get_token()
    
    def get_token(self):
        """Obtenir un token JWT pour l'API"""
        response = self.client.post('/api/token/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        return response.json().get('access')
    
    def test_api_create_ticket(self):
        """Test la création de ticket via API"""
        response = self.client.post('/api/tickets/', {
            'title': 'API Test',
            'description': 'API Test Description',
            'priority': 'HIGH'
        }, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['title'], 'API Test')
    
    def test_api_list_tickets(self):
        """Test la liste des tickets via API"""
        Ticket.objects.create(
            title='Test 1',
            description='Test',
            created_by=self.user
        )
        
        response = self.client.get('/api/tickets/', 
                                   HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.json()['results']) >= 1)
    
    def test_api_change_status(self):
        """Test le changement de statut via API"""
        ticket = Ticket.objects.create(
            title='Test',
            description='Test',
            created_by=self.user
        )
        
        response = self.client.post(f'/api/tickets/{ticket.id}/status/', {
            'status': 'IN_PROGRESS'
        }, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'IN_PROGRESS')


class DashboardTest(TestCase):
    """Tests du dashboard"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin',
            password='admin123',
            is_staff=True
        )
        self.client.login(username='admin', password='admin123')
    
    def test_dashboard_access(self):
        """Test l'accès au dashboard"""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_dashboard_stats(self):
        """Test les statistiques du dashboard"""
        response = self.client.get('/api/dashboard/stats/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('stats', data)
        self.assertIn('totals', data['stats'])


class SecurityTest(TestCase):
    """Tests de sécurité"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.admin = User.objects.create_user(
            username='admin',
            password='admin123',
            is_staff=True
        )
    
    def test_csrf_protection(self):
        """Test la protection CSRF"""
        response = self.client.post('/api/tickets/', {
            'title': 'Test',
            'description': 'Test'
        }, content_type='application/json')
        
        # Sans CSRF token, devrait échouer
        self.assertEqual(response.status_code, 403)
    
    def test_xss_protection(self):
        """Test la protection XSS"""
        ticket = Ticket.objects.create(
            title='<script>alert("XSS")</script>',
            description='Test',
            created_by=self.user
        )
        
        response = self.client.get(f'/api/tickets/{ticket.id}/')
        data = response.json()
        
        # Le titre devrait être échappé
        self.assertNotEqual(data['title'], '<script>alert("XSS")</script>')
    
    def test_file_upload_validation(self):
        """Test la validation des uploads"""
        # Tester l'upload d'un fichier PHP (devrait être refusé)
        with open('test.php', 'w') as f:
            f.write('<?php echo "hack"; ?>')
        
        response = self.client.post('/api/tickets/', {
            'title': 'Test',
            'description': 'Test',
            'attachments': open('test.php', 'rb')
        }, HTTP_AUTHORIZATION=f'Bearer {self.get_token()}')
        
        self.assertEqual(response.status_code, 400)
        
        import os
        os.remove('test.php')
    
    def get_token(self):
        response = self.client.post('/api/token/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        return response.json().get('access')


# Tests CI/CD - github/workflows/tests.yml
"""
name: Django CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install coverage flake8 pytest pytest-django
    
    - name: Lint with flake8
      run: |
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
    
    - name: Run migrations
      run: |
        python manage.py migrate
      env:
        DATABASE_URL: postgres://test:test@localhost:5432/test_db
    
    - name: Run tests with coverage
      run: |
        coverage run manage.py test apps
        coverage report --fail-under=80
      env:
        DATABASE_URL: postgres://test:test@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379/0
        DEBUG: False
"""