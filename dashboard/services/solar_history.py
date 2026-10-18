"""Hourly energy from HA recorder; no database writes or invented zeroes."""
from datetime import timedelta, timezone as utc_timezone
from django.utils import timezone

def hourly_solar(events, end):
    local = timezone.localtime(end)
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    next_day = midnight + timedelta(days=1)
    start = midnight.astimezone(utc_timezone.utc)
    stop = next_day.astimezone(utc_timezone.utc)
    energy = sorted(events.get('daily_pv', []))
    power = sorted(events.get('pv_power', []))
    def at(points, instant):
        return next((v for t,v in reversed(points) if t<=instant), None)
    rows = []
    while start < stop:
        finish = min(start+timedelta(hours=1), stop)
        until = min(finish, end)
        value = None
        method = 'counter'
        if start < end:
            points = [(start,at(energy,start)), *[(t,v) for t,v in energy if start<t<until], (until,at(energy,until))]
            if energy and all(v is not None for _,v in points):
                # Midnight reset is handled as a counter reset, never as negative energy.
                value = sum(b-a if b>=a else max(0,b) for (_,a),(_,b) in zip(points,points[1:]))
            else:
                method = 'power_estimate'
                points = [(start,at(power,start)), *[(t,v) for t,v in power if start<t<until], (until,at(power,until))]
                if power and all(v is not None for _,v in points):
                    value = sum(max(0,a)*(tb-ta).total_seconds()/3600000 for (ta,a),(tb,_) in zip(points,points[1:]))
        rows.append({'hour':timezone.localtime(start).strftime('%H:%M'), 'timestamp':start.isoformat(),
                     'kwh':round(value,3) if value is not None else None,
                     'status':'future' if start>=end else 'partial' if end<finish else 'complete', 'method':method})
        start=finish
    return rows
