/* Daily Quote Card — original deck/draw/thought mechanics blended into the
   accepted Aquila photo design. All state stays in this browser. */
const $ = (id) => document.getElementById(id);
const LEGACY_KEY = 'daily-quote-card:v1';           // previous build's data; read once, never rewritten
const PREF_KEY = 'daily-quote-card.prefs.v2';
const QKEY = 'daily-quote-card.quotes.v2';
const MEMO_KEY = 'daily-quote-card.memos.v2';
const DRAWN_KEY = 'daily-quote-card.drawn.v2';
const MIGRATION_KEY = 'daily-quote-card.migration.v1';
const strings = {
  en: {eyebrow:'A FRESH PERSPECTIVE',heading:'A thought for today.',subheading:'Twelve original reflections. A moment to make one your own.',author:'Original reflection',
    next:'Draw a card <span aria-hidden="true">↗</span>',history:'History',addQuote:'Add quote',
    readyText:'Pick one card from the flowing deck — today’s reflection arrives.',
    deckLabel:'Quote card deck. Drag a card down, or press Enter to draw.',
    hintIdle:'Pull a card down to draw',hintHold:'Keep pulling down slowly',hintRelease:'Let go to reveal the card',
    dismiss:'Dismiss card',memoCta:'Write your thought',
    addTitle:'Add a quote',addSub:'Add your own good thought to the deck.',
    qTextLabel:'Quote',qAuthorLabel:'Author or source',opt:'(optional)',
    qTextPlaceholder:'Write a line you want to keep close.',qAuthorPlaceholder:'Leave blank to save as Unknown.',
    memoTitle:'Your thought',memoLabel:'Your thought',memoPlaceholder:'What does this bring to mind?',
    errQuote:'Please enter the quote text.',errMemo:'Please enter your thought.',
    cancel:'Cancel',add:'Add',saveBtn:'Save',
    calTitle:'Card history',calBack:'‹ Back to month',calEmpty:'No cards or notes this month.',
    prevMonth:'Previous month',nextMonth:'Next month',
    memoSaved:'Thought saved',quoteAdded:'Quote added to the deck',
    addedCount:(n)=>`Now drawing from ${n} cards.`,
    saveFail:'Browser storage is unavailable. Changes could not be saved.',
    yourQuote:'Your quote',unknownAuthor:'Unknown',
    importedNote:'Imported note · original date unavailable',
    importedAt:(s)=>"Imported at "+s+" · original date unavailable",
    newCard:'New card:',dismissed:'Card dismissed. You can draw a new one.',
    cellLabel:(mon,d,n)=>`${mon} ${d} — ${n===1?'1 entry':n+' entries'}`,
    install:'Install app',notify:'Try a test notification',help:'About Daily Quote Card',
    about:'Twelve original reflections written for this app. Saved cards and notes are stored only in this browser.',
    notificationHelp:'Notifications here are an immediate, optional test. Daily or background push reminders are not enabled. On iPhone/iPad, notification support requires iOS/iPadOS 16.4 or later and a Home Screen installation; device settings still apply.',
    offlineHelp:'Cards can be read offline after your first online visit. Clearing browser storage removes saved notes.',
    footer:'Made by Haeminway',installTitle:'Add Daily Quote Card to your Home Screen',
    installHelp:'On iPhone/iPad: open this page in Safari, tap Share, then Add to Home Screen. On other browsers, look for Install app in the browser menu. Availability depends on your browser.',
    close:'Got it',pending:'Illustration in progress',
    savedCard:'Card saved',removed:'Card removed from saved',
    save:'Save card',unsave:'Unsave card',share:'Share card',copied:'Card copied',
    shareFail:'Sharing is unavailable here. You can select and copy the card.',
    storageFail:'Browser storage is unavailable. Your changes will last only while this page stays open.',
    loadingFail:'The cards could not load. Please reconnect and reload.',
    notifyUnsupported:'Notifications are not supported in this browser. On iPhone/iPad, install to the Home Screen first.',
    denied:'Notifications are blocked. You can change this in browser settings.',
    notifySent:'An immediate test notification was sent. Background reminders are not enabled.',
    notifyFail:'A notification could not be sent. Check device and browser settings.',
    installed:'Already running as an installed app.',offline:'You are offline. Cached cards are still available.',
    ready:'Ready for a fresh perspective.',counter:(n,of)=>`Card ${n} of ${of}`},
  ko: {eyebrow:'오늘을 위한 새로운 시선',heading:'오늘의 생각 한 장.',subheading:'직접 쓴 열두 가지 생각. 나만의 의미를 더해보세요.',author:'직접 쓴 생각',
    next:'카드 뽑기 <span aria-hidden="true">↗</span>',history:'기록',addQuote:'명언 추가',
    readyText:'흐르는 카드 중 마음에 닿는 한 장을 뽑아보세요. 오늘의 좋은 생각이 도착합니다.',
    deckLabel:'명언 카드 덱. 카드를 아래로 당기거나 Enter를 눌러 뽑으세요.',
    hintIdle:'원하는 카드를 아래로 당겨 뽑으세요',hintHold:'천천히 아래로 당겨주세요',hintRelease:'놓으면 카드가 뽑혀요',
    dismiss:'명언 카드 내리기',memoCta:'내 생각 메모',
    addTitle:'명언 추가',addSub:'나만의 좋은 생각을 덱에 더해보세요.',
    qTextLabel:'명언',qAuthorLabel:'작가 또는 출처',opt:'(선택)',
    qTextPlaceholder:'마음에 새기고 싶은 문장을 적어주세요.',qAuthorPlaceholder:'비워두면 ‘미상’으로 저장돼요.',
    memoTitle:'내 생각 메모',memoLabel:'내 생각',memoPlaceholder:'이 카드에 떠오른 생각을 자유롭게 적어보세요.',
    errQuote:'명언 내용을 입력해주세요.',errMemo:'메모 내용을 입력해주세요.',
    cancel:'취소',add:'추가',saveBtn:'저장',
    calTitle:'카드 기록',calBack:'‹ 달력으로',calEmpty:'이 달에는 뽑은 카드나 메모가 없어요.',
    prevMonth:'이전 달',nextMonth:'다음 달',
    memoSaved:'메모를 저장했어요',quoteAdded:'명언이 덱에 추가됐어요',
    addedCount:(n)=>`이제 ${n}장 중에서 뽑습니다.`,
    saveFail:'저장 공간을 사용할 수 없어 저장하지 못했어요',
    yourQuote:'내 명언',unknownAuthor:'미상',
    importedNote:'가져온 메모 · 원래 날짜는 알 수 없어요',
    importedAt:(s)=>s+" 에 가져옴 · 원래 날짜는 알 수 없어요",
    newCard:'새 카드:',dismissed:'명언 카드를 내렸습니다. 새 카드를 뽑을 수 있습니다.',
    cellLabel:(mon,d,n)=>`${mon} ${d}일, 기록 ${n}개`,
    install:'앱 설치',notify:'테스트 알림 보내기',help:'Daily Quote Card 소개',
    about:'이 앱을 위해 직접 쓴 열두 가지 생각입니다. 저장한 카드와 메모는 이 브라우저에만 보관됩니다.',
    notificationHelp:'알림은 선택해서 즉시 보내는 테스트입니다. 매일 알림이나 백그라운드 푸시는 제공하지 않습니다. iPhone/iPad는 iOS/iPadOS 16.4 이상에서 홈 화면 설치가 필요하며, 기기 설정에 따라 달라집니다.',
    offlineHelp:'온라인으로 한 번 방문하면 오프라인에서도 카드를 읽을 수 있습니다. 브라우저 저장 공간을 지우면 메모도 삭제됩니다.',
    footer:'Haeminway 제작',installTitle:'홈 화면에 Daily Quote Card 추가',
    installHelp:'iPhone/iPad에서는 Safari로 열고 공유 → 홈 화면에 추가를 누르세요. 다른 브라우저에서는 메뉴의 앱 설치를 확인하세요. 설치 지원은 브라우저마다 다릅니다.',
    close:'확인',pending:'그림을 준비하고 있어요',
    savedCard:'카드를 저장했어요',removed:'저장한 카드에서 삭제했어요',
    save:'카드 저장',unsave:'카드 저장 해제',share:'카드 공유',copied:'카드를 복사했어요',
    shareFail:'이 환경에서 공유할 수 없습니다. 문장을 선택해서 복사할 수 있어요.',
    storageFail:'브라우저 저장 공간을 사용할 수 없습니다. 페이지를 닫으면 변경 사항이 사라집니다.',
    loadingFail:'카드를 불러오지 못했습니다. 인터넷에 연결한 후 새로고침하세요.',
    notifyUnsupported:'이 브라우저는 알림을 지원하지 않습니다. iPhone/iPad는 먼저 홈 화면에 설치하세요.',
    denied:'알림이 차단되어 있습니다. 브라우저 설정에서 변경할 수 있어요.',
    notifySent:'즉시 테스트 알림을 보냈어요. 백그라운드 알림은 제공하지 않습니다.',
    notifyFail:'알림을 보내지 못했습니다. 기기와 브라우저 설정을 확인하세요.',
    installed:'설치한 앱으로 실행 중입니다.',offline:'오프라인입니다. 저장된 카드를 읽을 수 있어요.',
    ready:'오늘의 카드를 만나보세요.',counter:(n,of)=>`${of}장 중 ${n}번째 카드`}
};
let storageAvailable = true;
let state = {lang:'en',saved:[]};
let legacyState = null;
try { const v = JSON.parse(localStorage.getItem(LEGACY_KEY) || 'null'); if (v && typeof v === 'object') legacyState = v; }
catch { storageAvailable = false; }
try {
  const p = JSON.parse(localStorage.getItem(PREF_KEY) || 'null');
  if (p && typeof p === 'object') {
    if (p.lang === 'ko' || p.lang === 'en') state.lang = p.lang;
    if (Array.isArray(p.saved)) state.saved = p.saved.filter(x => typeof x === 'string');
  } else if (legacyState) {
    if (legacyState.lang === 'ko') state.lang = 'ko';
    if (Array.isArray(legacyState.saved)) state.saved = legacyState.saved.filter(x => typeof x === 'string');
  }
} catch { storageAvailable = false; }
const t = key => strings[state.lang][key];
function status(message) { $('status').textContent = message; }
function persistPrefs() {
  try { localStorage.setItem(PREF_KEY,JSON.stringify(state)); return true; }
  catch { storageAvailable = false; status(t('storageFail')); return false; }
}

