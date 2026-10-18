(()=>{'use strict';
const box=document.getElementById('solarHourly'),status=document.getElementById('solarHourlyStatus'),period=document.getElementById('solarPeriod'),date=document.getElementById('solarDay');if(!box)return;
let latest;function render(){if(!latest)return;const data=latest,en=localStorage.getItem('anma_lang')==='en',previous=period.value==='yesterday';
period.options[0].textContent=en?'Today':'Сьогодні';period.options[1].textContent=en?'Yesterday':'Вчора';period.setAttribute('aria-label',en?'Solar history day':'День історії генерації');box.replaceChildren();
if(data.error){status.textContent=en?'Home Assistant history unavailable. Retrying in one minute.':'Історія Home Assistant недоступна. Повторна спроба — за хвилину.';return;}
const rows=(previous?data.solar_yesterday:data.solar_hourly)||[];
if(!rows.length){status.textContent=data.demo?(en?'Hourly history is available in Live mode.':'Погодинна історія доступна в режимі Live.'):(en?'No hourly history from Home Assistant.':'Немає погодинної історії у Home Assistant.');return;}
date.textContent=new Date(rows[0].timestamp).toLocaleDateString(en?'en-GB':'uk-UA',{timeZone:data.solar_timezone||'Europe/Kyiv'});
const known=rows.filter(r=>r.status!=='future'&&r.kwh!==null),missing=rows.some(r=>r.status!=='future'&&r.kwh===null),estimate=known.some(r=>r.method==='power_estimate');
status.textContent=(data.demo?(en?'Demo · ':'Демо · '):'')+(en?'Hourly generation · kWh · Kyiv time':'Погодинна генерація · кВт·год · час Києва')+(previous?(en?' · yesterday (available history)':' · вчора (доступна історія)'):(en?' · current hour is incomplete':' · поточна година неповна'))+(estimate?(en?' · ≈ estimated from power':' · ≈ оцінка за потужністю'):'')+(missing?(en?' · ? = history missing; check Recorder and mapped PV entities':' · ? = немає історії; перевірте Recorder і сутності сонця'):'');
const max=Math.max(.01,...known.map(r=>r.kwh));box.style.gridTemplateColumns=`repeat(${rows.length},minmax(42px,1fr))`;
for(const row of rows){const cell=document.createElement('div');cell.className='solar-hour';const value=document.createElement('span');value.textContent=row.status==='future'?'—':row.kwh===null?'?':(row.method==='power_estimate'?'≈':'')+row.kwh.toFixed(2);const track=document.createElement('div');track.className='solar-hour-track';const bar=document.createElement('i');bar.style.height=(row.kwh>0?Math.max(2,row.kwh/max*100):0)+'%';track.append(bar);const label=document.createElement('small');label.textContent=row.hour;cell.title=row.hour+' · '+(row.status==='future'?(en?'Future hour':'Майбутня година'):row.kwh===null?(en?'No data':'Немає даних'):value.textContent+(en?' kWh':' кВт·год'));cell.append(value,track,label);box.append(cell);}
}
window.addEventListener('anma-history',e=>{latest=e.detail;render();});window.addEventListener('anma-language',render);period.addEventListener('change',render);
})();
