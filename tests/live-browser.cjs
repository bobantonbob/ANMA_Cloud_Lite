const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const auth=JSON.parse(fs.readFileSync('.backups/live-integration/browser-auth.json','utf8'));
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
 const context=await browser.newContext({hasTouch:true,viewport:{width:1440,height:1000}});
 await context.addCookies([{name:auth.name,value:auth.value,domain:'127.0.0.1',path:'/',httpOnly:true,sameSite:'Lax'}]);
 const page=await context.newPage();const errors=[],liveRequests=[];let lastLive=null;
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(r.url().includes('/live/?mode=live'))liveRequests.push(Date.now());});
 page.on('response',async r=>{if(r.url().includes('/live/?mode=live')&&r.status()===200)lastLive=await r.json();});
 await page.goto(`http://127.0.0.1:8095/app/?plant=${auth.plant}&mode=live`);
 await page.waitForFunction(()=>document.querySelector('#flowConnection').textContent==='LIVE');
 await page.waitForFunction(()=>document.querySelector('#historyStatus').textContent.includes('історія')||document.querySelector('#historyStatus').textContent.includes('Історія'));
 assert.equal(await page.locator('body').getAttribute('data-mode'),'live');
 assert.ok(lastLive&&!lastLive.demo&&lastLive.online);
 assert.equal(await page.locator('#flowPv').innerText(),(lastLive.pv_power/1000).toFixed(2));
 assert.equal(await page.locator('#forecastToday').innerText(),lastLive.forecast_today.toFixed(1));
 assert.match(await page.locator('#faultStatus').innerText(),/НЕМАЄ ДАНИХ/);
 assert.equal(await page.locator('.flow-solar').getAttribute('data-state'),'idle');
 const chart=page.locator('#batteryChart');await chart.scrollIntoViewIfNeeded();const bounds=await chart.boundingBox();await page.mouse.move(bounds.x+bounds.width-46,bounds.y+90);
 assert.equal(await page.locator('#batteryReticle').isVisible(),true);
 assert.match(await page.locator('#batteryTooltip').innerText(),/BATTERY: -/);
 assert.match(await page.locator('#batteryTooltip').innerText(),/SOC:/);
 await page.waitForTimeout(11000);
 assert.ok(liveRequests.length>=2,'Actual 10-second refresh');
 assert.ok(liveRequests[1]-liveRequests[0]>=9000&&liveRequests[1]-liveRequests[0]<12500,'Polling interval');
 for(const width of [320,375,768,1440]){
  await page.setViewportSize({width,height:1000});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`overflow at ${width}`);
  if(width===375){await chart.scrollIntoViewIfNeeded();const touchBounds=await chart.boundingBox();await page.touchscreen.tap(touchBounds.x+touchBounds.width-45,touchBounds.y+90);assert.equal(await page.locator('#batteryTooltip').isVisible(),true);}
  await page.evaluate(()=>window.scrollTo(0,0));
  if([375,1440].includes(width))await page.screenshot({path:`tests/live-${width}.png`,fullPage:true});
 }
 await page.getByRole('button',{name:'Demo',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('#flowConnection').textContent==='DEMO');
 assert.equal(await page.locator('body').getAttribute('data-mode'),'demo');
 assert.match(await page.locator('#historyStatus').innerText(),/Демонстраційна/);
 await page.getByRole('button',{name:'Live · Home Assistant',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('#flowConnection').textContent==='LIVE');
 await page.locator('#langBtn').click();
 assert.match(await page.locator('#historyStatus').innerText(),/history/);
 assert.match(await page.locator('[data-i18n=forecastDemo]').first().innerText(),/Home Assistant/);
 assert.deepEqual(errors,[]);
 console.log('PASS: actual Django + HA values, forecasts, fault unknown, real history tooltip, negative battery, 10-second refresh, Demo/Live, EN, 320–1440 px; no browser errors.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