/* ===================== local storage ===================== */
function lsGet(k){ try{ return JSON.parse(window.localStorage.getItem(k)||"null"); }catch(e){ return null; } }
function lsArray(k){ var value=lsGet(k); return Array.isArray(value)?value:[]; }
function lsSet(k,v){ try{ window.localStorage.setItem(k, JSON.stringify(v)); return true; }catch(e){ return false; } }
function bounded(list,limit){ return Array.isArray(list) ? list.slice(Math.max(0,list.length-limit)) : []; }
function safeString(value,max){ return String(value==null?"":value).slice(0,max); }
function normalizeQuotes(list){
  return bounded(list,200).filter(function(q){ return q && typeof q.t === "string" && q.t.trim(); }).map(function(q,i){
    return { id:safeString(q.id || ("custom-"+(i+1)),80), t:safeString(q.t,120), a:safeString(q.a || "",40) };
  });
}
function normalizeMemos(list){
  return bounded(list,500).filter(function(m){ return m && typeof m.thought === "string" && m.thought.trim(); }).map(function(m){
    var ts=Number(m.ts);
    return { id:safeString(m.id || (Date.now()+"-"+Math.random().toString(36).slice(2,6)),80), ts:Number.isFinite(ts)?ts:Date.now(),
      dateKey:safeString(m.dateKey || keyOf(new Date()),16), time:safeString(m.time || "",24),
      quoteId:safeString(m.quoteId || "",80), quoteSource:safeString(m.quoteSource || "",32),
      quote:safeString(m.quote || "",400), author:safeString(m.author || "",80), thought:safeString(m.thought,300),
      drawId:safeString(m.drawId || "",80), imported:!!m.imported };
  });
}
function normalizeDraws(list){
  return bounded(list,500).filter(function(d){ return d && d.quoteId; }).map(function(d){
    var ts=Number(d.ts);
    return { id:safeString(d.id || (Date.now()+"-"+Math.random().toString(36).slice(2,6)),80), ts:Number.isFinite(ts)?ts:Date.now(),
      dateKey:safeString(d.dateKey || keyOf(new Date()),16), time:safeString(d.time || "",24),
      quoteId:safeString(d.quoteId || "",80), quoteSource:safeString(d.quoteSource || "",32),
      quote:safeString(d.quote || "",400), author:safeString(d.author || "",80), custom:!!d.custom };
  });
}
function writeLocalState(){
  return lsSet(QKEY,customQuotes) && lsSet(MEMO_KEY,memos) && lsSet(DRAWN_KEY,drawnCards);
}
var testHook = window.DAILY_QUOTE_CARD_TEST = window.DAILY_QUOTE_CARD_TEST || {};
function seededRandom(seed){
  var state = Number.isFinite(seed) ? Math.trunc(seed) : 0;
  state = (state >>> 0) || 1;
  return function(){ state = (state * 1664525 + 1013904223) >>> 0; return state / 4294967296; };
}
var random = Number.isFinite(Number(testHook.seed)) ? seededRandom(Number(testHook.seed)) : Math.random;
function updateStorageHook(){
  testHook.storageReady = true;
  testHook.storageMode = "local";
  testHook.customQuoteCount = customQuotes.length;
  testHook.memoCount = memos.length;
  testHook.drawnCardCount = drawnCards.length;
  testHook.publicQuoteCount = BASE_QUOTES.length;
  testHook.totalQuoteCount = QUOTES.length;
}
function markStorageError(message){
  testHook.lastStorageError = message;
  storageAvailable = false;
  showToast(t("saveFail"));
}
function persistState(done){
  var ok = writeLocalState();
  updateStorageHook();
  if(!ok) markStorageError("local storage write failed");
  if(done) done(ok);
  return ok;
}

