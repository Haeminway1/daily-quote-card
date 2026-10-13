const $ = (id) => document.getElementById(id);
const KEY = 'daily-quote-card:v1';
const strings = {
  en: {eyebrow:'A FRESH PERSPECTIVE',heading:'A thought for today.',subheading:'Twelve original reflections. A moment to make one your own.',author:'Original reflection',next:'Draw a card <span aria-hidden="true">↗</span>',journal:'A note to yourself',privacy:'Your notes stay in this browser, on this device.',install:'Install app',notify:'Try a test notification',help:'About Daily Quote Card',about:'Twelve original reflections written for this app. Saved cards and notes are stored only in this browser.',notificationHelp:'Notifications here are an immediate, optional test. Daily or background push reminders are not enabled. On iPhone/iPad, notification support requires iOS/iPadOS 16.4 or later and a Home Screen installation; device settings still apply.',offlineHelp:'Cards can be read offline after your first online visit. Clearing browser storage removes saved notes.',footer:'Made by Haeminway',installTitle:'Add Daily Quote Card to your Home Screen',installHelp:'On iPhone/iPad: open this page in Safari, tap Share, then Add to Home Screen. On other browsers, look for Install app in the browser menu. Availability depends on your browser.',close:'Got it',placeholder:'What does this bring to mind?',pending:'Illustration in progress',saved:'Saved on device',savedCard:'Card saved',removed:'Card removed from saved',save:'Save card',unsave:'Unsave card',share:'Share card',copied:'Card copied',shareFail:'Sharing is unavailable here. You can select and copy the card.',storageFail:'Browser storage is unavailable. Your changes will last only while this page stays open.',loadingFail:'The cards could not load. Please reconnect and reload.',notifyUnsupported:'Notifications are not supported in this browser. On iPhone/iPad, install to the Home Screen first.',denied:'Notifications are blocked. You can change this in browser settings.',notifySent:'An immediate test notification was sent. Background reminders are not enabled.',notifyFail:'A notification could not be sent. Check device and browser settings.',installed:'Already running as an installed app.',offline:'You are offline. Cached cards are still available.',ready:'Ready for a fresh perspective.',counter:(n,of)=>`Card ${n} of ${of}`},
  ko: {eyebrow:'오늘을 위한 새로운 시선',heading:'오늘의 생각 한 장.',subheading:'직접 쓴 열두 가지 생각. 나만의 의미를 더해보세요.',author:'직접 쓴 생각',next:'다른 카드 뽑기 <span aria-hidden="true">↗</span>',journal:'나에게 남기는 메모',privacy:'메모는 이 기기의 브라우저에만 저장됩니다.',install:'앱 설치',notify:'테스트 알림 보내기',help:'Daily Quote Card 소개',about:'이 앱을 위해 직접 쓴 열두 가지 생각입니다. 저장한 카드와 메모는 이 브라우저에만 보관됩니다.',notificationHelp:'알림은 선택해서 즉시 보내는 테스트입니다. 매일 알림이나 백그라운드 푸시는 제공하지 않습니다. iPhone/iPad는 iOS/iPadOS 16.4 이상에서 홈 화면 설치가 필요하며, 기기 설정에 따라 달라집니다.',offlineHelp:'온라인으로 한 번 방문하면 오프라인에서도 카드를 읽을 수 있습니다. 브라우저 저장 공간을 지우면 메모도 삭제됩니다.',footer:'Haeminway 제작',installTitle:'홈 화면에 Daily Quote Card 추가',installHelp:'iPhone/iPad에서는 Safari로 열고 공유 → 홈 화면에 추가를 누르세요. 다른 브라우저에서는 메뉴의 앱 설치를 확인하세요. 설치 지원은 브라우저마다 다릅니다.',close:'확인',placeholder:'어떤 생각이 떠오르나요?',pending:'그림을 준비하고 있어요',saved:'기기에 저장됨',savedCard:'카드를 저장했어요',removed:'저장한 카드에서 삭제했어요',save:'카드 저장',unsave:'카드 저장 해제',share:'카드 공유',copied:'카드를 복사했어요',shareFail:'이 환경에서 공유할 수 없습니다. 문장을 선택해서 복사할 수 있어요.',storageFail:'브라우저 저장 공간을 사용할 수 없습니다. 페이지를 닫으면 변경 사항이 사라집니다.',loadingFail:'카드를 불러오지 못했습니다. 인터넷에 연결한 후 새로고침하세요.',notifyUnsupported:'이 브라우저는 알림을 지원하지 않습니다. iPhone/iPad는 먼저 홈 화면에 설치하세요.',denied:'알림이 차단되어 있습니다. 브라우저 설정에서 변경할 수 있어요.',notifySent:'즉시 테스트 알림을 보냈어요. 백그라운드 알림은 제공하지 않습니다.',notifyFail:'알림을 보내지 못했습니다. 기기와 브라우저 설정을 확인하세요.',installed:'설치한 앱으로 실행 중입니다.',offline:'오프라인입니다. 저장된 카드를 읽을 수 있어요.',ready:'오늘의 카드를 만나보세요.',counter:(n,of)=>`${of}장 중 ${n}번째 카드`}
};
let state = {lang:'en',current:'q01',seen:[],notes:{},saved:[]};
let storageAvailable = true;
try {
  const value = JSON.parse(localStorage.getItem(KEY) || 'null');
  if (value && typeof value === 'object') {
    state.lang = value.lang === 'ko' ? 'ko' : 'en';
    if (typeof value.current === 'string') state.current = value.current;
    state.seen = Array.isArray(value.seen) ? value.seen.filter(x => typeof x === 'string') : [];
    state.saved = Array.isArray(value.saved) ? value.saved.filter(x => typeof x === 'string') : [];
    state.notes = value.notes && typeof value.notes === 'object' && !Array.isArray(value.notes) ? value.notes : {};
  }
} catch { storageAvailable = false; }
let quotes = [], installEvent;
const t = key => strings[state.lang][key];
function status(message) { $('status').textContent = message; }
function persist() {
  try { localStorage.setItem(KEY,JSON.stringify(state)); return true; }
  catch { storageAvailable = false; status(t('storageFail')); return false; }
}
function current() { return quotes.find(q => q.id === state.current) || quotes[0]; }
function render() {
  const q = current(); if (!q) return;
  document.documentElement.lang = state.lang;
  $('language').value = state.lang;
  document.querySelectorAll('[data-i18n]').forEach(el => { el.innerHTML = t(el.dataset.i18n); });
  $('note').placeholder = t('placeholder');
  $('quote-text').textContent = state.lang === 'ko' ? q.ko : q.text;
  $('quote-text').dataset.quoteId = q.id;
  $('theme').textContent = state.lang === 'ko' ? '오늘의 생각' : q.theme;
  $('counter').textContent = t('counter')(quotes.indexOf(q)+1,quotes.length);
  $('media').replaceChildren();
  if (q.imageAvailable) {
    const img = new Image(); img.src = `images/${q.image}`; img.alt = ''; img.width=675; img.height=1200; img.decoding='async';
    img.addEventListener('error',() => showPending()); $('media').append(img);
  } else showPending();
  $('note').value = typeof state.notes[q.id] === 'string' ? state.notes[q.id] : '';
  $('note-status').textContent = $('note').value && storageAvailable ? t('saved') : '';
  const saved = state.saved.includes(q.id);
  $('bookmark').setAttribute('aria-pressed',String(saved));
  $('bookmark').setAttribute('aria-label',t(saved?'unsave':'save'));
  $('share').setAttribute('aria-label',t('share'));
}
function showPending() { const el = document.createElement('span');el.className='pending';el.textContent=t('pending');$('media').replaceChildren(el); }
$('language').addEventListener('change',e => { state.lang = e.target.value === 'ko' ? 'ko':'en'; persist(); render(); status(navigator.onLine ? t('ready'):t('offline')); });
$('next').addEventListener('click',() => {
  let candidates = quotes.filter(q => !state.seen.includes(q.id));
  if (!candidates.length) { state.seen=[]; candidates=quotes.filter(q=>q.id!==state.current); }
  const q = candidates[Math.floor(Math.random()*candidates.length)];
  state.current=q.id; state.seen.push(q.id);persist();render();$('quote-text').focus();
});
$('note').addEventListener('input',e => { state.notes[current().id]=e.target.value; $('note-status').textContent=persist()?t('saved'):''; });
$('bookmark').addEventListener('click',() => { const q=current(),saved=state.saved.includes(q.id);state.saved=saved?state.saved.filter(id=>id!==q.id):[...state.saved,q.id];const ok=persist();render();if(ok)status(t(saved?'removed':'savedCard')); });
$('share').addEventListener('click',async () => {
  const text = `${$('quote-text').textContent}\n— ${t('author')}`;
  try { if(navigator.share) await navigator.share({title:'Daily Quote Card',text,url:location.href});else if(navigator.clipboard){await navigator.clipboard.writeText(text);status(t('copied'));}else status(t('shareFail')); }
  catch(e) { if(e.name!=='AbortError')status(t('shareFail')); }
});
window.addEventListener('beforeinstallprompt',e => { e.preventDefault();installEvent=e; });
$('install').addEventListener('click',async () => {
  if(window.matchMedia('(display-mode: standalone)').matches || navigator.standalone){status(t('installed'));return;}
  if(installEvent){await installEvent.prompt();await installEvent.userChoice;installEvent=null;}
  else $('install-help').showModal();
});
const swReady = 'serviceWorker' in navigator && window.isSecureContext
  ? Promise.race([navigator.serviceWorker.register('./sw.js').then(()=>navigator.serviceWorker.ready),new Promise(r=>setTimeout(()=>r(null),8000))]).catch(()=>null)
  : Promise.resolve(null);
