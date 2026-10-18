from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from allauth.core import context
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialLogin
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.internal.flows.login import complete_login

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', ACCOUNT_RATE_LIMITS={}, STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class GoogleExistingTests(TestCase):
    def google_login(self, verified=True):
        request = RequestFactory().get('/accounts/google/login/callback/')
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)
        request.user = AnonymousUser()
        with context.request_context(request):
            provider = get_adapter(request).get_provider(request, 'google')
            social = SocialLogin(user=get_user_model()(email='owner@example.com'), account=SocialAccount(provider='google', uid='google-test-owner'), email_addresses=[EmailAddress(email='owner@example.com', verified=verified, primary=True)], provider=provider)
            response = complete_login(request, social)
        return request, response

    def test_verified_google_connects_existing_account_and_repeats(self):
        from django.core import mail
        user = get_user_model().objects.create_user('owner', email='owner@example.com', password='Cloud-Test-8274!')
        EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=True)
        for attempt in range(2):
            request, response = self.google_login()
            self.assertEqual(response.status_code, 302)
            self.assertEqual(int(request.session['_auth_user_id']), user.pk)
            self.assertNotIn('signup', response.url)
        self.assertEqual(SocialAccount.objects.get(provider='google').user_id, user.pk)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)
        user.refresh_from_db()
        self.assertTrue(user.check_password('Cloud-Test-8274!'))

    def test_unverified_google_cannot_connect(self):
        get_user_model().objects.create_user('owner', email='owner@example.com')
        request, response = self.google_login(verified=False)
        self.assertNotIn('_auth_user_id', request.session)
        self.assertFalse(SocialAccount.objects.exists())