/* ===================== date helpers ===================== */
var WD={en:["Sun","Mon","Tue","Wed","Thu","Fri","Sat"],ko:["일","월","화","수","목","금","토"]};
var MON_EN=["January","February","March","April","May","June","July","August","September","October","November","December"];
function pad(n){ return n<10?"0"+n:""+n; }
function keyOf(d){ return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate()); }
function monthName(m){ return state.lang==="ko" ? (m+1)+"월" : MON_EN[m]; }
function fmtFull(d){
  if(state.lang==="ko") return d.getFullYear()+"년 "+(d.getMonth()+1)+"월 "+d.getDate()+"일 ("+WD.ko[d.getDay()]+")";
  return MON_EN[d.getMonth()]+" "+d.getDate()+", "+d.getFullYear()+" ("+WD.en[d.getDay()]+")";
}
function fmtTime(d){
  var h=d.getHours(), hh=h%12; if(hh===0)hh=12;
  if(state.lang==="ko") return (h<12?"오전":"오후")+" "+hh+":"+pad(d.getMinutes());
  return hh+":"+pad(d.getMinutes())+" "+(h<12?"AM":"PM");
}

/* ===================== data ===================== */
var BASE_QUOTES=[], QUOTES=[], beltImages=[], deckLoadFailed=false;
var memos = normalizeMemos(lsArray(MEMO_KEY));
var customQuotes = normalizeQuotes(lsArray(QKEY));
var drawnCards = normalizeDraws(lsArray(DRAWN_KEY));
var quoteBag=[];
function rebuildQuotes(resetBag){
  QUOTES = BASE_QUOTES.slice();
  customQuotes.forEach(function(c,i){ QUOTES.push({id:c.id || ("custom-"+(i+1)), t:c.t, a:c.a, custom:true, source:"local"}); });
  if(resetBag) quoteBag=[];
  updateStorageHook();
}
function migrateLegacyNotes(){
  var done=false;
  try{ done=!!window.localStorage.getItem(MIGRATION_KEY); }catch(e){ done=true; }
  if(done) return;
  var notes = legacyState && legacyState.notes && typeof legacyState.notes==="object" && !Array.isArray(legacyState.notes) ? legacyState.notes : {};
  var ids = Object.keys(notes).filter(function(k){ return typeof notes[k]==="string" && notes[k].trim(); });
  if(ids.length){
    var now=new Date(), stamp=now.getTime();
    ids.forEach(function(qid,i){
      var q=null;
      for(var j=0;j<BASE_QUOTES.length;j++){ if(BASE_QUOTES[j].id===qid){ q=BASE_QUOTES[j]; break; } }
      memos.push({ id:"import-"+stamp+"-"+i, ts:stamp+i, dateKey:keyOf(now), time:fmtTime(now),
        quoteId:safeString(qid,80), quoteSource:"imported",
        quote:q?(state.lang==="ko"&&q.ko?q.ko:q.t):"", author:q?safeString(q.a,80):"",
        thought:safeString(notes[qid],300), drawId:"", imported:true });
    });
    memos = normalizeMemos(memos);
    writeLocalState();
  }
  try{ window.localStorage.setItem(MIGRATION_KEY, String(Date.now())); }catch(e){}
}

/* ===================== elements ===================== */
var deck=$("deck"), belt=$("belt"), drawCard=$("drawCard");
var deckArea=deck?deck.closest(".stage"):null;
var hint=$("hint"), ready=$("ready");
var quoteCard=$("quoteCard"), quoteText=$("quoteText"), quoteAuthor=$("quoteAuthor");
var quoteTheme=$("quoteTheme"), quoteIndex=$("quoteIndex"), quoteMedia=$("quoteMedia");
var quoteDismiss=$("quoteDismiss"), result=$("result");
var memoCta=$("memoCta"), live=$("live"), drawButton=$("drawButton");
var bookmarkBtn=$("bookmark"), shareBtn=$("share");

/* ===================== belt geometry ===================== */
var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
var N=7, CARD_W=178, CARD_H=240, GAP=124, SPAN=N*GAP, TRACK_OFFSET=GAP/2, BASE_TOP=36, ARC_H=22, MAX_TILT=14;
var SPEED = reduce ? 0 : 26;        // px / second
var THRESHOLD = 120;
var cards=[], cx=0, HALF=0;
function measure(){
  cx=deck.clientWidth/2; HALF=cx;
  ARC_H=(HALF*Math.tan(MAX_TILT*Math.PI/180))/2;
}
function cardInner(i){
  var img=beltImages.length?beltImages[i%beltImages.length]:"";
  return img ? '<img class="card-img" src="images/'+img+'" alt="" draggable="false">'
             : '<span class="card-img card-fallback"></span>';
}
function buildDeck(){
  belt.innerHTML=""; cards=[];
  for(var i=0;i<N;i++){ var c=document.createElement("div"); c.className="card belt-card"; c.innerHTML=cardInner(i); belt.appendChild(c); cards.push(c); }
  drawCard.innerHTML=cardInner(0);
}
function clamp(v,a,b){ return v<a?a:(v>b?b:v); }
function beltX(i){ var raw=i*GAP+pos+TRACK_OFFSET; return ((raw%SPAN)+SPAN)%SPAN - SPAN/2; }
function styleFor(x){
  var u=HALF?x/HALF:0;
  var y=BASE_TOP+ARC_H*Math.min(1,u*u);
  var tilt=clamp(u*MAX_TILT,-MAX_TILT,MAX_TILT);
  var scale=Math.max(0.86,1-Math.abs(u)*0.08);
  var dist=Math.abs(x), edge=HALF*0.72;
  var op=dist<=edge?1:Math.max(0,1-(dist-edge)/(HALF*0.55));
  var z=Math.round(1000+x);
  return {x:x,y:y,tilt:tilt,scale:scale,op:op,z:z};
}
function composeTransform(s,extra){
  return "translate("+(cx+s.x-CARD_W/2)+"px,"+s.y+"px) rotate("+s.tilt+"deg) scale("+s.scale+")"+(extra||"");
}
function apply(el,s,op){
  el.style.transform=composeTransform(s);
  el.style.opacity=(op==null?s.op:op);
  if(s.z!=null) el.style.zIndex=s.z;
}

