"""Private Tailscale-only connector; no general-purpose HTTP proxy."""
import hashlib
import hmac
import ipaddress
import json
import re
import secrets
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler
from datetime import timedelta
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import transaction, IntegrityError
from django.utils import timezone
from .home_assistant import HAError, NoRedirect, HomeAssistant, FIELDS, HISTORY_FIELDS
from ..models import Plant, HAConnection, PairingAttempt, TelemetrySample


def validate_address(address):
    try:
        ip = ipaddress.IPv4Address(address)
    except ipaddress.AddressValueError:
        raise HAError('invalid_address') from None
    if ip not in ipaddress.ip_network('100.64.0.0/10'):
        raise HAError('invalid_address')
    if settings.ANMA_ALLOWED_TAILSCALE_IPS and str(ip) not in settings.ANMA_ALLOWED_TAILSCALE_IPS:
        raise HAError('address_not_allowed')
    return str(ip)


def cipher():
    try:
        return Fernet(settings.ANMA_CONNECTION_KEY.encode())
    except (ValueError, TypeError):
        raise HAError('encryption_not_configured') from None


def connector_request(ip, path, body=None, token=None):
    address = validate_address(ip)
    if path not in ('verify', 'pair', 'states', 'history'):
        raise HAError('invalid_request')
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = Request(f'http://{address}:8123/api/anma_cloud/{path}',
                  data=json.dumps(body).encode() if body is not None else None, headers=headers)
    try:
        # Ignore system proxy settings and disallow redirects, including same-host redirects.
        with build_opener(ProxyHandler({}), NoRedirect).open(req, timeout=min(settings.HA_TIMEOUT, 15)) as response:
            limit = 24_000_000 if path == 'history' else 200_000
            raw = response.read(limit+1)
            if len(raw) > limit:
                raise HAError('invalid_response')
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise HAError('invalid_response')
            return result
    except HTTPError as exc:
        code = 'invalid_or_expired_code' if exc.code in (401, 403) else 'integration_missing' if exc.code == 404 else 'connector_error'
        raise HAError(code) from None
    except (URLError, TimeoutError, OSError):
        raise HAError('connection_failed') from None
    except (ValueError, UnicodeError):
        raise HAError('invalid_response') from None


def pair_plant(user, name, address, code):
    encryption = cipher()
    address = validate_address(address)
    code = code.replace('-', '').replace(' ', '').upper()
    if not re.fullmatch(r'[A-F0-9]{32}', code):
        raise HAError('invalid_or_expired_code')
    if PairingAttempt.objects.filter(user=user, created_at__gte=timezone.now()-timedelta(minutes=10)).count() >= 10:
        raise HAError('too_many_attempts')
    attempt = PairingAttempt.objects.create(user=user)
    try:
        token = secrets.token_urlsafe(32)
        payload = {'nonce': secrets.token_hex(16), 'timestamp': int(time.time()),
                   'credential_hash': hashlib.sha256(token.encode()).hexdigest()}
        material = f"{payload['nonce']}\n{payload['timestamp']}\n{payload['credential_hash']}"
        payload['proof'] = hmac.new(code.encode(), material.encode(), hashlib.sha256).hexdigest()
        remote = connector_request(address, 'verify', payload)
        installation = remote.get('installation_id', '')
        if not re.fullmatch(r'[a-f0-9]{32}', installation) or remote.get('protocol') != 1:
            raise HAError('invalid_response')
        with transaction.atomic():
            existing = HAConnection.objects.select_for_update().select_related('plant').filter(installation_id=installation).first()
            if existing and existing.plant.owner_id != user.pk:
                raise HAError('already_bound')
            if existing and not existing.enabled:
                raise HAError('connection_disabled')
            encrypted = encryption.encrypt(token.encode()).decode()
            if existing:
                plant = existing.plant
                plant.name, plant.tailscale_ip = name, address
                plant.save(update_fields=['name','tailscale_ip'])
                existing.credential, existing.tailscale_ip, existing.last_error = encrypted, address, ''
                existing.save(update_fields=['credential','tailscale_ip','last_error'])
            else:
                plant = Plant.objects.create(owner=user, name=name, model='Home Assistant · ANMA', demo=False, tailscale_ip=address)
                HAConnection.objects.create(plant=plant, installation_id=installation, tailscale_ip=address, credential=encrypted)
            confirmed = connector_request(address, 'pair', payload)
            if confirmed.get('installation_id') != installation or confirmed.get('paired') is not True:
                raise HAError('invalid_response')
        attempt.result = 'paired'
        return plant
    except IntegrityError:
        attempt.result = 'already_bound'
        raise HAError('already_bound') from None
    except HAError as exc:
        attempt.result = exc.code
        raise
    finally:
        attempt.save(update_fields=['result'])


class PairedHomeAssistant(HomeAssistant):
    def __init__(self, connection):
        self.connection = connection
        if not connection.enabled:
            raise HAError('connection_disabled')
        try:
            self.token = cipher().decrypt(connection.credential.encode()).decode()
        except InvalidToken:
            raise HAError('credential_unreadable') from None
        self.overrides = {}
        self.key = 'paired:' + hashlib.sha256((connection.installation_id+self.token).encode()).hexdigest()

    def sign(self, field):
        return 1  # Integration already normalizes directions.

    def states(self):
        try:
            result = connector_request(self.connection.tailscale_ip, 'states', token=self.token)
            if result.get('installation_id') != self.connection.installation_id or not isinstance(result.get('states'), list):
                raise HAError('invalid_response')
            states = result['states']
            if any(not isinstance(s, dict) or not isinstance(s.get('entity_id'), str) or not isinstance(s.get('attributes'), dict) for s in states):
                raise HAError('invalid_response')
            HAConnection.objects.filter(pk=self.connection.pk).update(last_seen=timezone.now(), last_error='')
            return {s['entity_id']:s for s in states}
        except HAError as exc:
            HAConnection.objects.filter(pk=self.connection.pk).update(last_error=exc.code)
            raise

    def history_raw(self, ids, start, end):
        try:
            result = connector_request(self.connection.tailscale_ip, 'history', token=self.token)
        except HAError as exc:
            if exc.code == 'integration_missing':
                raise HAError('history_upgrade_required') from None
            raise
        if result.get('installation_id') != self.connection.installation_id or not isinstance(result.get('history'),list):
            raise HAError('invalid_history')
        return result['history']


def service_for(plant):
    if hasattr(plant, 'connection'):
        return PairedHomeAssistant(plant.connection)
    if plant.pk == settings.HA_PLANT_ID:
        return HomeAssistant()
    raise HAError('live_not_bound')
