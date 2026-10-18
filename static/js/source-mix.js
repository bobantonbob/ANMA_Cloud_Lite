(function(root){
'use strict';
function shares({pv,grid,battery,load,online}){
 if(!online||[pv,grid,battery,load].some(v=>typeof v!=='number'||!Number.isFinite(v))||load<=0)return null;
 const inputs=[Math.max(0,pv),Math.max(0,grid),Math.max(0,-battery)];
 const total=inputs.reduce((a,b)=>a+b,0);if(total<=0)return null;
 const exact=inputs.map(v=>v/total*100),rounded=exact.map(Math.floor);
 const missing=100-rounded.reduce((a,b)=>a+b,0);
 const order=exact.map((v,i)=>({i,rest:v-rounded[i]})).sort((a,b)=>b.rest-a.rest);
 for(let i=0;i<missing;i++)rounded[order[i].i]++;
 return {exact,rounded};
}
const calculate=shares;
if(typeof module!=='undefined')module.exports=calculate;
if(!root.document)return;
let latest;const ids=['sourceSolar','sourceGrid','sourceBattery'],colors=['#fbbf24','#57aeff','#22d6a1'];
function render(data){latest=data;const en=localStorage.getItem('anma_lang')==='en';const names=en?['Solar','Grid','Battery']:['Сонце','Мережа','Батарея'];const result=calculate(data);const legend=document.getElementById('sourceLegend'),ring=document.getElementById('sourceRing');if(!legend||!ring)return;legend.replaceChildren();let offset=0;
 ids.forEach((id,i)=>{const arc=document.getElementById(id),part=result?result.exact[i]:0;arc.style.strokeDasharray=`${part} ${100-part}`;arc.style.strokeDashoffset=String(-offset);offset+=part;const item=document.createElement('span'),dot=document.createElement('i');dot.style.background=colors[i];item.append(dot,`${names[i]} ${result?result.rounded[i]+'%':'—'}`);legend.append(item);});
 const hint=document.createElement('small');hint.textContent=result?(en?'Estimated source mix · incoming power':'Оцінка часток джерел · вхідна потужність'):(en?'Source mix unavailable: missing readings or no load':'Частки недоступні: немає показників або навантаження');legend.append(hint);ring.setAttribute('aria-label',legend.textContent);
}
root.addEventListener('anma-live',e=>render(e.detail));root.addEventListener('anma-language',()=>{if(latest)render(latest);});
})(typeof window==='undefined'?globalThis:window);