/* ===================== belt loop ===================== */
var pos=0, spinning=true, holding=false, drawing=false, centerIdx=0, lastT=0;
function nearestCenter(){ var b=0,bd=1e9; for(var i=0;i<N;i++){var d=Math.abs(beltX(i)); if(d<bd){bd=d;b=i;}} return b; }
function tick(){
  var now=(window.performance&&performance.now)?performance.now():Date.now();
  if(!lastT) lastT=now;
  var dt=Math.min(0.05,(now-lastT)/1000); lastT=now;
  if(spinning&&!holding){ pos-=SPEED*dt; if(pos<-SPAN) pos+=SPAN; }
  for(var i=0;i<N;i++){ if(holding&&i===centerIdx) continue; apply(cards[i],styleFor(beltX(i))); }
}

/* ===================== grab / draw ===================== */
var base=null;
function eventPoint(e){
  var p=e.touches&&e.touches[0]?e.touches[0]:e;
  return {x:p.clientX,y:p.clientY};
}
function cardAtPoint(clientX,clientY){
  var rect=deck.getBoundingClientRect(), x=clientX-rect.left, y=clientY-rect.top;
  var best=-1, score=1e9;
  for(var i=0;i<N;i++){
    var s=styleFor(beltX(i));
    if(s.op<0.2) continue;
    var left=cx+s.x-CARD_W/2, top=s.y, padX=10, padY=8;
    if(x<left-padX||x>left+CARD_W+padX||y<top-padY||y>top+CARD_H+padY) continue;
    var dx=Math.abs(x-(left+CARD_W/2)), dy=Math.abs(y-(top+CARD_H/2))*0.25;
    var next=dx+dy+(1-s.op)*90;
    if(next<score){ score=next; best=i; }
  }
  return best;
}
function grabCard(idx,source){
  spinning=false; holding=true; centerIdx=idx==null?nearestCenter():idx;
  if(deckArea) deckArea.classList.add("is-drawing");
  base=styleFor(beltX(centerIdx));
  for(var i=0;i<N;i++){ apply(cards[i],styleFor(beltX(i))); }
  cards[centerIdx].style.opacity="0";
  drawCard.innerHTML=cards[centerIdx].innerHTML;
  apply(drawCard,base,1); drawCard.style.zIndex="3000"; drawCard.style.transition="none"; drawCard.style.opacity="1";
  testHook.lastGrabIndex=centerIdx;
  testHook.lastGrabX=Math.round(base.x);
  testHook.lastGrabSource=source||"keyboard";
}
function releaseCenter(){
  holding=false; drawCard.style.opacity="0"; spinning=true;
  if(deckArea) deckArea.classList.remove("is-drawing");
}
var dragging=false,startY=0,curDy=0,moved=0,pointerId=null,armed=false;
function setHeld(on){ deck.classList.toggle("is-held",on); }
function onDown(e){
  if(drawing||!quoteCard.hidden) return;
  var point=eventPoint(e), hit=cardAtPoint(point.x,point.y);
  if(hit<0){ testHook.lastDeckMiss=true; return; }
  dragging=true; armed=false; moved=0; curDy=0;
  startY=point.y; pointerId=e.pointerId;
  if(e.pointerId!=null&&deck.setPointerCapture){ try{deck.setPointerCapture(e.pointerId);}catch(_){} }
  setHeld(true); grabCard(hit,"pointer"); setHint("hold");
}
function onMove(e){
  if(!dragging) return;
  var y=(e.touches?e.touches[0].clientY:e.clientY), dy=y-startY;
  moved=Math.max(moved,Math.abs(dy));
  if(dy<0) dy=dy*0.26; curDy=dy;
  var p=clamp(dy/THRESHOLD,0,1);
  apply(drawCard,{x:base.x*(1-p),y:base.y+dy,tilt:base.tilt*(1-p),scale:base.scale+p*0.05,z:3000},1);
  if(dy>=THRESHOLD&&!armed){ armed=true; setHint("release"); buzz(); }
  else if(dy<THRESHOLD&&armed){ armed=false; setHint("hold"); }
  if(e.cancelable) e.preventDefault();
}
function onUp(){
  if(!dragging) return;
  dragging=false; setHeld(false);
  if(pointerId!=null&&deck.releasePointerCapture){ try{deck.releasePointerCapture(pointerId);}catch(_){} }
  if(curDy>=THRESHOLD){ doDraw("pointer"); }
  else{
    setHint("idle");
    if(reduce){ releaseCenter(); return; }
    drawCard.style.transition="transform .5s var(--aq-ease), opacity .3s ease";
    apply(drawCard,base,1);
    setTimeout(function(){ if(!drawing) releaseCenter(); },360);
  }
}

var lastIndex=-1, lastQuoteId="";
function quoteIdAt(idx){
  var q=QUOTES[idx];
  if(!q) return "";
  return q.id || (q.custom ? "custom-"+idx : "quote-"+idx);
}
function shuffledQuoteBag(){
  var indices=[];
  for(var i=0;i<QUOTES.length;i++) indices.push(i);
  for(var j=indices.length-1;j>0;j--){
    var k=Math.floor(random()*(j+1)), tmp=indices[j];
    indices[j]=indices[k]; indices[k]=tmp;
  }
  if(indices.length>1 && quoteIdAt(indices[0])===lastQuoteId){
    for(var n=1;n<indices.length;n++){
      if(quoteIdAt(indices[n])!==lastQuoteId){
        var first=indices[0]; indices[0]=indices[n]; indices[n]=first;
        break;
      }
    }
  }
  return indices;
}
function forcedQuoteIndex(){
  var forcedId=testHook.forceQuoteId || testHook.nextQuoteId || "";
  if(!forcedId) return -1;
  testHook.forceQuoteId="";
  testHook.nextQuoteId="";
  for(var i=0;i<QUOTES.length;i++){
    if(quoteIdAt(i)===forcedId) return i;
  }
  return -1;
}
function pickQuote(){
  if(QUOTES.length===1) return 0;
  var forced=forcedQuoteIndex();
  if(forced>=0){
    quoteBag=quoteBag.filter(function(idx){ return idx!==forced; });
    lastIndex=forced;
    return forced;
  }
  if(!quoteBag.length) quoteBag=shuffledQuoteBag();
  var idx=quoteBag.shift();
  if(quoteBag.length && quoteIdAt(idx)===lastQuoteId){
    var next=quoteBag.shift();
    quoteBag.unshift(idx);
    idx=next;
  }
  lastIndex=idx;
  return idx;
}
function drawTarget(){
  var stageEl=deck.closest(".stage")||deck, stageRect=stageEl.getBoundingClientRect();
  var deckRect=deck.getBoundingClientRect();
  var y=stageRect.height*0.5-(deckRect.top-stageRect.top)-CARD_H/2;
  var scale=clamp((deck.clientWidth-62)/CARD_W,.98,1.48);
  return {x:0,y:y,tilt:-2,scale:scale,z:3500};
}

