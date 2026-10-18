from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect


def auth_context(request):
    return {'google_ready': bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)}


class GoogleOnlyAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        verified = any(e.verified and e.email for e in sociallogin.email_addresses)
        if sociallogin.account.provider != 'google' or not verified:
            messages.error(request, 'Потрібен обліковий запис Google з підтвердженою поштою.')
            raise ImmediateHttpResponse(redirect('login'))

    def is_open_for_signup(self, request, sociallogin):
        return sociallogin.account.provider == 'google' and any(e.verified for e in sociallogin.email_addresses)
