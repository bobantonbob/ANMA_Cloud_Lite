from django.test import SimpleTestCase
from .services.home_assistant import battery_direction, normalize

class BatteryDirectionTests(SimpleTestCase):
    def test_state_overrides_sign(self):
        self.assertEqual(battery_direction(400,'discharge',True),-400)
        self.assertEqual(battery_direction(-400,'charge',True),400)
    def test_idle_unknown_and_legacy(self):
        self.assertEqual(battery_direction(400,'idle',True),0)
        self.assertIsNone(battery_direction(400,None,True))
        self.assertIsNone(battery_direction(None,'charge',True))
        self.assertEqual(battery_direction(-400,None,False),-400)
    def test_state_normalization(self):
        for raw,expected in [('Charging','charge'),('discharge','discharge'),('standby','idle'),('unexpected',None)]:
            self.assertEqual(normalize({'state':raw},'battery_state'),expected)
