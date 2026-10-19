const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const script=fs.readFileSync('static/js/dashboard.js','utf8');
let language='uk';
const context={lang:()=>language};vm.createContext(context);
vm.runInContext(script.slice(script.indexOf('const reading='),script.indexOf('const magnitude=')),context);
for(const [input,value,unit] of [[30,'30','Вт'],[999,'999','Вт'],[1000,'1.000','кВт'],[11040,'11.040','кВт'],[-30,'-30','Вт'],[-11040,'-11.040','кВт'],[0,'0','Вт'],[null,'—','Вт'],['unavailable','—','Вт']]){
 const actual=context.power(input);assert.equal(actual.value,value);assert.equal(actual.unit,unit);
}
language='en';assert.equal(context.power(30).unit,'W');assert.equal(context.power(1000).unit,'kW');
console.log('Adaptive power units, precision, signed history and missing readings: OK');