function doDraw(source){
  if(drawing||dragging||!QUOTES.length) return;
  if(dismissTimer||!quoteCard.hidden) finishDismiss(false);
  if(!holding) grabCard(null,source||"keyboard");
  drawing=true; setHint("idle");
  drawButton.disabled=true;
  var idx=pickQuote();
  if(reduce){
    reveal(idx); releaseCenter(); drawing=false; drawButton.disabled=false; return;
  }
  deck.classList.add("is-background");
  var target=drawTarget();
  var revealed=false;
  function showQuote(){ if(revealed) return; revealed=true; reveal(idx); }
  var done=false;
  function finish(){
    if(done) return; done=true;
    showQuote(); releaseCenter(); drawing=false; drawButton.disabled=false;
  }
  drawCard.style.zIndex="3500";
  drawCard.style.opacity="1";
  drawCard.style.transition="transform .54s cubic-bezier(.22,1,.36,1), opacity .18s ease";
  window.setTimeout(function(){ apply(drawCard,target,1); },0);
  window.setTimeout(function(){
    drawCard.style.transition="transform .3s cubic-bezier(.32,0,.24,1), opacity .18s ease";
    drawCard.style.transform=composeTransform(target," rotateY(88deg)");
    drawCard.style.opacity=".24";
  },520);
  window.setTimeout(function(){
    showQuote();
    drawCard.style.opacity="0";
  },640);
  window.setTimeout(finish,940);
}

var currentQuote={id:"",en:"",ko:"",a:"",theme:"",image:"",imageAvailable:false,source:"",custom:false,drawId:"",idx:-1};
function quoteDisplayText(){ return state.lang==="ko"&&currentQuote.ko ? currentQuote.ko : currentQuote.en; }
function quoteDisplayAuthor(){
  if(currentQuote.custom) return currentQuote.a || t("unknownAuthor");
  return (currentQuote.a && currentQuote.a!=="Original reflection") ? currentQuote.a : t("author");
}
function recordDrawnCard(quote){
  var now=new Date();
  var draw={ id:now.getTime()+"-"+Math.random().toString(36).slice(2,6), ts:now.getTime(),
    dateKey:keyOf(now), time:fmtTime(now), quoteId:quote.id, quoteSource:quote.source,
    quote:quoteDisplayText(), author:quoteDisplayAuthor(), custom:!!quote.custom };
  drawnCards.push(draw);
  drawnCards = normalizeDraws(drawnCards);
  persistState();
  return draw.id;
}
function showQuotePending(){
  var el=document.createElement("span"); el.className="pending";
  el.textContent=currentQuote.custom?"":t("pending");
  quoteMedia.replaceChildren(el);
}
function updateQuoteCardContent(){
  quoteText.textContent=quoteDisplayText();
  quoteAuthor.textContent=quoteDisplayAuthor();
  var old=quoteCard.querySelector(".quote-badge"); if(old) old.remove();
  if(currentQuote.custom){ var b=document.createElement("span"); b.className="quote-badge"; b.textContent=t("yourQuote"); quoteAuthor.appendChild(b); }
  quoteTheme.textContent=currentQuote.custom ? t("yourQuote") : (state.lang==="ko" ? "오늘의 생각" : currentQuote.theme);
  quoteIndex.textContent=t("counter")(currentQuote.idx+1,QUOTES.length);
  quoteMedia.replaceChildren();
  if(currentQuote.imageAvailable&&currentQuote.image){
    var img=new Image(); img.src="images/"+currentQuote.image; img.alt=""; img.decoding="async";
    img.addEventListener("error",function(){ showQuotePending(); });
    quoteMedia.append(img);
  }else showQuotePending();
  var saved=state.saved.indexOf(currentQuote.id)!==-1;
  bookmarkBtn.setAttribute("aria-pressed",String(saved));
  bookmarkBtn.setAttribute("aria-label",t(saved?"unsave":"save"));
}
function reveal(idx){
  var q=QUOTES[idx];
  var drawId = quoteIdAt(idx);
  currentQuote={id:drawId,en:q.t,ko:q.ko||"",a:q.a||"",theme:q.theme||"",image:q.image||"",
    imageAvailable:!!q.imageAvailable,source:q.source||(q.custom?"local":"default"),custom:!!q.custom,drawId:"",idx:idx};
  lastQuoteId=drawId;
  testHook.lastDrawId = drawId;
  testHook.drawCount = (testHook.drawCount || 0) + 1;
  currentQuote.drawId=recordDrawnCard(currentQuote);
  quoteCard.dataset.state = "revealed";
  var text=quoteDisplayText();
  quoteCard.dataset.density = text.length > 220 ? "dense" : text.length > 130 ? "long" : "normal";
  updateQuoteCardContent();
  result.classList.add("is-revealed");
  result.style.transform=""; result.style.opacity="";
  ready.hidden=true; quoteCard.hidden=false; memoCta.hidden=false;
  deck.classList.add("is-background");
  if(deckArea) deckArea.classList.add("is-revealed");
  quoteCard.classList.remove("anim-in"); void quoteCard.offsetWidth; quoteCard.classList.add("anim-in");
  live.textContent=t("newCard")+" "+text+" — "+quoteDisplayAuthor();
}

var dismissTimer=null;
function finishDismiss(focusDeck){
  if(dismissTimer){ clearTimeout(dismissTimer); dismissTimer=null; }
  result.classList.remove("is-revealed","is-dragging");
  result.style.transform=""; result.style.opacity="";
  deck.classList.remove("is-background");
  if(deckArea) deckArea.classList.remove("is-revealed");
  quoteCard.hidden=true; memoCta.hidden=true; ready.hidden=false;
  quoteCard.dataset.state="ready"; quoteCard.classList.remove("anim-in");
  drawButton.disabled=false;
  testHook.dismissCount = (testHook.dismissCount || 0) + 1;
  live.textContent=t("dismissed");
  if(focusDeck) deck.focus();
}

function dismissQuote(focusDeck){
  if(quoteCard.hidden) return;
  result.classList.remove("is-dragging");
  if(reduce){ finishDismiss(focusDeck); return; }
  result.style.transform="translateY(calc(100% + 34px))";
  result.style.opacity="0";
  dismissTimer=window.setTimeout(function(){ dismissTimer=null; finishDismiss(focusDeck); },260);
}

