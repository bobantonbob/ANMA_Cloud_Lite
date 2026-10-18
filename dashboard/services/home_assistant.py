"""Read-only HA REST adapter. No credentials or raw HA errors reach the browser."""
import hashlib
import json
import math
import time
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime

# field: (entity suffix, canonical unit, entity domain)
FIELDS = {
    'pv_power': ('pv_power', 'W', 'sensor'),
    'load_power': ('load_power', 'W', 'sensor'),
    'battery_soc': ('battery_soc', '%', 'sensor'),
    'battery_power': ('battery_power', 'W', 'sensor'),
    'battery_state': ('battery_state', None, 'sensor'),
    'grid_power': ('grid_power', 'W', 'sensor'),
    'grid_voltage': ('grid_voltage', 'V', 'sensor'),
    'daily_pv': ('pv_energy_today', 'kWh', 'sensor'),
    'daily_load': ('load_energy_today', 'kWh', 'sensor'),
    'grid_import_today': ('grid_import_today', 'kWh', 'sensor'),
    'grid_export_today': ('grid_export_today', 'kWh', 'sensor'),
    'battery_charge_today': ('battery_charge_today', 'kWh', 'sensor'),
    'battery_discharge_today': ('battery_discharge_today', 'kWh', 'sensor'),
    'forecast_today': ('pv_forecast_today', 'kWh', 'sensor'),
    'forecast_tomorrow': ('pv_forecast_tomorrow', 'kWh', 'sensor'),
    'grid_available': ('grid_available', None, 'binary_sensor'),
    'inverter_fault': ('inverter_fault', None, 'binary_sensor'),
    'inverter_status': ('inverter_status', None, 'sensor'),
    'fault_code': ('inverter_fault_code', None, 'sensor'),
}
HISTORY_FIELDS = {'pv_power':'pv', 'load_power':'load', 'grid_power':'grid', 'battery_soc':'soc', 'battery_power':'battery'}


