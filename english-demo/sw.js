const CACHE = 'daily-quote-card-shell-v2';
const BASE = new URL('./',self.location.href);
const CORE = ['./','index.html','style.css','aquila.css','app.js','deck.json','manifest.webmanifest','icons/icon-192.png','icons/icon-512.png'].map(p=>new URL(p,BASE).href);
self.addEventListener('install',event => event.waitUntil((async()=>{
  const cache=await caches.open(CACHE);await cache.addAll(CORE);
  const response=await cache.match(new URL('deck.json',BASE).href);const deck=await response.json();
  await Promise.all(deck.quotes.filter(q=>q.imageAvailable).map(q=>cache.add(new URL(`images/${q.image}`,BASE).href)));
  await self.skipWaiting();
})()));
self.addEventListener('activate',event=>event.waitUntil((async()=>{
  await Promise.all((await caches.keys()).filter(k=>k.startsWith('daily-quote-card-')&&k!==CACHE).map(k=>caches.delete(k)));
  await self.clients.claim();
})()));
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  // Own-origin assets only: never claim access to a GAS iframe's content or permissions.
  if(event.request.method!=='GET'||url.origin!==BASE.origin||!url.pathname.startsWith(BASE.pathname))return;
  event.respondWith((async()=>{
    const cache=await caches.open(CACHE);
    try{const response=await fetch(event.request);if(response.ok)await cache.put(event.request,response.clone());return response;}
    catch{const cached=await cache.match(event.request);if(cached)return cached;
      if(event.request.mode==='navigate')return cache.match(new URL('index.html',BASE).href);
      return Response.error();}
  })());
});
self.addEventListener('notificationclick',event=>{
  event.notification.close();event.waitUntil((async()=>{
    const windows=await self.clients.matchAll({type:'window',includeUncontrolled:true});
    const existing=windows.find(c=>c.url.startsWith(BASE.href));if(existing)return existing.focus();
    return self.clients.openWindow(BASE.href);
  })());
});
