import random,math,datetime
from django.utils import timezone
FIELDS=['pv_power','load_power','battery_soc','battery_power','grid_power','grid_voltage','daily_pv','fault_code']
def snapshot(plant):
 seed=plant.pk*913 if plant.pk else 11
 t=timezone.localtime();h=t.hour+t.minute/60
 pv=round(max(0,5900*math.sin(math.pi*(h-6)/13)) if 6<h<19 else 0)
 load=round(1700+500*math.sin(h/2+seed)+random.Random(seed+t.minute//2).randint(-120,120))
 soc=max(15,min(100,round(64+19*math.sin((h-9)*math.pi/12))))
 bat=round((pv-load)*.47)
 grid=round(load-pv+bat)
 return {'pv_power':pv,'load_power':load,'battery_soc':soc,'battery_power':bat,'grid_power':grid,'grid_voltage':229.3,'daily_pv':round(23.8+seed%5*.7,1),'fault_code':'0','grid_available':True,'inverter_fault':False,'forecast_today':round((23.8+seed%5*.7)*1.06,1),'forecast_tomorrow':round((23.8+seed%5*.7)*.86,1),'online':True,'updated_at':t.isoformat(),'demo':True}
def history(plant):
 seed=plant.pk or 1
 result=[]
 end=timezone.now()
 for i in range(97):
  stamp=end-datetime.timedelta(minutes=15*(96-i))
  local=timezone.localtime(stamp)
  h=local.hour+local.minute/60
  pv=round(max(0,5800*math.sin(math.pi*(h-6)/13)) if 6<h<19 else 0)
  load=round(1600+420*math.sin(i/9+seed)+110*math.sin(i/3))
  bat=round((pv-load)*.45)
  result.append({'timestamp':stamp.isoformat(),'time':f'{int(h):02d}:{int(h%1*60):02d}','pv':pv,'load':load,'battery':bat,'grid':load-pv+bat,'soc':max(17,min(100,round(65+18*math.sin(i/20))))})
 return result


def history_payload(plant):
 from .services.solar_history import hourly_solar
 series=history(plant)
 end=datetime.datetime.fromisoformat(series[-1]['timestamp'])
 events={'pv_power':[(datetime.datetime.fromisoformat(row['timestamp']),row['pv']) for row in series]}
 return {'series':series,'demo':True,'available':True,
         'solar_hourly':hourly_solar(events,end),
         'solar_yesterday':hourly_solar(events,end,timezone.localdate(end)-datetime.timedelta(days=1)),
         'solar_date':timezone.localdate(end).isoformat(),'solar_timezone':str(timezone.get_current_timezone())}
