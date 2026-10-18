(()=>{'use strict';
const app=window.ANMA;if(!app)return;
const el=id=>document.getElementById(id);
let history=app.history||[],latest=null,lastUpdated=null;
// Missing telemetry must never be displayed as a measured zero.
const reading=v=>v===null||v===undefined||typeof v==='boolean'||String(v).trim()===''?null:Number.isFinite(Number(v))?Number(v):null;
const kw=v=>reading(v)===null?'—':(Number(v)/1000).toFixed(2);
const magnitude=v=>v===null?null:Math.abs(v);
const lang=()=>localStorage.getItem('anma_lang')==='en'?'en':'uk';
const labels={uk:{import:'→ ІМПОРТ',export:'← ЕКСПОРТ',idle:'БЕЗ ПЕРЕТОКУ',charge:'↓ ЗАРЯД',discharge:'↑ РОЗРЯД',offline:'НЕМАЄ ЗВʼЯЗКУ',battery:'АКУМУЛЯТОР',time:'Час',power:'Потужність',unknown:'НЕМАЄ ДАНИХ',noSolar:'БЕЗ ГЕНЕРАЦІЇ',generating:'ГЕНЕРАЦІЯ',noGrid:'МЕРЕЖА ВІДСУТНЯ',gridOn:'Мережа доступна',online:'ДЕМО · ОНЛАЙН',inverter:'Інвертор онлайн',connected:'Зʼєднання активне',normal:'Норма',fault:'Помилка інвертора',noFault:'Помилок не виявлено',last:'Останні дані',unit:'кВт'},en:{import:'→ IMPORT',export:'← EXPORT',idle:'IDLE',charge:'↓ CHARGING',discharge:'↑ DISCHARGING',offline:'OFFLINE',battery:'BATTERY',time:'Time',power:'Power',unknown:'NO DATA',noSolar:'NO GENERATION',generating:'GENERATING',noGrid:'GRID UNAVAILABLE',gridOn:'Grid available',online:'DEMO · ONLINE',inverter:'Inverter online',connected:'Connection active',normal:'Normal',fault:'Inverter fault',noFault:'No faults detected',last:'Last data',unit:'kW'}};
Object.assign(labels.uk,{liveOnline:'LIVE · ОНЛАЙН',historyLoading:'Завантаження історії…',historyEmpty:'Історія за останні 24 години відсутня.',historyFailed:'Історію не вдалося завантажити. Повторна спроба — за хвилину.',historyPartial:'Часткова історія · порожні ділянки означають відсутність даних',historyLive:'Історія Home Assistant · останні 24 години',historyDemo:'Демонстраційна історія · останні 24 години',connectionError:'Немає зв’язку з Home Assistant. Показники недоступні.',authenticationError:'Home Assistant відхилив доступ. Перевірте серверну конфігурацію.',notBound:'Цей об’єкт не прив’язаний до локального Home Assistant.'});
Object.assign(labels.en,{liveOnline:'LIVE · ONLINE',historyLoading:'Loading history…',historyEmpty:'No history for the last 24 hours.',historyFailed:'History could not be loaded. Retrying in one minute.',historyPartial:'Partial history · gaps indicate missing data',historyLive:'Home Assistant history · last 24 hours',historyDemo:'Demo history · last 24 hours',connectionError:'Home Assistant is unreachable. Readings are unavailable.',authenticationError:'Home Assistant denied access. Check the server configuration.',notBound:'This site is not bound to the local Home Assistant.'});
const tr=k=>labels[lang()][k]||k;
function set(id,value){if(el(id))el(id).textContent=value}
function updateMotion(id,path,active){
 const particle=document.querySelector('.'+id+'-particle');if(!particle)return;
 particle.classList.toggle('paused',!active);
 const motion=particle.querySelector('animateMotion');
 if(motion&&motion.getAttribute('path')!==path)motion.setAttribute('path',path);
}
function flowState(name,state,wire){
 const node=document.querySelector('.flow-'+name);if(node)node.dataset.state=state;
 if(el(wire))el(wire).classList.toggle('wire-inactive',state!=='active');
}
function available(value){if(value===true||value==='on')return true;if(value===false||value==='off')return false;return null;}
function render(d){
 latest=d;
 const online=d.online===true;
 const isDemo=d.demo===true;
 const notice=el('telemetryError');if(notice){notice.hidden=online;notice.textContent=online?'':tr(d.error==='authentication_failed'?'authenticationError':d.error==='live_not_bound'?'notBound':'connectionError');}
 const read=key=>online?reading(d[key]):null;
 const pv=read('pv_power'),load=read('load_power'),battery=read('battery_power'),grid=read('grid_power');
 const rawSoc=read('battery_soc'),soc=rawSoc!==null&&rawSoc>=0&&rawSoc<=100?rawSoc:null;
 const voltage=read('grid_voltage');
 // Explicit availability wins. Voltage is a fallback for older demo responses.
 const gridAvailable=!online?null:('grid_available' in d?available(d.grid_available):voltage===null?null:voltage>0);
 const gridActive=gridAvailable===true&&grid!==null&&grid!==0;
 const gridLabel=gridAvailable===false?tr('noGrid'):gridAvailable===null||grid===null?tr('unknown'):grid>0?tr('import'):grid<0?tr('export'):tr('idle');
 const batteryLabel=battery===null?tr('unknown'):battery>0?tr('charge'):battery<0?tr('discharge'):tr('idle');
 set('pv',kw(pv));set('flowPv',kw(pv));set('load',kw(load));set('flowLoad',kw(load));
 set('soc',soc??'—');set('flowSoc',soc??'—');if(el('socBar'))el('socBar').style.width=(soc??0)+'%';
 const gridDisplay=gridAvailable===null?null:magnitude(grid);
 set('grid',kw(gridDisplay));set('flowGrid',kw(gridDisplay));
 set('gridStatus',gridLabel);set('flowGridStatusText',gridLabel);
 set('batteryStatus',batteryLabel);set('flowBatteryStatus',batteryLabel);
 set('batteryDirectionMark',battery===null?'?':battery>0?'↓':battery<0?'↑':'—');
 const batteryMagnitude=read('battery_power_magnitude')??magnitude(battery);
 set('flowBatteryPower',kw(batteryMagnitude)+' '+tr('unit'));
 set('batteryPower',kw(batteryMagnitude)+' '+tr('unit'));
 set('flowSolarStatus',pv===null?tr('unknown'):pv>0?tr('generating'):tr('noSolar'));
 flowState('solar',pv===null?'unknown':pv>0?'active':'idle','wirePv');
 flowState('grid',gridAvailable===false?'unavailable':gridAvailable===null||grid===null?'unknown':gridActive?'active':'idle','wireGrid');
 flowState('battery',battery===null?'unknown':battery!==0?'active':'idle','wireBattery');
 flowState('load',load===null?'unknown':load>0?'active':'idle','wireLoad');
 updateMotion('solar','M300 78 V185',pv!==null&&pv>0);
 updateMotion('grid',grid>=0?'M107 205 H260':'M260 205 H107',gridActive);
 updateMotion('load','M340 205 H493',load!==null&&load>0);
 updateMotion('battery',battery>=0?'M300 230 V313':'M300 313 V230',battery!==null&&battery!==0);
 const stamp=d.updated_at?new Date(d.updated_at):null;
 if(stamp&&!Number.isNaN(stamp.getTime()))lastUpdated=stamp;
 const when=lastUpdated?lastUpdated.toLocaleString(lang()==='uk'?'uk-UA':'en-GB'):'—';
 ['updated','updatedMobile','flowUpdated'].forEach(id=>set(id,online?when:tr('offline')+' · '+tr('last')+': '+when));
 document.querySelectorAll('[data-connection-label]').forEach(node=>node.textContent=online?tr(isDemo?'online':'liveOnline'):tr('offline'));
 document.body.classList.toggle('telemetry-offline',!online);
 set('flowConnection',online?(isDemo?'DEMO':'LIVE'):tr('offline'));
 set('inverterStatus',online?tr('inverter'):tr('offline'));set('connectionStatus',online?tr('connected'):tr('last')+': '+when);
 set('gridHealth',gridAvailable===null?tr('unknown'):gridAvailable?tr('gridOn'):tr('noGrid'));
 set('voltage',voltage===null?'—':voltage+' V');
 const binaryFault=available(d.inverter_fault);
 const codeKnown=d.fault_code!=null&&!['unknown','unavailable',''].includes(String(d.fault_code));
 const fault=online&&(binaryFault===true||(codeKnown&&!['0','none','ok'].includes(String(d.fault_code).toLowerCase())));
 const faultKnown=online&&(binaryFault!==null||codeKnown);
 set('faultStatus',!faultKnown?tr('unknown'):fault?tr('fault')+(codeKnown?': '+d.fault_code:''):tr('noFault'));
 if(online && d.inverter_status != null)set('faultStatus', String(d.inverter_status));
 const inverterState=online?String(d.inverter_status??'').trim().toLowerCase():'';
 const inverterOn=['on','online','connected','running','ok','normal'].includes(inverterState);
 const inverterOff=['off','offline','disconnected'].includes(inverterState);
 document.querySelectorAll('.health-row').forEach(row=>{
  const icon=row.querySelector('.health-ico');if(!icon)return;
  const isInverter=!!row.querySelector('#faultStatus');
  const good=online&&(row.querySelector('#gridHealth')?gridAvailable===true:isInverter?(inverterState?inverterOn&&!fault:faultKnown&&!fault):true);
  icon.textContent=good?'✓':isInverter&&inverterOff?'⏻':isInverter&&fault?'!':'—';
  icon.classList.toggle('health-muted',!good);
 });
 const base=read('daily_pv');set('daily',base??'—');
 const today=read('forecast_today'),tomorrow=read('forecast_tomorrow');
 set('forecastToday',today===null?'—':today.toFixed(1));set('forecastTomorrow',tomorrow===null?'—':tomorrow.toFixed(1));

}
const definitions={powerChart:[{key:'pv',label:'PV',color:'--orange',scale:1000},{key:'load',label:'LOAD',color:'--blue',scale:1000},{key:'grid',label:'GRID',color:'--purple',scale:1000}],batteryChart:[{key:'soc',label:'SOC',color:'--green',scale:1},{key:'battery',label:'BATTERY',color:'--orange',scale:1000}]};
let layout={},historyState=history.length?'historyDemo':'historyLoading';
const timestamp=(item,i)=>Number.isFinite(Date.parse(item.timestamp))?Date.parse(item.timestamp):i;
const localTime=(stamp,full=false)=>new Date(stamp).toLocaleString(lang()==='uk'?'uk-UA':'en-GB',full?{timeZone:app.timeZone||'Europe/Kyiv'}:{timeZone:app.timeZone||'Europe/Kyiv',hour:'2-digit',minute:'2-digit'});
function draw(id){
 const canvas=el(id);if(!canvas)return;
 const lines=definitions[id],width=Math.max(180,canvas.getBoundingClientRect().width),height=220,dpr=Math.min(window.devicePixelRatio||1,2);
 canvas.width=width*dpr;canvas.height=height*dpr;
 const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);
 const batteryChart=id==='batteryChart',pad={l:40,r:batteryChart?43:12,t:22,b:27},w=width-pad.l-pad.r,h=height-pad.t-pad.b;
 const value=(item,line)=>reading(item[line.key])===null?null:Number(item[line.key])/line.scale;
 let min=0,max=.1;
 for(const item of history)for(const line of lines){if(line.key==='soc')continue;const v=value(item,line);if(v!==null){min=Math.min(min,v);max=Math.max(max,v);}}
 min=min<0?min*1.1:0;max*=1.1;
 const yCoord=(v,line)=>pad.t+h*(1-(line.key==='soc'?v/100:(v-min)/(max-min)));
 const times=history.map(timestamp),first=times[0]??0,last=times[times.length-1]??1;
 const xCoord=i=>pad.l+w*(times[i]-first)/(last-first||1);
 const color=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
 ctx.clearRect(0,0,width,height);ctx.font='10px sans-serif';ctx.fillStyle=color('--muted');
 ctx.textAlign='left';ctx.fillText(batteryChart?'SOC %':tr('unit'),pad.l,11);
 if(batteryChart){ctx.textAlign='right';ctx.fillText(tr('unit'),width-pad.r,11);}
 for(let j=0;j<=4;j++){
  const y=pad.t+j*h/4;ctx.strokeStyle='rgba(130,140,160,.18)';ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(width-pad.r,y);ctx.stroke();
  ctx.textAlign='right';ctx.fillText(batteryChart?String(100-j*25):(max-(max-min)*j/4).toFixed(1),pad.l-6,y+3);
  if(batteryChart){ctx.textAlign='left';ctx.fillText((max-(max-min)*j/4).toFixed(1),width-pad.r+6,y+3);}
 }
 if(history.length){
  if(min<0){ctx.strokeStyle=color('--muted');ctx.setLineDash([3,4]);ctx.beginPath();ctx.moveTo(pad.l,yCoord(0,{key:'power'}));ctx.lineTo(width-pad.r,yCoord(0,{key:'power'}));ctx.stroke();ctx.setLineDash([]);}
  [0,.25,.5,.75,1].forEach(fr=>{ctx.textAlign='center';const ix=Math.round(fr*(history.length-1));const text=history[0].timestamp?localTime(first+(last-first)*fr):(history[ix].time||'');ctx.fillText(text,pad.l+w*fr,height-5);});
  for(const line of lines){
   ctx.strokeStyle=color(line.color);ctx.lineWidth=2;ctx.beginPath();let previous=null;
   history.forEach((item,i)=>{const v=value(item,line),x=xCoord(i);if(v===null){previous=null;return;}const y=yCoord(v,line);if(previous!==null){ctx.lineTo(x,previous);ctx.lineTo(x,y);}else ctx.moveTo(x,y);previous=y;});ctx.stroke();
  }
 }
 layout[id]={width,pad,w,lines,value,times,xCoord,first,last};
}
function hideTip(id){const battery=id==='batteryChart';const t=el(battery?'batteryTooltip':'powerTooltip'),r=el(battery?'batteryReticle':'powerReticle');if(t)t.hidden=true;if(r)r.hidden=true;}
function move(id,event){
 const canvas=el(id),tip=el(id==='powerChart'?'powerTooltip':'batteryTooltip'),cfg=layout[id];if(!canvas||!tip||!cfg||!history.length)return;
 const x=event.clientX-canvas.getBoundingClientRect().left;
 const target=cfg.first+Math.max(0,Math.min(1,(x-cfg.pad.l)/cfg.w))*(cfg.last-cfg.first);
 let ix=0;for(let i=1;i<cfg.times.length;i++){if(Math.abs(cfg.times[i]-target)<Math.abs(cfg.times[ix]-target))ix=i;}
 const item=history[ix],reticle=el(id==='powerChart'?'powerReticle':'batteryReticle');
 if(reticle){reticle.hidden=false;reticle.style.left=cfg.xCoord(ix)+'px';}
 tip.replaceChildren();const title=document.createElement('b');title.textContent=tr('time')+': '+(item.timestamp?localTime(cfg.times[ix],true):String(item.time||''));tip.append(title);
 for(const line of cfg.lines){const row=document.createElement('div'),dot=document.createElement('span');dot.className='dot-mark';dot.style.background=getComputedStyle(document.documentElement).getPropertyValue(line.color).trim();const v=cfg.value(item,line);row.append(dot,document.createTextNode(line.label+': '+(v===null?'—':((['grid','battery'].includes(line.key)&&v>0?'+':'')+v.toFixed(line.key==='soc'?0:2)))+' '+(line.key==='soc'?'%':tr('unit'))));tip.append(row);}
 tip.hidden=false;tip.style.left=Math.max(2,Math.min(cfg.width-tip.offsetWidth-2,x+12))+'px';tip.style.top='18px';
}
Object.keys(definitions).forEach(id=>{const canvas=el(id);if(!canvas)return;canvas.addEventListener('pointermove',e=>move(id,e));canvas.addEventListener('pointerdown',e=>{if(e.pointerType==='touch')canvas.setPointerCapture(e.pointerId);move(id,e);});canvas.addEventListener('pointerleave',e=>{if(e.pointerType!=='touch')hideTip(id);});canvas.addEventListener('pointercancel',()=>hideTip(id));});
function drawAll(){Object.keys(definitions).forEach(draw);set('historyStatus',tr(historyState));}
let refreshing=false,historyRefreshing=false,lastHistoryAttempt=0;
async function fetchJson(url){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),25000);try{const response=await fetch(url,{cache:'no-store',credentials:'same-origin',signal:controller.signal});const data=await response.json();return {ok:response.ok,data};}finally{clearTimeout(timer);}}
async function refreshHistory(){
 if(historyRefreshing)return;historyRefreshing=true;lastHistoryAttempt=Date.now();
 try{const {ok,data}=await fetchJson(app.historyEndpoint);window.dispatchEvent(new CustomEvent('anma-history',{detail:data}));if(!ok)throw Error(data.error||'History unavailable');history=Array.isArray(data.series)?data.series:[];const fields=['pv','load','grid','soc','battery'];const hasValues=history.some(row=>fields.some(k=>reading(row[k])!==null));historyState=!hasValues?'historyEmpty':data.demo?'historyDemo':history.some(row=>fields.some(k=>reading(row[k])===null))?'historyPartial':'historyLive';}
 catch(error){history=[];historyState='historyFailed';window.dispatchEvent(new CustomEvent('anma-history',{detail:{error:error.message}}));}
 finally{historyRefreshing=false;drawAll();}
}
async function refresh(){
 if(refreshing)return;refreshing=true;
 try{const {ok,data}=await fetchJson(app.endpoint);if(!ok&&!data.error)throw Error('Offline');render({...data,online:ok&&data.online===true});}
 catch(error){render({...latest,online:false,error:'connection_failed'});}
 finally{refreshing=false;}
 if(Date.now()-lastHistoryAttempt>=60000)refreshHistory();
}
window.addEventListener('resize',drawAll);window.addEventListener('anma-theme',drawAll);
window.addEventListener('anma-language',()=>{if(latest)render(latest);drawAll();});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
refresh();refreshHistory();drawAll();setInterval(()=>{if(!document.hidden)refresh();},10000);
})();
