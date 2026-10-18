(()=>{
 const root=document.querySelector('#machine-live');if(!root)return;
 const status=document.querySelector('#machine-status'),updated=document.querySelector('#machine-updated'),button=document.querySelector('#machine-refresh');
 let busy=false;
 const time=value=>value?new Date(value).toLocaleString('uk-UA'):'—';
 const clear=()=>root.querySelectorAll('.metric-value,.metric-updated').forEach(el=>el.textContent='—');
 async function refresh(){
  if(busy||document.hidden)return;busy=true;button.disabled=true;
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),35000);
  try{
   const response=await fetch(root.dataset.url,{credentials:'same-origin',cache:'no-store',signal:controller.signal});
   if(response.redirected||response.status===401||response.status===403){clear();status.textContent='Сесія завершилась або немає дозволу. Увійдіть в адмінку.';updated.textContent='';return;}
   const data=await response.json();
   if(!response.ok||!data.online){clear();const errors={live_not_bound:'Ця машина ще не має Live-підключення.',connection_disabled:'Підключення призупинено.',connection_failed:'Не вдалося з’єднатися з Home Assistant.',invalid_or_expired_code:'Ключ читання відкликано або недійсний.'};status.textContent=errors[data.error]||'Дані недоступні. Перевірте підключення машини.';updated.textContent='';return;}
   for(const metric of data.metrics){
    const row=root.querySelector(`[data-metric="${metric.key}"]`);if(!row)continue;
    const value=metric.value;
    row.querySelector('.metric-value').textContent=value===null||value===undefined?'Немає даних':typeof value==='boolean'?(value?'Так':'Ні'):`${value}${metric.unit?' '+metric.unit:''}`;
    row.querySelector('.metric-updated').textContent=time(metric.source_updated_at);
   }
   status.textContent='Дані отримано · лише читання';updated.textContent='Останній запит: '+time(data.updated_at);
  }catch{clear();status.textContent='Немає зв’язку. Повторимо запит автоматично.';updated.textContent='';}
  finally{clearTimeout(timeout);busy=false;button.disabled=false;}
 }
 button.addEventListener('click',refresh);
 document.querySelector('#machine-select').addEventListener('change',event=>location.assign(event.target.value));
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
 refresh();setInterval(refresh,10000);
})();