class HAError(Exception):
    """Only fixed, non-sensitive codes are safe to return or log."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class NoRedirect(HTTPRedirectHandler):
    # Never forward Authorization to a redirected host.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def normalize(state, field, sign=1):
    if not state or state.get('state') in (None, '', 'unknown', 'unavailable'):
        return None
    value = state['state']
    if field in ('grid_available', 'inverter_fault'):
        return {'on': True, 'off': False}.get(value)
    if field == 'battery_state':
        return {'charge':'charge','charging':'charge','discharge':'discharge','discharging':'discharge','idle':'idle','standby':'idle','not charging':'idle'}.get(str(value).strip().lower())
    if field in ('fault_code', 'inverter_status'):
        return str(value)[:100]
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    unit = state.get('attributes', {}).get('unit_of_measurement')
    target = FIELDS[field][1]
    factors = {'W': {'W':1, 'kW':1000, 'MW':1000000}, 'kWh': {'Wh':.001, 'kWh':1, 'MWh':1000}, 'V': {'V':1, 'mV':.001, 'kV':1000}, '%': {'%':1}}
    if unit not in factors[target]:
        return None  # Do not guess the unit of an unmapped/misconfigured sensor.
    value *= factors[target][unit]
    if field == 'battery_soc' and not 0 <= value <= 100:
        return None
    return value * sign


def state_time(state):
    value = state.get('last_updated') or state.get('last_changed')
    try:
        stamp = parse_datetime(value) if value else None
    except (ValueError, TypeError):
        return None
    return stamp if stamp and timezone.is_aware(stamp) else None


def battery_direction(power, state, configured):
    if not configured:
        return power
    if state == 'idle':
        return 0
    if power is not None and state in ('charge','discharge'):
        return abs(power) * (1 if state == 'charge' else -1)
    return None


class HomeAssistant:
    def __init__(self):
        self.url = settings.HA_URL
        self.token = settings.HA_TOKEN
        parsed = urlsplit(self.url)
        if not self.token or not self.url:
            raise HAError('not_configured')
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise HAError('invalid_configuration')
        if settings.HA_GRID_SIGN not in (-1, 1) or settings.HA_BATTERY_SIGN not in (-1, 1):
            raise HAError('invalid_sign_configuration')
        try:
            self.overrides = json.loads(settings.HA_ENTITY_MAPPING)
            if not isinstance(self.overrides, dict) or any(k not in FIELDS or not isinstance(v,str) or not v.startswith(FIELDS[k][2]+'.') or any(c in v for c in '/?&#') for k,v in self.overrides.items()):
                raise ValueError
        except (TypeError, ValueError):
            raise HAError('invalid_mapping') from None
        # Cache partition includes config and credential fingerprint, never a raw token.
        material = json.dumps([self.url,self.token,self.overrides,settings.HA_GRID_SIGN,settings.HA_BATTERY_SIGN])
        self.key = 'ha:' + hashlib.sha256(material.encode()).hexdigest()
        self.timeout = max(1,min(settings.HA_TIMEOUT,30))

    def request(self, path, params=None):
        url = self.url + path + ('?' + urlencode(params) if params else '')
        req = Request(url, headers={'Authorization': 'Bearer '+self.token, 'Accept':'application/json'})
        for attempt in range(2):
            try:
                with build_opener(NoRedirect).open(req, timeout=self.timeout) as response:
                    raw = response.read(24_000_001)
                    if len(raw) > 24_000_000:
                        raise HAError('response_too_large')
                    return json.loads(raw)
            except HTTPError as exc:
                if exc.code in (401,403):
                    raise HAError('authentication_failed') from None
                if attempt == 0 and exc.code in (502,503,504):
                    time.sleep(.2)
                    continue
                raise HAError('http_'+str(exc.code)) from None
            except (URLError, TimeoutError, OSError):
                if attempt == 0:
                    time.sleep(.2)
                    continue
                raise HAError('connection_failed') from None
            except (ValueError, UnicodeError):
                raise HAError('invalid_response') from None

    def authenticate(self):
        return self.request('/api/').get('message') == 'API running.'

    def states(self):
        states = self.request('/api/states')
        if not isinstance(states,list) or any(not isinstance(s,dict) or 'entity_id' not in s for s in states):
            raise HAError('invalid_response')
        return {s['entity_id']:s for s in states}

    def mapping(self, states):
        mapping = {}
        for field,(suffix,unit,domain) in FIELDS.items():
            candidates = [f'{domain}.anma_{suffix}', f'{domain}.anma_cloud_{suffix}']
            mapping[field] = self.overrides.get(field) or next((x for x in candidates if x in states),candidates[0])
        return mapping

    def sign(self, field):
        return settings.HA_GRID_SIGN if field=='grid_power' else settings.HA_BATTERY_SIGN if field=='battery_power' else 1

    def discover(self, states=None):
        states = self.states() if states is None else states
        return [{'entity_id':eid,'friendly_name':s.get('attributes',{}).get('friendly_name'),
                 'state':s.get('state'),'unit':s.get('attributes',{}).get('unit_of_measurement'),
                 'available':s.get('state') not in (None,'unknown','unavailable'),
                 'device_class':s.get('attributes',{}).get('device_class')}
                for eid,s in states.items() if eid.startswith(('sensor.anma_','binary_sensor.anma_'))
                and not any(word in eid for word in ('token','secret','pairing','key'))]

    def snapshot(self):
        cached = cache.get(self.key+':snapshot')
        if cached is not None:
            return cached
        states = self.states()
        mapping = self.mapping(states)
        payload = {field:normalize(states.get(eid),field,self.sign(field)) for field,eid in mapping.items()}
        payload['battery_power_magnitude'] = abs(payload['battery_power']) if payload['battery_power'] is not None else None
        payload['battery_power'] = battery_direction(payload['battery_power'], payload['battery_state'], mapping['battery_state'] in states)
        stamp = timezone.now().isoformat()
        payload.update(online=True,demo=False,updated_at=stamp,
                       source_updated_at={field:(states.get(eid) or {}).get('last_updated') for field,eid in mapping.items()},
                       missing=[field for field,eid in mapping.items() if eid not in states],
                       unavailable=[field for field,eid in mapping.items() if eid in states and payload[field] is None])
        cache.set(self.key+':last_success',stamp,86400)
        cache.set(self.key+':snapshot',payload,5)
        return payload

    def offline(self, code):
        return {**{field:None for field in FIELDS},'online':False,'demo':False,'updated_at':cache.get(self.key+':last_success'),'error':code}

    def history_raw(self, ids, start, end):
        return self.request('/api/history/period/'+quote(start.isoformat(),safe=''),
                           {'end_time':end.isoformat(),'filter_entity_id':','.join(ids),'minimal_response':'1'}) if ids else []

    def history(self):
        cached = cache.get(self.key+':history')
        if cached is not None:
            return cached
        states = self.states()
        mapping = self.mapping(states)
        fields = {**HISTORY_FIELDS, 'daily_pv':'energy', 'battery_state':'battery_state'}
        ids = list(dict.fromkeys(mapping[f] for f in fields if mapping[f] in states))
        end = timezone.now(); start = end-timedelta(hours=24)
        raw = self.history_raw(ids, end-timedelta(hours=26), end)
        if not isinstance(raw,list):
            raise HAError('invalid_history')
        events = {f:[] for f in fields}
        for group in raw:
            if not isinstance(group,list) or not group:
                continue
            eid = group[0].get('entity_id')
            matched = [f for f in fields if mapping[f]==eid]
            attributes = {}
            for state in group:
                attributes = state.get('attributes',attributes)
                stamp = state_time(state)
                if not stamp or stamp>end:
                    continue
                for field in matched:
                    events[field].append((stamp,normalize({**state,'attributes':attributes},field,self.sign(field))))
        timeline = {start,end}
        changes = {}
        for field,items in events.items():
            if field == 'daily_pv':
                continue
            for stamp,value in items:
                stamp = max(start, stamp)
                timeline.add(stamp)
                changes.setdefault(stamp,{})[fields[field]]=value
        current = {key:None for key in HISTORY_FIELDS.values()}
        series = []
        for stamp in sorted(timeline):
            current.update(changes.get(stamp,{}))
            row = dict(current)
            row['battery'] = battery_direction(row['battery'], row.get('battery_state'), mapping['battery_state'] in states)
            series.append({'timestamp':stamp.isoformat(),'time':timezone.localtime(stamp).strftime('%H:%M'),**row})
        result = {'series':series,'demo':False,'start':start.isoformat(),'end':end.isoformat(),
                  'missing':[HISTORY_FIELDS[f] for f in HISTORY_FIELDS if not events[f]],
                  'available':any(items for items in events.values()),'updated_at':end.isoformat()}
        from .solar_history import hourly_solar
        result['solar_hourly'] = hourly_solar(events, end)
        result['source'] = 'home_assistant'
        cache.set(self.key+':history',result,60)
        return result
