const {chromium}=require('playwright');
const path=require('path');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 for(const width of [1440,390]){
  const page=await browser.newPage({viewport:{width,height:1000}});
  for(const name of ['login','homes','connect','operations']){
   await page.goto('file:///'+path.resolve(__dirname,'screenshots',name+'.html').replaceAll('\\','/'));
   await page.waitForLoadState('networkidle');
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
   await page.screenshot({path:path.resolve(__dirname,'screenshots',`${name}-${width}.png`),fullPage:true});
   console.log(`${name} ${width}px: overflow=${overflow}`);
   if(overflow)process.exitCode=1;
  }
  await page.close();
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
