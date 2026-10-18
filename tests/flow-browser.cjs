const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 let response={online:true,demo:true,pv_power:3200,load_power:1200,battery_power:1000,battery_soc:64,grid_power:-1000,grid_available:true,grid_voltage:230,daily_pv:12,forecast_today:20,forecast_tomorrow:25,fault_code:'0',updated_at:'2026-10-17T12:00:00+03:00'};
 let fail=false;
 await page.route('**/tests/telemetry.json*',r=>r.fulfill({status:fail?503:200,contentType:'application/json',body:JSON.stringify(response)}));
 await page.addInitScript(()=>{window.setInterval=fn=>{window.refreshTelemetry=fn;return 1;};});
 await page.goto('http://127.0.0.1:8097/tests/preview.html');
 await page.waitForFunction(()=>document.getElementById('flowPv').textContent==='3.20');
 const path=type=>page.locator('.'+type+'-particle animateMotion').getAttribute('path');
 assert.equal(await path('battery'),'M300 230 V313');assert.equal(await path('grid'),'M260 205 H107');
 assert.match(await page.locator('#flowBatteryStatus').innerText(),/ЗАРЯД/);
 async function refresh(){await page.evaluate(()=>window.refreshTelemetry());await page.waitForTimeout(100);}
 response={...response,pv_power:0,battery_power:-1000,grid_power:200};await refresh();
 assert.equal(await path('battery'),'M300 313 V230');assert.equal(await path('grid'),'M107 205 H260');
 assert.equal(await page.locator('.flow-solar').getAttribute('data-state'),'idle');
 assert.equal(await page.locator('.solar-particle').evaluate(n=>getComputedStyle(n).opacity),'0');
 response={...response,grid_available:false,grid_power:200};await refresh();
 assert.match(await page.locator('#gridHealth').innerText(),/ВІДСУТНЯ/);assert.equal(await page.locator('.flow-grid').getAttribute('data-state'),'unavailable');
 assert.equal(await page.locator('.grid-particle').evaluate(n=>getComputedStyle(n).opacity),'0');
 response={...response,pv_power:null,battery_power:'unavailable',battery_soc:null,grid_available:'unknown',grid_power:null};await refresh();
 assert.equal(await page.locator('#flowPv').innerText(),'—');assert.equal(await page.locator('#flowSoc').innerText(),'—');assert.match(await page.locator('#flowGridStatusText').innerText(),/НЕМАЄ ДАНИХ/);
 response={...response,pv_power:0,battery_power:0,battery_soc:0,grid_available:true,grid_power:0};await refresh();
 assert.equal(await page.locator('#flowSoc').innerText(),'0');assert.match(await page.locator('#flowBatteryStatus').innerText(),/БЕЗ ПЕРЕТОКУ/);
 fail=true;await refresh();assert.equal(await page.locator('.particle:not(.paused)').count(),0);assert.match(await page.locator('#updatedMobile').innerText(),/НЕМАЄ ЗВ/);assert.equal(await page.locator('#flowPv').innerText(),'—');
 fail=false;response={...response,pv_power:3200,battery_power:1000,battery_soc:64,grid_power:-1000};await refresh();
 assert.equal(await page.locator('body.telemetry-offline').count(),0);
 for(const language of ['uk','en']){
 await page.evaluate(l=>setLanguage(l),language);
 for(const theme of ['dark','light']){
 await page.evaluate(t=>setTheme(t),theme);
 for(const width of [320,375,690,768,1024,1440]){
 await page.setViewportSize({width,height:1000});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`overflow ${width} ${language} ${theme}`);
 const nodes=await page.locator('.flow-item').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();const p=n.parentElement.getBoundingClientRect();return r.left>=p.left-1&&r.right<=p.right+1&&r.top>=p.top-1&&r.bottom<=p.bottom+1}));
 assert.ok(nodes.every(Boolean),`flow bounds ${width} ${language}`);
 if(language==='uk'&&theme==='dark'&&[375,1440].includes(width))await page.screenshot({path:`tests/preview-${width}.png`,fullPage:true});
 }
 }
 }
 await page.emulateMedia({reducedMotion:'reduce'});assert.equal(await page.locator('.solar-particle').evaluate(n=>getComputedStyle(n).display),'none');
 assert.deepEqual(errors,[]);console.log('PASS: directions, night, grid outage, unknown, zero, offline/recovery, UK/EN, dark/light, 320–1440px, reduced motion; no browser errors');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