$('notify').addEventListener('click',async () => {
  if(!('Notification' in window)||!('serviceWorker' in navigator)||!window.isSecureContext){status(t('notifyUnsupported'));return;}
  try {
    // Request permission immediately inside the user gesture, before any awaited setup.
    const permission=await Notification.requestPermission();
    if(permission!=='granted'){status(t('denied'));return;}
    const reg=await swReady;if(!reg){status(t('notifyFail'));return;}
    await reg.showNotification('Daily Quote Card',{body:state.lang==='ko'?current().ko:current().text,icon:'icons/icon-192.png',badge:'icons/icon-192.png',tag:'daily-quote-card-test',data:{url:location.href}});
    status(t('notifySent'));
  }catch{status(t('notifyFail'));}
});
window.addEventListener('offline',()=>status(t('offline')));
window.addEventListener('online',()=>status(t('ready')));
try {
  const response=await fetch('./deck.json');if(!response.ok)throw new Error('deck');
  const data=await response.json();quotes=data.quotes.filter(q=>/^q\d\d$/.test(q.id)&&typeof q.text==='string'&&typeof q.ko==='string');
  if(!quotes.length)throw new Error('empty');
  state.current=current().id;
  state.seen=[...new Set([...state.seen.filter(id=>quotes.some(q=>q.id===id)),state.current])];
  persist();render();status(storageAvailable?(navigator.onLine?t('ready'):t('offline')):t('storageFail'));
}catch{status(t('loadingFail'));$('next').disabled=true;}