var hintMode="idle";
function setHint(s){
  hintMode=s;
  hint.innerHTML='<span class="dot"></span>'+t(s==="hold"?"hintHold":s==="release"?"hintRelease":"hintIdle");
  hint.classList.toggle("ready",s==="release");
}
function buzz(){ if(navigator.vibrate){ try{navigator.vibrate(8);}catch(_){} } }

if(window.PointerEvent){
  deck.addEventListener("pointerdown",onDown);
  window.addEventListener("pointermove",onMove,{passive:false});
  window.addEventListener("pointerup",onUp);
  window.addEventListener("pointercancel",onUp);
}else{
  deck.addEventListener("touchstart",onDown,{passive:true});
  window.addEventListener("touchmove",onMove,{passive:false});
  window.addEventListener("touchend",onUp);
  deck.addEventListener("mousedown",onDown);
  window.addEventListener("mousemove",onMove);
  window.addEventListener("mouseup",onUp);
}
deck.addEventListener("keydown",function(e){ if(e.key==="Enter"||e.key===" "||e.key==="Spacebar"){ e.preventDefault(); doDraw("keyboard"); } });
drawButton.addEventListener("click",function(){ doDraw("button"); });

var quoteDragging=false, quoteStartY=0, quoteDy=0, quotePointerId=null, quoteStartScroll=0;
function quoteClientY(e){ return e.touches?e.touches[0].clientY:e.clientY; }
function onQuoteDown(e){
  if(quoteCard.hidden || e.target.closest("button,textarea,input,a")) return;
  quoteStartScroll=quoteCard.scrollTop || 0;
  if(quoteStartScroll>0) return;
  quoteDragging=true; quoteDy=0; quoteStartY=quoteClientY(e); quotePointerId=e.pointerId;
  result.classList.add("is-dragging");
  if(e.pointerId!=null&&quoteCard.setPointerCapture){ try{quoteCard.setPointerCapture(e.pointerId);}catch(_){} }
}
function onQuoteMove(e){
  if(!quoteDragging) return;
  if(quoteStartScroll>0){ quoteDragging=false; result.classList.remove("is-dragging"); return; }
  var dy=quoteClientY(e)-quoteStartY;
  if(dy<0) dy=dy*0.18;
  quoteDy=Math.max(0,dy);
  result.style.transform="translateY("+quoteDy+"px)";
  result.style.opacity=String(Math.max(0.35,1-quoteDy/240));
  if(quoteDy>0&&e.cancelable) e.preventDefault();
}
function onQuoteUp(){
  if(!quoteDragging) return;
  quoteDragging=false;
  if(quotePointerId!=null&&quoteCard.releasePointerCapture){ try{quoteCard.releasePointerCapture(quotePointerId);}catch(_){} }
  result.classList.remove("is-dragging");
  if(quoteDy>78){ dismissQuote(false); return; }
  result.style.transform=""; result.style.opacity="";
}
if(window.PointerEvent){
  quoteCard.addEventListener("pointerdown",onQuoteDown);
  window.addEventListener("pointermove",onQuoteMove,{passive:false});
  window.addEventListener("pointerup",onQuoteUp);
  window.addEventListener("pointercancel",onQuoteUp);
}else{
  quoteCard.addEventListener("touchstart",onQuoteDown,{passive:true});
  window.addEventListener("touchmove",onQuoteMove,{passive:false});
  window.addEventListener("touchend",onQuoteUp);
  quoteCard.addEventListener("mousedown",onQuoteDown);
  window.addEventListener("mousemove",onQuoteMove);
  window.addEventListener("mouseup",onQuoteUp);
}
quoteDismiss.addEventListener("click",function(){ dismissQuote(true); });

/* ===================== generic sheet controller ===================== */
function focusables(root){ return Array.prototype.filter.call(root.querySelectorAll('button,textarea,input,[tabindex]'),function(x){return !x.disabled && x.offsetParent!==null;}); }
function openSheet(root,focusEl){
  Array.prototype.forEach.call(document.querySelectorAll(".sheet-root.open"),function(o){
    if(o!==root){ o.classList.remove("open"); o.hidden=true; if(o._key) document.removeEventListener("keydown",o._key); }
  });
  root._last=document.activeElement;
  root.hidden=false; void root.offsetWidth; root.classList.add("open");
  setTimeout(function(){ var f=focusEl&&!focusEl.hidden?focusEl:focusables(root)[0]; if(f) f.focus(); }, reduce?0:170);
  root._key=function(e){
    if(e.key==="Escape"){ closeSheet(root); }
    else if(e.key==="Tab"){ var f=focusables(root); if(!f.length)return; var a=f[0],b=f[f.length-1];
      if(e.shiftKey&&document.activeElement===a){e.preventDefault();b.focus();}
      else if(!e.shiftKey&&document.activeElement===b){e.preventDefault();a.focus();} }
  };
  document.addEventListener("keydown",root._key);
}
function closeSheet(root){
  root.classList.remove("open");
  document.removeEventListener("keydown",root._key);
  var fin=function(){ root.hidden=true; if(root._last&&root._last.focus) root._last.focus(); };
  if(reduce) fin(); else setTimeout(fin,420);
}
Array.prototype.forEach.call(document.querySelectorAll(".backdrop[data-close]"),function(bd){
  bd.addEventListener("click",function(){ closeSheet(bd.closest(".sheet-root")); });
});

/* ===================== add a quote ===================== */
var addRoot=$("addRoot");
var qText=$("qText"), qAuthor=$("qAuthor");
var addField=$("addField"), textCount=$("textCount");
$("openAddTop").addEventListener("click",function(){
  qText.value=""; qAuthor.value=""; textCount.textContent="0/120"; addField.classList.remove("error","shake");
  openSheet(addRoot,qText);
});
$("addCancel").addEventListener("click",function(){ closeSheet(addRoot); });
qText.addEventListener("input",function(){ textCount.textContent=qText.value.length+"/120"; if(qText.value.trim()) addField.classList.remove("error"); });
$("addSave").addEventListener("click",function(){
  var t2=qText.value.trim();
  if(!t2){ addField.classList.add("error"); addField.classList.remove("shake"); void addField.offsetWidth; addField.classList.add("shake"); qText.focus(); return; }
  var a=qAuthor.value.trim();
  var customId="custom-"+Date.now()+"-"+Math.random().toString(36).slice(2,6);
  QUOTES.push({id:customId,t:t2,a:a,custom:true,source:"local"});
  quoteBag=[];
  customQuotes.push({id:customId,t:t2,a:a});
  customQuotes = normalizeQuotes(customQuotes);
  persistState(function(ok){
    if(!ok){
      customQuotes=customQuotes.filter(function(quote){ return quote.id !== customId; });
      QUOTES=QUOTES.filter(function(quote){ return quote.id !== customId; });
      quoteBag=[]; updateStorageHook();
      showToast(t("saveFail"));
      return;
    }
    closeSheet(addRoot);
    showToast(t("quoteAdded"));
    live.textContent=t("addedCount")(QUOTES.length);
    testHook.customQuoteCount = customQuotes.length;
    testHook.totalQuoteCount = QUOTES.length;
  });
});

