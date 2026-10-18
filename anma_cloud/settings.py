import os
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR=Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env', override=False, encoding='utf-8-sig')
SECRET_KEY=os.getenv('DJANGO_SECRET_KEY','dev-only-change-before-publication')
DEBUG=os.getenv('DJANGO_DEBUG','0')=='1'
ALLOWED_HOSTS=[x.strip() for x in os.getenv('DJANGO_ALLOWED_HOSTS','localhost,127.0.0.1').split(',') if x.strip()]
CSRF_TRUSTED_ORIGINS=[x.strip() for x in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS','').split(',') if x.strip()]
# The production container is served through an HTTPS reverse proxy.
# Local requests without this header keep their original HTTP scheme.
SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')
INSTALLED_APPS=['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','dashboard']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='anma_cloud.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.debug','django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='anma_cloud.wsgi.application'
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3'}}
AUTH_PASSWORD_VALIDATORS=[{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':10}},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE='uk'
TIME_ZONE='Europe/Kyiv'
USE_I18N=True
USE_TZ=True
STATIC_URL='static/'
STATICFILES_DIRS=[BASE_DIR/'static']
STATIC_ROOT=BASE_DIR/'staticfiles'
STORAGES={'staticfiles':{'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
LOGIN_URL='login';LOGIN_REDIRECT_URL='dashboard';LOGOUT_REDIRECT_URL='landing'
SESSION_COOKIE_HTTPONLY=True
CSRF_COOKIE_HTTPONLY=True
SESSION_COOKIE_SECURE=not DEBUG
CSRF_COOKIE_SECURE=not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF=True
X_FRAME_OPTIONS='DENY'

# One explicitly bound local HA installation. These values never enter templates.
HA_URL=os.getenv('HA_URL','').rstrip('/')
HA_TOKEN=os.getenv('HA_TOKEN','')
HA_PLANT_ID=int(os.getenv('HA_PLANT_ID','0'))
HA_TIMEOUT=float(os.getenv('HA_TIMEOUT','10'))
HA_GRID_SIGN=int(os.getenv('HA_GRID_SIGN','1'))
HA_BATTERY_SIGN=int(os.getenv('HA_BATTERY_SIGN','1'))
HA_ENTITY_MAPPING=os.getenv('HA_ENTITY_MAPPING','{}')

# Google is the only public account entry point. Django admin retains staff login.
INSTALLED_APPS += ['allauth', 'allauth.account', 'allauth.socialaccount', 'allauth.socialaccount.providers.google']
INSTALLED_APPS[0] = 'dashboard.apps.ANMAAdminConfig'
INSTALLED_APPS[INSTALLED_APPS.index('dashboard')] = 'dashboard.apps.DashboardConfig'
MIDDLEWARE += ['allauth.account.middleware.AccountMiddleware']
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend', 'allauth.account.auth_backends.AuthenticationBackend']
SOCIALACCOUNT_ONLY = False
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_UNIQUE_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_STORE_TOKENS = False
SOCIALACCOUNT_ADAPTER = 'dashboard.auth.GoogleOnlyAdapter'
LOGIN_REDIRECT_URL = 'plants'
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
SOCIALACCOUNT_PROVIDERS = {'google': {'EMAIL_AUTHENTICATION': True, 'SCOPE': ['profile', 'email'], 'OAUTH_PKCE_ENABLED': True,
    'APPS': [{'client_id': GOOGLE_CLIENT_ID, 'secret': GOOGLE_CLIENT_SECRET, 'key': ''}]}}
ANMA_CONNECTION_KEY = os.getenv('ANMA_CONNECTION_KEY', '')
# Exact Tailscale IPv4 addresses, optional narrowing inside 100.64.0.0/10.
ANMA_ALLOWED_TAILSCALE_IPS = [v.strip() for v in os.getenv('ANMA_ALLOWED_TAILSCALE_IPS', '').split(',') if v.strip()]
TEMPLATES[0]['OPTIONS']['context_processors'].append('dashboard.auth.auth_context')

# SMTP delivery for account verification and password recovery.
EMAIL_BACKEND = os.getenv('DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('DJANGO_EMAIL_HOST', os.getenv('EMAIL_HOST', ''))
EMAIL_PORT = int(os.getenv('DJANGO_EMAIL_PORT', os.getenv('EMAIL_PORT', '587')))
EMAIL_HOST_USER = os.getenv('DJANGO_EMAIL_HOST_USER', os.getenv('EMAIL_HOST_USER', ''))
EMAIL_HOST_PASSWORD = os.getenv('DJANGO_EMAIL_HOST_PASSWORD', os.getenv('EMAIL_HOST_PASSWORD', ''))
EMAIL_USE_TLS = os.getenv('DJANGO_EMAIL_USE_TLS', os.getenv('EMAIL_USE_TLS', '1')) == '1'
EMAIL_USE_SSL = os.getenv('DJANGO_EMAIL_USE_SSL', os.getenv('EMAIL_USE_SSL', '0')) == '1'
EMAIL_TIMEOUT = int(os.getenv('DJANGO_EMAIL_TIMEOUT', os.getenv('EMAIL_TIMEOUT', '15')))
DEFAULT_FROM_EMAIL = os.getenv('DJANGO_DEFAULT_FROM_EMAIL', os.getenv('DEFAULT_FROM_EMAIL', 'ANMA Cloud <noreply@anma-electric.com.ua>'))
