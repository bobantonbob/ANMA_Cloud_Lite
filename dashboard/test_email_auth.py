from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core import mail
from allauth.account.models import EmailAddress, EmailConfirmationHMAC

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}, ACCOUNT_RATE_LIMITS={})
class EmailAuthTests(TestCase):
    def test_signup_requires_confirmation_then_password_login(self):
        response = self.client.post('/register/', {'email': 'new@example.com', 'password1': 'Cloud-Test-8274!', 'password2': 'Cloud-Test-8274!'})
        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(email='new@example.com')
        self.assertTrue(user.check_password('Cloud-Test-8274!'))
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(len(mail.outbox), 1)
        address = EmailAddress.objects.get(user=user)
        self.assertFalse(address.verified)
        response = self.client.post('/login/', {'login': user.email, 'password': 'Cloud-Test-8274!'})
        self.assertNotIn('_auth_user_id', self.client.session)
        key = EmailConfirmationHMAC(address).key
        response = self.client.post('/accounts/confirm-email/' + key + '/')
        address.refresh_from_db()
        self.assertTrue(address.verified)
        self.client.post('/login/', {'login': user.email, 'password': 'Cloud-Test-8274!'})
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_wrong_password_and_external_redirect(self):
        user = get_user_model().objects.create_user('existing', email='existing@example.com', password='Cloud-Test-8274!')
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        self.client.post('/login/', {'login': user.email, 'password': 'incorrect'})
        self.assertNotIn('_auth_user_id', self.client.session)
        response = self.client.post('/login/', {'login': user.email, 'password': 'Cloud-Test-8274!', 'next': 'https://evil.example/'})
        self.assertFalse(response.get('Location', '').startswith('https://evil.example'))

    def test_reset_and_confirmation_use_brand_layout(self):
        for path in ['/accounts/password/reset/', '/accounts/confirm-email/']:
            response = self.client.get(path)
            self.assertContains(response, 'ANMA Cloud Lite')
            self.assertContains(response, 'auth-wrap')

    def test_duplicate_email_does_not_create_another_user(self):
        get_user_model().objects.create_user('existing', email='existing@example.com')
        self.client.post('/register/', {'email': 'existing@example.com', 'password1': 'Cloud-Test-8274!', 'password2': 'Cloud-Test-8274!'})
        self.assertEqual(get_user_model().objects.filter(email__iexact='existing@example.com').count(), 1)

    def test_demo_without_house(self):
        from dashboard.models import Plant
        user = get_user_model().objects.create_user('demo-viewer')
        self.client.force_login(user)
        response = self.client.get('/app/demo/')
        self.assertContains(response, '?data=live')
        self.assertContains(response, 'https://anma-electric.com.ua/')
        self.assertTrue(self.client.get('/app/demo/?data=live').json()['demo'])
        self.assertEqual(len(self.client.get('/app/demo/?data=history').json()['series']), 97)
        self.assertEqual(Plant.objects.count(), 0)