/* ===================== your thought memo ===================== */
var memoRoot=$("memoRoot");
var memoText=$("memoText"), memoField=$("memoField"), memoCount=$("memoCount");
var memoWhen=$("memoWhen");
$("memoBtn").addEventListener("click",function(){
  if(!currentQuote.en) return;
  var now=new Date();
  memoWhen.textContent=fmtFull(now)+" · "+fmtTime(now);
  $("memoQuoteText").textContent="“"+quoteDisplayText()+"”";
  $("memoQuoteAuthor").textContent=quoteDisplayAuthor();
  memoText.value=""; memoCount.textContent="0/300"; memoField.classList.remove("error","shake");
  openSheet(memoRoot,memoText);
});
$("memoCancel").addEventListener("click",function(){ closeSheet(memoRoot); });
memoText.addEventListener("input",function(){ memoCount.textContent=memoText.value.length+"/300"; if(memoText.value.trim()) memoField.classList.remove("error"); });
$("memoSave").addEventListener("click",function(){
  var th=memoText.value.trim();
  if(!th){ memoField.classList.add("error"); memoField.classList.remove("shake"); void memoField.offsetWidth; memoField.classList.add("shake"); memoText.focus(); return; }
  var now=new Date();
  var memo={ id:now.getTime()+"-"+Math.random().toString(36).slice(2,6), ts:now.getTime(),
    dateKey:keyOf(now), time:fmtTime(now), quoteId:currentQuote.id, quoteSource:currentQuote.source,
    quote:quoteDisplayText(), author:quoteDisplayAuthor(), thought:th, drawId:currentQuote.drawId||"", imported:false };
  memos.push(memo);
  memos = normalizeMemos(memos);
  persistState(function(ok){
    if(!ok){
      memos=memos.filter(function(item){ return item.id !== memo.id; });
      updateStorageHook();
      showToast(t("saveFail"));
      return;
    }
    closeSheet(memoRoot);
    showToast(t("memoSaved"));
    live.textContent=t("memoSaved");
  });
});

/* ===================== card history calendar ===================== */
var calRoot=$("calRoot");
var calMonthView=$("calMonthView"), calDayView=$("calDayView");
var calGrid=$("calGrid"), calMonthLabel=$("calMonthLabel"), calEmpty=$("calEmpty"), calWeek=$("calWeek");
var viewY, viewM;

function eventsByKey(){
  var m={};
  function slot(k){ return m[k]||(m[k]={draws:[],memos:[]}); }
  drawnCards.forEach(function(d){ slot(d.dateKey).draws.push(d); });
  memos.forEach(function(x){ slot(x.dateKey).memos.push(x); });
  return m;
}
function renderCalWeek(){
  calWeek.innerHTML=WD[state.lang].map(function(w,i){ return "<span"+(i===0?' class="sun"':"")+">"+w+"</span>"; }).join("");
}
function renderCalendar(){
  calMonthView.hidden=false; calDayView.hidden=true;
  calMonthLabel.textContent=state.lang==="ko" ? viewY+"년 "+(viewM+1)+"월" : MON_EN[viewM]+" "+viewY;
  var first=new Date(viewY,viewM,1), startDow=first.getDay(), days=new Date(viewY,viewM+1,0).getDate();
  var today=new Date(), tkey=keyOf(today);
  var byKey=eventsByKey(), monthHas=0;
  var html="";
  for(var b=0;b<startDow;b++) html+='<div class="cal-cell empty"></div>';
  for(var d=1;d<=days;d++){
    var k=viewY+"-"+pad(viewM+1)+"-"+pad(d);
    var slot=byKey[k], cnt=slot?slot.draws.length+slot.memos.length:0; if(cnt) monthHas++;
    var cls="cal-cell"+(cnt?" has":"")+(k===tkey?" today":"");
    var dots="";
    if(cnt){ var n=Math.min(cnt,4); for(var j=0;j<n;j++) dots+="<i></i>"; }
    html+='<button class="'+cls+'" type="button" '+(cnt?'data-k="'+k+'" aria-label="'+t("cellLabel")(monthName(viewM),d,cnt)+'"':'tabindex="-1" aria-hidden="true"')+'>'+
          '<span class="cal-num">'+d+'</span><span class="cal-dots">'+dots+'</span></button>';
  }
  calGrid.innerHTML=html;
  calEmpty.hidden = monthHas>0;
}
function esc(s){ return String(s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c];}); }
function openDay(k){
  var slot=eventsByKey()[k]||{draws:[],memos:[]};
  var parts=k.split("-"), d=new Date(+parts[0],+parts[1]-1,+parts[2]);
  $("calDayTitle").textContent=fmtFull(d);
  var byDraw={};
  slot.memos.forEach(function(m){ var key=m.drawId||""; (byDraw[key]=byDraw[key]||[]).push(m); });
  var linked={}, html="";
  slot.draws.slice().sort(function(a,b){return a.ts-b.ts;}).forEach(function(dr){
    linked[dr.id]=true;
    html+='<div class="entry"><p class="e-time">'+esc(dr.time)+'</p>'+
          '<p class="e-quote">“'+esc(dr.quote)+'”</p>'+
          '<p class="e-author">'+esc(dr.author||t("unknownAuthor"))+(dr.custom?' · '+esc(t("yourQuote")):'')+'</p>'+
          (byDraw[dr.id]||[]).map(function(m){ return '<p class="e-thought">'+esc(m.thought)+'</p>'; }).join("")+
          '</div>';
  });
  slot.memos.filter(function(m){ return !m.drawId || !linked[m.drawId]; }).sort(function(a,b){return a.ts-b.ts;}).forEach(function(m){
    html+='<div class="entry">'+(m.imported?'<p class="e-badge">'+esc(t("importedNote"))+'</p>':'')+
          '<p class="e-time">'+(m.imported?esc(m.time?t("importedAt")(m.time):t("importedNote")):esc(m.time))+'</p>'+
          (m.quote?'<p class="e-quote">“'+esc(m.quote)+'”</p><p class="e-author">'+esc(m.author||t("unknownAuthor"))+'</p>':'')+
          '<p class="e-thought">'+esc(m.thought)+'</p></div>';
  });
  $("dayList").innerHTML=html;
  calMonthView.hidden=true; calDayView.hidden=false;
  calDayView.querySelector(".cal-back").focus();
}

