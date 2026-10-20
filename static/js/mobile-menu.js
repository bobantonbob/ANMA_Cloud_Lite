(()=>{const menu=document.querySelector('.mobile-menu');if(!menu)return;
document.querySelector('[data-mobile-language]').addEventListener('click',()=>setLanguage(document.documentElement.lang==='uk'?'en':'uk'));
document.querySelector('[data-mobile-theme]').addEventListener('click',()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark'));
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&menu.open){menu.open=false;menu.querySelector('summary').focus();}});
document.addEventListener('click',e=>{if(!menu.contains(e.target))menu.open=false;});
})();
document.querySelectorAll('.android-download').forEach(panel=>{
document.addEventListener('click',event=>{if(!panel.contains(event.target))panel.open=false;});
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&panel.open){panel.open=false;panel.querySelector('summary').focus();}});
});
