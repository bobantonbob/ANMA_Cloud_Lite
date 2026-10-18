from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from django.test import SimpleTestCase, override_settings
from .services.solar_history import hourly_solar

@override_settings(TIME_ZONE='Europe/Kyiv')
class SolarHistoryTests(SimpleTestCase):
    def setUp(self):
        self.start=datetime(2026,10,18,tzinfo=ZoneInfo('Europe/Kyiv'))

    def test_counter_partial_and_future(self):
        events={'daily_pv':[(self.start,0),(self.start+timedelta(hours=1),2),(self.start+timedelta(hours=1,minutes=20),3)]}
        rows=hourly_solar(events,self.start+timedelta(hours=1,minutes=30))
        self.assertEqual(len(rows),24)
        self.assertEqual([r['kwh'] for r in rows[:3]],[2,1,None])
        self.assertEqual(rows[1]['status'],'partial')
        self.assertEqual(rows[2]['status'],'future')

    def test_power_estimate_and_unavailable(self):
        events={'pv_power':[(self.start,1000),(self.start+timedelta(hours=1),None)]}
        rows=hourly_solar(events,self.start+timedelta(hours=2))
        self.assertIsNone(rows[1]['kwh'])
        self.assertEqual(rows[0]['method'],'power_estimate')

    def test_constant_zero_is_not_missing(self):
        rows=hourly_solar({'pv_power':[(self.start,0)]},self.start+timedelta(hours=1))
        self.assertEqual(rows[0]['kwh'],0)
        self.assertIsNone(hourly_solar({},self.start+timedelta(hours=1))[0]['kwh'])

    def test_midnight_reset(self):
        rows=hourly_solar({'daily_pv':[(self.start-timedelta(seconds=1),20),(self.start+timedelta(seconds=1),0),(self.start+timedelta(minutes=30),.5)]}, self.start+timedelta(hours=1))
        self.assertEqual(rows[0]['kwh'],.5)

    def test_dst_day_has_actual_hours(self):
        end=datetime(2026,10,25,23,tzinfo=ZoneInfo('Europe/Kyiv'))
        rows=hourly_solar({},end)
        self.assertEqual(len(rows),25)
        self.assertEqual(len(set(r['timestamp'] for r in rows)),25)

    def test_yesterday_remains_available_after_midnight(self):
        end=self.start+timedelta(days=1,minutes=18)
        events={'daily_pv':[(self.start,0),(self.start+timedelta(hours=12),3),
                            (self.start+timedelta(hours=13),5),(self.start+timedelta(days=1),0)]}
        today=hourly_solar(events,end)
        yesterday=hourly_solar(events,end,self.start.date())
        self.assertEqual(today[0]['kwh'],0)
        self.assertEqual(yesterday[12]['kwh'],2)
        self.assertEqual(len(yesterday),24)
        self.assertTrue(all(row['status']=='complete' for row in yesterday))

    def test_missing_counter_falls_back_to_hourly_power(self):
        events={'pv_power':[(self.start,0),(self.start+timedelta(hours=8),2000),
                           (self.start+timedelta(hours=9),0)]}
        rows=hourly_solar(events,self.start+timedelta(hours=10))
        self.assertEqual(rows[8]['kwh'],2)
        self.assertEqual(rows[8]['method'],'power_estimate')