$("openCal").addEventListener("click",function(){
  var t2=new Date(); viewY=t2.getFullYear(); viewM=t2.getMonth();
  renderCalendar(); openSheet(calRoot);
});
$("calPrev").addEventListener("click",function(){ viewM--; if(viewM<0){viewM=11;viewY--;} renderCalendar(); });
$("calNext").addEventListener("click",function(){ viewM++; if(viewM>11){viewM=0;viewY++;} renderCalendar(); });
$("calBack").addEventListener("click",renderCalendar);
calGrid.addEventListener("click",function(e){ var c=e.target.closest(".cal-cell.has"); if(c&&c.getAttribute("data-k")) openDay(c.getAttribute("data-k")); });

/* ===================== toast ===================== */
var toast=$("toast"), toastMsg=$("toastMsg"), toastTimer=null;
function showToast(msg){ toastMsg.textContent=msg; toast.classList.add("show"); clearTimeout(toastTimer); toastTimer=setTimeout(function(){ toast.classList.remove("show"); },2600); }

/* ===================== render / language ===================== */
function render(){
  document.documentElement.lang = state.lang;
  $("language").value = state.lang;
  document.querySelectorAll("[data-i18n]").forEach(function(el){ el.innerHTML = t(el.dataset.i18n); });
  deck.setAttribute("aria-label",t("deckLabel"));
  quoteDismiss.setAttribute("aria-label",t("dismiss"));
  $("openCal").setAttribute("aria-label",t("calTitle"));
  $("openAddTop").setAttribute("aria-label",t("addQuote"));
  $("calPrev").setAttribute("aria-label",t("prevMonth"));
  $("calNext").setAttribute("aria-label",t("nextMonth"));
  shareBtn.setAttribute("aria-label",t("share"));
  memoText.placeholder=t("memoPlaceholder");
  qText.placeholder=t("qTextPlaceholder");
  qAuthor.placeholder=t("qAuthorPlaceholder");
  renderCalWeek();
  setHint(hintMode);
  if(!quoteCard.hidden&&currentQuote.en) updateQuoteCardContent();
}
$("language").addEventListener("change",function(e){
  state.lang = e.target.value === "ko" ? "ko" : "en";
  persistPrefs(); render(); status(navigator.onLine ? t("ready") : t("offline"));
});
bookmarkBtn.addEventListener("click",function(){
  if(!currentQuote.id) return;
  var saved=state.saved.indexOf(currentQuote.id)!==-1;
  state.saved=saved?state.saved.filter(function(id){return id!==currentQuote.id;}):state.saved.concat([currentQuote.id]);
  var ok=persistPrefs(); updateQuoteCardContent();
  status(ok?t(saved?"removed":"savedCard"):t("storageFail"));
});
shareBtn.addEventListener("click",async function(){
  var text=quoteText.textContent+"\n— "+quoteAuthor.textContent;
  try {
    if(navigator.share) await navigator.share({title:"Daily Quote Card",text:text,url:location.href});
    else if(navigator.clipboard){ await navigator.clipboard.writeText(text); status(t("copied")); }
    else status(t("shareFail"));
  } catch(e){ if(e.name!=="AbortError") status(t("shareFail")); }
});

/* ===================== pwa: install / notify ===================== */
let installEvent;
window.addEventListener("beforeinstallprompt",function(e){ e.preventDefault(); installEvent=e; });
$("install").addEventListener("click",async function(){
  if(window.matchMedia("(display-mode: standalone)").matches || navigator.standalone){ status(t("installed")); return; }
  if(installEvent){ await installEvent.prompt(); await installEvent.userChoice; installEvent=null; }
  else $("install-help").showModal();
});
const swReady = "serviceWorker" in navigator && window.isSecureContext
  ? Promise.race([navigator.serviceWorker.register("./sw.js").then(function(){return navigator.serviceWorker.ready;}),new Promise(function(r){setTimeout(function(){r(null);},8000);})]).catch(function(){return null;})
  : Promise.resolve(null);
$("notify").addEventListener("click",async function(){
  if(!("Notification" in window)||!("serviceWorker" in navigator)||!window.isSecureContext){ status(t("notifyUnsupported")); return; }
  try {
    const permission=await Notification.requestPermission();
    if(permission!=="granted"){ status(t("denied")); return; }
    const reg=await swReady; if(!reg){ status(t("notifyFail")); return; }
    var q=null;
    for(var i=0;i<BASE_QUOTES.length;i++){ if(BASE_QUOTES[i].id===currentQuote.id){ q=BASE_QUOTES[i]; break; } }
    if(!q) q=BASE_QUOTES[0]||{t:"",ko:""};
    await reg.showNotification("Daily Quote Card",{body:state.lang==="ko"?(q.ko||q.t):q.t,icon:"icons/icon-192.png",badge:"icons/icon-192.png",tag:"daily-quote-card-test",data:{url:location.href}});
    status(t("notifySent"));
  }catch(e){ status(t("notifyFail")); }
});
window.addEventListener("offline",function(){ status(t("offline")); });
window.addEventListener("online",function(){ status(t("ready")); });

/* ===================== deck load + init ===================== */
try {
  const response=await fetch("./deck.json");
  if(!response.ok) throw new Error("deck");
  const data=await response.json();
  BASE_QUOTES=(Array.isArray(data.quotes)?data.quotes:[]).filter(function(q){
    return q&&/^q\d\d$/.test(q.id)&&typeof q.text==="string";
  }).map(function(q){
    return { id:q.id, t:q.text, ko:typeof q.ko==="string"?q.ko:"", a:typeof q.author==="string"?q.author:"",
      theme:typeof q.theme==="string"?q.theme:"", image:typeof q.image==="string"?q.image:"",
      imageAvailable:!!q.imageAvailable, source:"default" };
  });
  if(!BASE_QUOTES.length) throw new Error("empty");
}catch(e){ deckLoadFailed=true; }
beltImages=BASE_QUOTES.filter(function(q){ return q.imageAvailable&&q.image; }).map(function(q){ return q.image; });
migrateLegacyNotes();
rebuildQuotes(false);
updateStorageHook();
measure(); buildDeck();
window.addEventListener("resize",measure);
render();
setHint("idle");
tick(); setInterval(tick,1000/60);
if(deckLoadFailed){
  drawButton.disabled=true;
  deck.setAttribute("aria-disabled","true");
  status(t("loadingFail"));
}else{
  status(storageAvailable?(navigator.onLine?t("ready"):t("offline")):t("storageFail"));
}
