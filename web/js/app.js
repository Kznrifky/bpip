'use strict';
const $ = (selector, root = document) => root.querySelector(selector);
const app = $('#app');
const dialog = $('#dialog');
const state = {user:null, csrf:'', config:{}, documents:[], archivedCount:0, customerArchivedCount:0, customerSearch:'', customerSelected:[], customerDeleteMode:false, customerEditMode:false, documentSelected:[], documentDeleteMode:false, historySearch:'', historyResult:'all', customers:[], customerUpdates:[], customerUpdateFilter:'all', route:'dashboard', page:1, search:'', dateFrom:'', dateTo:'', status:'all', kind:'all', detail:null, messages:[], mailId:null};
const paths = {
 trash:'<path d="M3 6h18M9 6V4h6v2M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
 phone:'<path d="M20 15.5v3a2 2 0 0 1-2.2 2A17 17 0 0 1 3.5 6.2 2 2 0 0 1 5.5 4h3a1 1 0 0 1 1 .8l.6 2.8a1 1 0 0 1-.3 1l-1.5 1.5a13 13 0 0 0 5.6 5.6l1.5-1.5a1 1 0 0 1 1-.3l2.8.6a1 1 0 0 1 .8 1z"/>',
 identity:'<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="8" cy="10" r="2"/><path d="M5 16a3 3 0 0 1 6 0M14 9h4M14 13h4M14 16h3"/>',
 briefcase:'<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12a21 21 0 0 0 18 0M10 12v3h4v-3"/>',
 person:'<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
 attachment:'<path d="m8 13 7-7a3 3 0 0 1 4 4L9 20a5 5 0 0 1-7-7L13 2a2 2 0 0 1 3 3L6 15a1 1 0 0 0 2 2l8-8"/>',
 payment:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18M7 15h4"/>',
 grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
 file:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
 shield:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z"/><path d="m8 12 3 3 5-6"/>',
 clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 check:'<path d="m5 12 4 4L19 6"/>',
 close:'<path d="m6 6 12 12M6 18 18 6"/>',
 plus:'<path d="M12 5v14M5 12h14"/>',
 arrow:'<path d="M5 12h14m-5-5 5 5-5 5"/>',
 left:'<path d="M19 12H5m5-5-5 5 5 5"/>',
 chevron:'<path d="m9 5 7 7-7 7"/>',
 search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/>',
 mail:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 6 9 7 9-7"/>',
 people:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M22 21v-2a4 4 0 0 0-3-3.87"/><circle cx="9" cy="7" r="4"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
 settings:'<path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/><circle cx="12" cy="12" r="5"/>',
 logout:'<path d="M9 4H4v16h5M9 12h12m-4-4 4 4-4 4"/>',
 edit:'<path d="m15 4 5 5M4 20l5-1L21 7a2.8 2.8 0 0 0-4-4L5 15z"/>',
 upload:'<path d="M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5"/>',
 lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
 refresh:'<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 7a7 7 0 0 1 12-2l2 3M4 16l2 3a7 7 0 0 0 12-2"/>',
 info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
 menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
 download:'<path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4"/>',
 calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18"/>',
 eyeOff:'<path d="m3 3 18 18M10.6 5.1A12 12 0 0 1 12 5c6 0 10 7 10 7a18 18 0 0 1-3.1 3.7M6.1 6.1A18 18 0 0 0 2 12s4 7 10 7a12 12 0 0 0 5.9-1.9M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
 approval:'<rect x="4" y="3" width="16" height="18" rx="3"/><path d="m8 12 3 3 5-6"/>',
 eye:'<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
 chat:'<path d="M21 11.5a8.4 8.4 0 0 1-9 8.5 9 9 0 0 1-4-.9L3 21l1.8-4.9A9 9 0 1 1 21 11.5z"/><path d="M9 7.5c-1 0-1.5 1-1.5 2 0 2.5 3.5 6 6 6 1 0 2-.5 2-1.5l-2-1-1 1c-1.5-.5-3-2-3.5-3.5l1-1z"/>',
 copy:'<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h3"/>'
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.file}</svg>`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Capitalize entered names without lowercasing acronyms or changing the caret.
const capitalizeName = value => value.replace(/(^|[\s'’\-])(\p{L})/gu, (_, prefix, letter) => prefix + letter.toLocaleUpperCase('id-ID'));
function capitalizeNameField(event) {
 const input=event.target;
 if(!input.matches?.('input[data-capitalize="words"]')||input.readOnly||event.isComposing)return;
 const value=input.value,formatted=capitalizeName(value);
 if(value===formatted)return;
 const start=input.selectionStart,end=input.selectionEnd,direction=input.selectionDirection;
 input.value=formatted;
 if(start!==null&&end!==null)input.setSelectionRange(capitalizeName(value.slice(0,start)).length,capitalizeName(value.slice(0,end)).length,direction);
}
for(const event of ['input','change','compositionend'])document.addEventListener(event,capitalizeNameField);
const rupiah = n => new Intl.NumberFormat('id-ID',{style:'currency',currency:'IDR',maximumFractionDigits:0}).format(n);
const date = value => new Intl.DateTimeFormat('id-ID',{dateStyle:'medium',timeStyle:'short',timeZone:'Asia/Jakarta'}).format(new Date(value));
const submissionDate = value => new Intl.DateTimeFormat('en-CA',{year:'numeric',month:'2-digit',day:'2-digit',timeZone:'Asia/Jakarta'}).format(new Date(value));
function matchesSubmissionDate(d) {const day=submissionDate(d.created);return (!state.dateFrom||day>=state.dateFrom)&&(!state.dateTo||day<=state.dateTo);}
const rangeDay = day => new Date(day+'T12:00:00');
const rangeDateLabel = day => new Intl.DateTimeFormat('id-ID',{day:'numeric',month:'short',year:'numeric'}).format(rangeDay(day));
const rangeButtonLabel = () => state.dateFrom&&state.dateTo ? `${rangeDateLabel(state.dateFrom)} – ${rangeDateLabel(state.dateTo)}` : 'Filter tanggal';
function positionDateRange() {
 const picker=$('#date-picker'),trigger=$('#date-range-trigger'),panel=$('#date-range-panel');
 if(!picker?.open||!trigger||!panel)return;
 if(window.matchMedia('(max-width: 760px)').matches){panel.style.removeProperty('left');panel.style.removeProperty('top');return;}
 const rect=trigger.getBoundingClientRect(),width=panel.offsetWidth,height=panel.offsetHeight,margin=12,gap=8;
 const left=Math.max(margin,Math.min(rect.right-width,window.innerWidth-width-margin));
 const below=rect.bottom+gap;
 const top=below+height<=window.innerHeight-margin?below:Math.max(margin,rect.top-height-gap);
 panel.style.left=left+'px';panel.style.top=top+'px';
}
window.addEventListener('resize',positionDateRange);
window.addEventListener('scroll',positionDateRange,true);
function bindDateRange() {
 const picker=$('#date-picker'),trigger=$('#date-range-trigger'),panel=$('#date-range-panel');
 let from=state.dateFrom,to=state.dateTo,month=rangeDay(from||submissionDate(new Date()));month.setDate(1);
 const dayKey=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
 const close=()=>{picker.open=false;trigger.focus();};
 const apply=(start,end)=>{state.dateFrom=start;state.dateTo=end;state.page=1;trigger.innerHTML=icon('calendar')+`<span>${esc(rangeButtonLabel())}</span>`;trigger.title=rangeButtonLabel();trigger.classList.toggle('active',!!start);close();renderTable();};
 const draw=()=>{
  const offset=(month.getDay()+6)%7,days=new Date(month.getFullYear(),month.getMonth()+1,0).getDate();
  panel.innerHTML=`<div class="range-month"><button type="button" class="btn icon small" data-month="-1" aria-label="Bulan sebelumnya">${icon('left')}</button><strong>${esc(new Intl.DateTimeFormat('id-ID',{month:'long',year:'numeric'}).format(month))}</strong><button type="button" class="btn icon small" data-month="1" aria-label="Bulan berikutnya">${icon('arrow')}</button></div><div class="range-calendar">${['Sen','Sel','Rab','Kam','Jum','Sab','Min'].map(x=>`<span class="range-weekday">${x}</span>`).join('')}${'<span></span>'.repeat(offset)}${Array.from({length:days},(_,i)=>{const key=dayKey(new Date(month.getFullYear(),month.getMonth(),i+1)),edge=key===from||key===to,inside=from&&to&&key>from&&key<to;return `<button type="button" class="range-day ${edge?'selected':inside?'in-range':''}" data-day="${key}" aria-label="${esc(rangeDateLabel(key))}" aria-pressed="${edge?'true':'false'}">${i+1}</button>`;}).join('')}</div><p class="range-hint" aria-live="polite">${from&&to?esc(`${rangeDateLabel(from)} – ${rangeDateLabel(to)}`):from?'Pilih tanggal akhir.':'Pilih tanggal awal, lalu tanggal akhir.'}</p><div class="range-footer"><button type="button" class="btn text small" data-range-reset ${from||to||state.dateFrom||state.dateTo?'':'disabled'}>Reset</button><button type="button" class="btn small" data-range-close>Batal</button><button type="button" class="btn primary small" data-range-apply ${from&&to?'':'disabled'}>Terapkan</button></div>`;
  positionDateRange();
 };
 picker.addEventListener('toggle',()=>{if(picker.open){const today=submissionDate(new Date());from=state.dateFrom||today;to=state.dateTo||(state.dateFrom?'':today);month=rangeDay(from);month.setDate(1);draw();}});
 panel.addEventListener('click',e=>{
  e.stopPropagation();
  const button=e.target.closest('button');if(!button)return;
  if(button.dataset.day){const key=button.dataset.day;if(!from||to){from=key;to='';}else{to=key;if(to<from)[from,to]=[to,from];}draw();panel.querySelector(`[data-day="${key}"]`)?.focus();}
  else if(button.dataset.month){month.setMonth(month.getMonth()+Number(button.dataset.month));draw();panel.querySelector(`[data-month="${button.dataset.month}"]`).focus();}
  else if(button.hasAttribute('data-range-reset'))apply('','');
  else if(button.hasAttribute('data-range-apply'))apply(from,to);
  else if(button.hasAttribute('data-range-close'))close();
 });
 picker.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();close();}});
}
// Close an open calendar when clicking elsewhere without changing the filter.
function setMenuOpen(open,focus=false) {
 $('#sidebar')?.classList.toggle('open',open);
 $('.mobile-toggle')?.setAttribute('aria-expanded',String(open));
 if($('.workspace'))$('.workspace').inert=open;
 if(focus)$(open?'.mobile-close':'.mobile-toggle')?.focus();
}
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&$('#sidebar')?.classList.contains('open'))setMenuOpen(false,true);});
window.matchMedia('(max-width: 760px)').addEventListener('change',e=>{if(!e.matches)setMenuOpen(false);});
document.addEventListener('click',e=>{const picker=$('#date-picker');if(picker?.open&&!picker.contains(e.target))picker.open=false;});
const labels = {pending:'Menunggu nasabah',confirmed:'Disetujui nasabah',rejected:'Ditolak nasabah'};
const solLabels = {pending:'Menunggu Verifikasi',approved:'Disetujui AMOL',rejected:'Ditolak AMOL',revision_requested:'Menunggu Verifikasi',cancelled:'Ditolak',whatsapp_manual:'Tidak dipilih'};
const colors = {checker:'amber',review:'amber',pending:'amber',confirmed:'green',rejected:'red',approved:'green',revision_requested:'amber'};
const mailLabels = {queued:'Menunggu pengiriman',sending:'Sedang dikirim',sent:'Diserahkan ke layanan email',local:'Email lokal',retry:'Pengiriman akan dicoba ulang',failed:'Pengiriman gagal',cancelled:'Dibatalkan',whatsapp_manual:'Tidak dipilih'};
const badge = (value, text) => `<span class="badge ${colors[value] || 'grey'}">${esc(text)}</span>`;
function needsChecker(d) {return d.review_flow>=2;}
function finalStatus(d) {if(needsChecker(d)&&d.checker_status==='rejected')return 'rejected';if(needsChecker(d)&&d.customer_status==='confirmed'&&d.checker_status==='pending'&&['pending','revision_requested'].includes(d.sol_status))return 'checker';if(d.customer_status==='rejected')return 'rejected';return ['pending','revision_requested'].includes(d.sol_status) ? (d.customer_status === 'pending' ? 'pending' : 'review') : d.sol_status;}
function activeDocuments(docs=state.documents) {return docs.filter(d=>!historyOutcome(d));}
function statusBadge(d) {if(d.sol_status==='pending'&&d.customer_status==='rejected')return badge('rejected',labels.rejected);const status = finalStatus(d); return badge(status, status === 'checker' ? 'Menunggu Review SOL' : status === 'review' ? 'Menunggu Review AMOL' : status === 'pending' ? 'Menunggu nasabah' : solLabels[status]);}
function toast(message, error=false) {const t = $('#toast');t.textContent=message;t.className='visible'+(error?' error':'');clearTimeout(toast.timer);toast.timer=setTimeout(()=>{t.className='';},4500);}
async function api(url, data, raw=false) {
 const options={headers:{}};
 if(data!==undefined){options.method='POST';options.headers['Content-Type']='application/json';options.headers['X-CSRF-Token']=state.csrf;options.body=JSON.stringify(data);}
 let res;
 try {res=await fetch('/api'+url,options);} catch {throw new Error('Server tidak dapat dihubungi. Periksa koneksi Anda.');}
 if(!res.ok){const result=await res.json().catch(()=>({}));const error=new Error(result.error||'Permintaan gagal.');error.status=res.status;throw error;}
 return raw?res.blob():res.json();
}
const brand = () => `<div class="brand"><div class="brand-logo"><img src="/assets/bri-vista-logo-transparent.png" width="2172" height="724" alt="BRI VISTA" fetchpriority="high"></div><small>Verification, Integration &amp; Secure Tracking Application</small></div>`;
const sidebarBrand = () => `<div class="brand sidebar-brand"><div class="sidebar-logo"><img src="/assets/bri-vista-login-logo.png" width="2120" height="742" alt="BRI VISTA" fetchpriority="high"></div></div>`;
const notice = (message, variant='') => `<div class="notice ${variant}">${icon(variant==='error'?'info':'shield')}<div>${message}</div></div>`;
const empty = (title, subtitle, action='') => `<div class="empty">${icon('file')}<h3>${esc(title)}</h3><p>${esc(subtitle)}</p>${action}</div>`;
const head = (eyebrow,title,subtitle,action='') => `<div class="page-heading spread"><h1>${title}</h1>${action}</div>`;
function go(route) {if(location.hash==='#'+route) renderRoute();else location.hash=route;}
function errorBlock(err) {return notice(esc(err.message),'error');}
function routeNow() {return location.hash.slice(1)||'dashboard';}
async function boot() {
 try {state.config=await api('/config');}catch(err){app.innerHTML=`<div class="loading-screen">${brand()}${errorBlock(err)}<button class="btn" data-action="reload">Coba lagi</button></div>`;return;}
 if(routeNow().startsWith('confirm/')) return renderPortal();
 try {const session=await api('/session');state.user=session.user;state.csrf=session.csrf;await loadWorkspace();}catch(err){if(err.status===401)renderLogin();else app.innerHTML=`<div class="loading-screen">${brand()}${errorBlock(err)}<button class="btn" data-action="reload">Coba lagi</button></div>`;}
}
function renderLogin() {
 state.user=null;state.csrf='';state.documentSelected=[];state.documentDeleteMode=false;state.customerSelected=[];state.customerDeleteMode=false;state.customerEditMode=false;
 app.innerHTML=`<div class="login-layout"><section class="login-story login-branded"><div class="login-branding"><div class="login-logo"><img src="/assets/bri-vista-login-logo.png" width="2120" height="742" alt="BRI VISTA — Verification, Integration &amp; Secure Tracking Application" fetchpriority="high"></div></div><div class="story-content"><h1>Verifikasi dan Konfirmasi<br>Dokumen Operasional</h1><p>Pengembangan Prototype BRI VISTA sebagai sistem terintegrasi untuk memperkuat pengendalian transaksi.</p><ol class="story-flow story-flow-checker" aria-label="Alur pengajuan"><li class="story-step"><div class="step-mark">${icon('file')}<span class="step-number">1</span></div><span class="step-label">Pengajuan<br>Surat</span></li><li class="story-step"><div class="step-mark">${icon('people')}<span class="step-number">2</span></div><span class="step-label">Review<br>Nasabah</span></li><li class="story-step"><div class="step-mark">${icon('shield')}<span class="step-number">3</span></div><span class="step-label">Review<br>SOL</span></li><li class="story-step"><div class="step-mark">${icon('approval')}<span class="step-number">4</span></div><span class="step-label">Approval<br>AMOL</span></li></ol></div></section><section class="login-panel"><form id="login-form" class="login-form"><div class="field"><label for="login-email">Alamat email</label><div class="login-input">${icon('mail')}<input id="login-email" name="email" type="email" autocomplete="username" placeholder="nama@perusahaan.co.id" required></div></div><div class="field"><label for="login-password">Kata sandi</label><div class="login-input">${icon('lock')}<input id="login-password" name="password" type="password" autocomplete="current-password" placeholder="Masukkan kata sandi" required><button id="login-password-toggle" class="login-password-toggle" type="button" aria-label="Tampilkan kata sandi" aria-pressed="false">${icon('eyeOff')}</button></div></div><div id="login-error" class="error-message" role="alert"></div><button class="btn primary full" type="submit">Login</button>${state.config.demo?`<div class="demo-box"><strong>Akun demo · pengujian lokal</strong><div class="demo-account"><span>Petugas<br><code>PetugasDemo!2026</code></span><button type="button" class="btn small" data-action="demo" data-role="petugas">Gunakan akun</button></div><div class="demo-account"><span>AMOL<br><code>SolDemo!2026</code></span><button type="button" class="btn small" data-action="demo" data-role="sol">Gunakan akun</button></div><small>Email tersimpan di kotak email lokal, belum dikirim ke nasabah.</small></div>`:''}</form></section></div>`;
 $('#login-password-toggle').addEventListener('click',e=>{const input=$('#login-password'),button=e.currentTarget,visible=input.type==='password';input.type=visible?'text':'password';button.setAttribute('aria-pressed',String(visible));button.setAttribute('aria-label',visible?'Sembunyikan kata sandi':'Tampilkan kata sandi');button.innerHTML=icon(visible?'eye':'eyeOff');});
 $('#login-form').addEventListener('submit',async e=>{e.preventDefault();const button=$('button[type=submit]',e.target);button.disabled=true;$('#login-error').textContent='';try{const result=await api('/login',Object.fromEntries(new FormData(e.target)));state.user=result.user;state.csrf=result.csrf;await loadWorkspace();}catch(err){$('#login-error').textContent=err.message;button.disabled=false;}});
}
function profileDisplayName(user) {return user.role==='sol'&&user.name.trim().toUpperCase()==='SOL'?'AMOL':user.name;}
async function refreshData() {
 const role=state.user.role;
 const [docs,customers,updates,session]=await Promise.all([api('/documents'),role==='boh'?Promise.resolve({customers:[]}):api('/customers'),['sol','checker'].includes(role)?api('/customer-edit-requests'):Promise.resolve({requests:[]}),api('/session')]);
 state.documents=docs.documents;state.archivedCount=docs.archived_count||0;state.customers=customers.customers;state.customerArchivedCount=customers.archived_count||0;state.customerUpdates=updates.requests;state.user=session.user;state.csrf=session.csrf;
 const profile=$('#profile-name');if(profile)profile.textContent=profileDisplayName(state.user);updateNavCount();
}
function updateNavCount() {
 for(const [route,count] of [['documents',state.user.role==='sol'?kpiDocuments('review').length:0],['customer-updates',state.customerUpdates.filter(r=>r.status==='pending').length]]){
  const nav=$('.nav [data-route="'+route+'"]');if(!nav)continue;$('.count',nav)?.remove();if(count){const el=document.createElement('span');el.className='count';el.textContent=count;nav.append(el);}
 }
}
async function loadWorkspace() {await refreshData();renderShell();await renderRoute();}
function renderShell() {
 const user=state.user;const isSOL=user.role==='sol',isBOH=user.role==='boh',isChecker=user.role==='checker';
 const roleLabel=isChecker?'SOL':isBOH?'BOH':isSOL?'AMOL':'Officer';
 const nav=(route,label,ico,count='')=>`<button type="button" data-route="${route}">${icon(ico)}${label}${count?`<span class="count">${count}</span>`:''}</button>`;
 app.innerHTML=`<div class="shell nusantara-theme"><aside class="sidebar" id="sidebar">${sidebarBrand()}<button class="btn text icon mobile-close" data-action="menu" aria-label="Tutup navigasi">${icon('close')}</button><div class="nav-label">Menu</div><nav class="nav" aria-label="Navigasi utama">${nav('dashboard','Dashboard','grid')}${isBOH?'':isChecker?nav('customers','Data Nasabah','people'):isSOL?nav('customers','Data Nasabah','people'):nav('initiate','Pengajuan','plus')}${isSOL||isChecker?nav('customer-updates','Update Data','people',state.customerUpdates.filter(r=>r.status==='pending').length||''):''}${nav('history','History','clock')}${!isBOH&&!isChecker&&state.config.mail_mode==='console'?nav('emails','Kotak email lokal','mail'):''}${!isBOH?nav('settings','Pengaturan','settings'):''}</nav><div class="sidebar-bottom"><div class="profile"><div class="avatar">${roleLabel[0]}</div><div><strong id="profile-name">${esc(profileDisplayName(user))}</strong><small>${roleLabel}</small></div><button class="btn text icon" data-action="logout" title="Keluar dari akun" aria-label="Keluar dari akun">${icon('logout')}</button></div></div></aside><button class="menu-overlay" data-action="menu" aria-label="Tutup navigasi"></button><div class="workspace"><header class="topbar"><div class="breadcrumb"><button class="btn text icon mobile-toggle" data-action="menu" aria-label="Buka navigasi" aria-expanded="false" aria-controls="sidebar">${icon('menu')}</button><span>Menu</span>${icon('chevron')}<strong id="breadcrumb-page">Ringkasan</strong></div><div class="topbar-right"><span class="date">${icon('calendar')}<span>${new Intl.DateTimeFormat('id-ID',{dateStyle:'long',timeZone:'Asia/Jakarta'}).format(new Date())}</span></span><span class="role-tag">${roleLabel}</span><button class="btn text icon" data-action="refresh" title="Muat ulang data" aria-label="Muat ulang data">${icon('refresh')}</button></div></header><main class="main" id="main"></main></div></div>`;
}
async function renderRoute() {
 const route=routeNow();
 if(route.startsWith('confirm/'))return renderPortal();
 if(!state.user)return boot();
 if(!$('#main'))renderShell();
 if(state.route!==route){state.documentDeleteMode=false;state.documentSelected=[];state.customerDeleteMode=false;state.customerEditMode=false;state.customerSelected=[];}
 if(route.startsWith('doc/')&&state.route!==route&&!state.route.startsWith('doc/'))state.detailBackRoute=['dashboard','history','documents'].includes(state.route)&&$('#doc-table')?state.route:null;
 state.route=route;
 if(state.user.role==='checker'&&!route.startsWith('doc/')&&!route.startsWith('customer/')&&!['dashboard','documents','customers','customer-updates','history','settings'].includes(route)){go('dashboard');return;}
 if(state.user.role==='boh'&&!route.startsWith('doc/')&&!['dashboard','history'].includes(route)){go('dashboard');return;}
 const base=route.split('/')[0];const titles={'customer-updates':'Update Data',archive:'Arsip data',dashboard:'Dashboard',documents:'Pengajuan',history:'History',initiate:'Tambah Pengajuan',customers:'Data Nasabah',customer:'Detail Nasabah',emails:'Kotak email lokal',settings:'Pengaturan',doc:'Detail pengajuan',revise:'Revisi surat'};
 $('#breadcrumb-page').textContent=titles[base]||'Dashboard';
 document.querySelectorAll('.nav button').forEach(b=>{const active=b.dataset.route===base||(base==='doc'&&b.dataset.route==='documents')||(base==='customer'&&b.dataset.route==='customers');b.classList.toggle('active',active);if(active)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
 setMenuOpen(false);
 const main=$('#main');
 main.classList.toggle('dashboard-theme',route==='dashboard');
 try {
  if(route==='dashboard'||route==='documents')renderDashboard(route==='documents');
  else if(route==='history')renderHistory();
  else if(route==='initiate'&&state.user.role==='petugas')renderDocumentForm();
  else if(base==='doc'){main.innerHTML=notice('Memuat detail pengajuan…');const result=await api('/documents/'+encodeURIComponent(route.split('/')[1]));if(state.route!==route)return;state.detail=result.document;renderDetail();}
  else if(base==='revise'){go('doc/'+route.split('/')[1]);return;}
  else if(route==='customers'&&['sol','checker'].includes(state.user.role))renderCustomers();
  else if(base==='customer'&&['sol','checker'].includes(state.user.role))renderCustomerDetail(route.split('/')[1]);
  else if(route==='customer-updates'&&['sol','checker'].includes(state.user.role))renderCustomerUpdates();
  else if(route==='emails'&&state.config.mail_mode==='console'){main.innerHTML=notice('Memuat kotak email lokal…');const result=await api('/outbox');if(state.route!==route)return;state.messages=result.messages;renderEmails();}
  else if(base==='archive'&&state.user.role==='sol')await renderArchive(route.split('/')[1]);
  else if(route==='settings')renderSettings();
  else go('dashboard');
 }catch(err){main.innerHTML=errorBlock(err);if(err.status===401)renderLogin();}
}
const kpiLabels={total:'Total Pengajuan',pending:'Review Nasabah',checker:'Review SOL',review:'Review AMOL'};
const kpiReviewLabels={all:'Semua Status',pending:'Menunggu',approved:'Disetujui',rejected:'Ditolak'};
function customerReviewText(d,fallback) {return d.verification?.required===2&&d.customer_status==='pending'&&d.verification.confirmed>0?'Menunggu verifikator lainnya':fallback;}
function kpiReviewStatus(key,d) {
 if(key==='pending')return d.customer_status==='pending'?(d.sol_status==='cancelled'?null:'pending'):{confirmed:'approved',rejected:'rejected'}[d.customer_status]||null;
 if(key==='checker')return !needsChecker(d)||d.customer_status!=='confirmed'?null:d.checker_status||'pending';
 if(key==='review'&&needsChecker(d)&&d.checker_status!=='approved')return null;
 if(key==='review')return ['pending','revision_requested'].includes(d.sol_status)?(d.customer_status==='pending'?null:'pending'):['approved','rejected'].includes(d.sol_status)?d.sol_status:null;
 return null;
}
const kpiDocuments=(key,docs=state.documents,status='pending')=>activeDocuments(docs).filter(d=>key==='total'||(status==='all'?kpiReviewStatus(key,d)!==null:kpiReviewStatus(key,d)===status));
function dashboardCounts(docs) {
 return Object.fromEntries(Object.keys(kpiLabels).map(key=>[key,kpiDocuments(key,docs).length]));
}
function viewKpi(key) {
 if(!Object.hasOwn(kpiLabels,key))return;
 const documents=[...state.documents],monitoring=state.user.role==='boh',stage=key!=='total';
 let page=1,query='',status='pending';
 dialog.innerHTML=`<div class="kpi-detail"><div class="dialog-head"><h2 id="dialog-title">${esc(kpiLabels[key])}</h2><button class="btn text icon" data-action="close-dialog" aria-label="Tutup">${icon('close')}</button></div><div class="dialog-body stack"><p id="kpi-result-count" class="muted" aria-live="polite"></p><div class="kpi-filters"><div class="search-box">${icon('search')}<input id="kpi-search" class="input" type="search" aria-label="Cari detail KPI" placeholder="Cari nasabah, pengaju, CIF, atau ID dokumen…"></div>${stage?`<select id="kpi-status" class="input" aria-label="Filter status ${esc(kpiLabels[key])}">${Object.entries(kpiReviewLabels).map(([value,label])=>`<option value="${value}" ${value===status?'selected':''}>${label}</option>`).join('')}</select>`:''}</div><div id="kpi-documents"></div></div><div class="dialog-footer"><button class="btn" data-action="close-dialog">Tutup</button></div></div>`;
 const draw=()=>{
  const filtered=kpiDocuments(key,documents,status).filter(d=>`${d.customer_name} ${d.maker_name||''} ${d.cif} ${d.id}`.toLocaleLowerCase('id-ID').includes(query));
  $('#kpi-result-count').textContent=`${filtered.length} pengajuan`;
  const pages=Math.max(1,Math.ceil(filtered.length/5));page=Math.min(page,pages);
  const start=(page-1)*5,rows=filtered.slice(start,start+5);
  $('#kpi-documents').innerHTML=rows.length?`<div class="table-wrap"><table class="table submission-table"><thead><tr><th>Nasabah / Dokumen</th><th>Nominal transaksi</th><th>${stage?'Status review':'Status pengajuan'}</th></tr></thead><tbody>${rows.map(d=>`<tr data-document-row="${esc(d.id)}"><td><strong>${documentName(d)}</strong><small>${esc(d.id)}</small><small>CIF ${esc(d.cif)}</small></td><td><strong class="amount">${rupiah(d.nominal)}</strong><small>${esc(d.kind)}</small></td><td>${stage?badge(kpiReviewStatus(key,d),kpiReviewLabels[kpiReviewStatus(key,d)]):statusBadge(d)}</td></tr>`).join('')}</tbody></table></div><div class="table-footer"><span aria-live="polite">${start+1}–${start+rows.length} dari ${filtered.length} pengajuan</span>${pages>1?`<div class="table-pagination" role="group" aria-label="Halaman detail KPI"><button class="btn small" data-kpi-page="-1" ${page===1?'disabled':''}>Sebelumnya</button><span>${page} / ${pages}</span><button class="btn small" data-kpi-page="1" ${page===pages?'disabled':''}>Berikutnya</button></div>`:''}</div>`:empty(query?'Tidak ada pengajuan yang cocok':'Belum ada pengajuan',query?'Ubah pencarian Anda.':'Belum ada pengajuan dalam kategori ini.');
  labelRecordTables($('#kpi-documents'));bindDocumentRows($('#kpi-documents'));
 };
 $('#kpi-status')?.addEventListener('change',e=>{status=e.target.value;page=1;draw();});
 $('#kpi-search').addEventListener('input',e=>{query=e.target.value.trim().toLocaleLowerCase('id-ID');page=1;draw();});
 $('.kpi-detail').addEventListener('click',e=>{const button=e.target.closest('[data-kpi-page]');if(button){page+=Number(button.dataset.kpiPage);draw();}});
 draw();dialog.showModal();
}
function renderDashboard(full=false) {
 const sol=state.user.role==='sol',boh=state.user.role==='boh',checker=state.user.role==='checker';const docs=activeDocuments();
 const count=status=>docs.filter(d=>finalStatus(d)===status).length;
 const newButton=boh||checker?'':!sol?`<button class="btn primary" data-route="initiate">${icon('plus')} Tambah Pengajuan</button>`:full?`<div class="actions selection-actions">${state.documentDeleteMode?'<button class="btn" data-action="cancel-document-selection">Batal</button>':''}<button class="btn danger" id="delete-selected-documents" data-action="${state.documentDeleteMode?'archive-selected-documents':'select-documents'}" ${docs.length?'':'disabled'}>Hapus</button></div>`:'';
 const dateFilter=`<div class="table-head-tools"><details id="date-picker" class="date-picker"><summary id="date-range-trigger" class="btn ${state.dateFrom?'active':''}" aria-label="Pilih rentang tanggal pengajuan" title="${esc(rangeButtonLabel())}">${icon('calendar')}<span>${esc(rangeButtonLabel())}</span></summary><div id="date-range-panel" class="date-range-panel" role="group" aria-label="Kalender rentang tanggal"></div></details></div>`;
 const counts=dashboardCounts(docs);
 const stats=[['total','Total Pengajuan','blue'],['pending','Review Nasabah','blue'],['checker','Review SOL','yellow'],['review','Review AMOL','yellow']];
 const kpiIcons={total:'file',pending:'people',checker:'shield',review:'approval'};
 const attention=checker?counts.checker:sol?counts.review:0;
 const attentionText='pengajuan menunggu verifikasi';
 $('#main').innerHTML=`${!full?`<div class="stats stats-review-flow">${stats.map(([key,label,tone])=>`<button type="button" class="card stat stat-${tone}" data-action="view-kpi" data-kpi="${key}" aria-haspopup="dialog" title="Lihat detail ${label}"><span class="stat-icon" aria-hidden="true">${icon(kpiIcons[key])}</span><span class="stat-content"><span class="stat-label"><strong>${label}</strong></span><span class="stat-value" data-stat="${key}">${counts[key]}</span></span></button>`).join('')}</div><div class="task-link" id="dashboard-task" data-count="${attention}" ${attention?'':'hidden'}><span class="task-copy"><span class="task-icon" aria-hidden="true">${icon('clock')}</span><span><strong>${attention}</strong> ${attentionText}</span></span><button class="btn small" data-action="view-attention">Lihat ${icon('arrow')}</button></div>`:''}<section class="card submission-list-card"><div class="card-head"><h2>Daftar Pengajuan</h2>${full?newButton:''}</div><div class="filters submission-filters"><div class="search-box">${icon('search')}<input id="search" class="input" type="search" aria-label="Cari pengajuan" placeholder="Cari nasabah, pengaju, CIF, atau ID dokumen…" value="${esc(state.search)}"></div><select id="filter-status" class="input" aria-label="Filter status"><option value="all">Semua status</option><option value="pending">Menunggu nasabah</option><option value="checker">Menunggu Review SOL</option><option value="review">Menunggu Review AMOL</option></select><select id="filter-kind" class="input" aria-label="Filter jenis dokumen"><option value="all">Semua jenis</option><option>Standing Instruction</option><option>Warkat</option></select>${dateFilter}</div><div id="doc-table"></div></section>${state.config.mail_mode==='console'?'<footer class="workspace-footer">Pengujian lokal · Email belum terkirim ke nasabah</footer>':''}`;
 $('#filter-status').value=state.status;$('#filter-kind').value=state.kind;
 $('#search').addEventListener('input',e=>{state.search=e.target.value;state.page=1;renderTable();});
 $('#filter-status').addEventListener('change',e=>{state.status=e.target.value;state.page=1;renderTable();});
 $('#filter-kind').addEventListener('change',e=>{state.kind=e.target.value;state.page=1;renderTable();});
 bindDateRange();
 renderTable();
}
function bindDocumentRows(root=document) {
 root.querySelectorAll('[data-document-row]').forEach(row=>row.addEventListener('click',e=>{
  if(e.target.closest('a,button,input,select,textarea,label,details,summary')||window.getSelection()?.toString())return;
  if(row.closest('dialog'))dialog.close();
  state.page=1;go('doc/'+row.dataset.documentRow);
 }));
}
const documentName = d => `<a class="document-row-link" href="#doc/${esc(d.id)}" data-route="doc/${esc(d.id)}" aria-label="Lihat detail ${esc(d.customer_name)} ${esc(d.id)}">${esc(d.customer_name)}</a>`;
function labelRecordTables(root=document) {
 root.querySelectorAll('.submission-table,.history-table,.customer-table,.customer-updates-table,.account-table').forEach(table=>{
  table.classList.add('record-table');
  const headers=Array.from(table.querySelectorAll('thead th'),th=>th.textContent.trim());
  table.querySelectorAll('tbody tr').forEach(row=>Array.from(row.cells).forEach((cell,index)=>{
   cell.dataset.label=headers[index];
   const primary=table.classList.contains('customer-table')?headers[index]==='Nama nasabah':index===(row.cells[0].classList.contains('customer-select')?1:0);
   const actions=!!cell.querySelector('button');
   cell.classList.toggle('record-primary',primary);cell.classList.toggle('record-actions',actions);
   if(!primary&&!actions&&!cell.classList.contains('customer-select')){const value=document.createElement('div');value.className='record-value';while(cell.firstChild)value.append(cell.firstChild);cell.append(value);}
  }));
 });
}
function renderTable() {
 if(!$('#doc-table'))return;
 if(state.route==='history')return renderHistoryTable();
 const monitoring=state.user.role==='boh',selectable=state.user.role==='sol'&&state.route==='documents'&&state.documentDeleteMode;
 const active=activeDocuments();
 state.documentSelected=state.documentSelected.filter(id=>active.some(d=>d.id===id&&d.customer_status!=='confirmed'));
 const remove=$('#delete-selected-documents');if(remove){remove.disabled=selectable?!state.documentSelected.length:!active.some(d=>d.customer_status!=='confirmed');remove.textContent=selectable&&state.documentSelected.length?'Hapus ('+state.documentSelected.length+')':'Hapus';}
 let docs=active.filter(d=>matchesSubmissionDate(d)&&(state.status==='all'||finalStatus(d)===state.status)&&(state.kind==='all'||d.kind===state.kind)&&(`${d.customer_name} ${d.maker_name||''} ${d.id} ${d.cif}`.toLowerCase().includes(state.search.toLowerCase())));
 const total=docs.length,pages=Math.max(1,Math.ceil(total/5));state.page=Math.max(1,Math.min(state.page,pages));const start=(state.page-1)*5;docs=docs.slice(start,start+5);const removable=docs.filter(d=>d.customer_status!=='confirmed');
 $('#doc-table').innerHTML=docs.length?`<div class="table-wrap"><table class="table submission-table review-table ${selectable?'submission-selectable':''} ${monitoring?'monitoring-table':''}"><thead><tr>${selectable?`<th class="customer-select"><input id="select-visible-documents" type="checkbox" aria-label="Pilih semua pengajuan di halaman ini" ${removable.length&&removable.every(d=>state.documentSelected.includes(d.id))?'checked':''} ${removable.length?'':'disabled'}></th>`:''}<th>Nasabah / Dokumen</th><th>Jenis & nominal</th><th>Review Nasabah</th><th>Review SOL</th><th>Review AMOL</th></tr></thead><tbody>${docs.map(d=>`<tr data-document-row="${esc(d.id)}">${selectable?`<td class="customer-select"><input type="checkbox" data-document-select="${esc(d.id)}" aria-label="Pilih pengajuan ${esc(d.customer_name)} ${esc(d.id)}" ${state.documentSelected.includes(d.id)?'checked':''} ${d.customer_status==='confirmed'?'disabled title="Sudah disetujui nasabah"':''}></td>`:''}<td><strong>${documentName(d)}</strong><small class="mono">${esc(d.id)}</small></td><td><strong class="amount">${rupiah(d.nominal)}</strong><small>${esc(d.kind)}</small></td><td>${badge(d.customer_status,kpiReviewLabels[d.customer_status==='confirmed'?'approved':d.customer_status]||labels[d.customer_status])}</td><td>${needsChecker(d)?badge(d.checker_status,kpiReviewLabels[d.checker_status]||'Menunggu'):'<span class="muted">Alur sebelumnya</span>'}</td><td>${badge(d.sol_status,['pending','revision_requested'].includes(d.sol_status)?'Menunggu':kpiReviewLabels[d.sol_status]||solLabels[d.sol_status])}</td></tr>`).join('')}</tbody></table></div><div class="table-footer"><span aria-live="polite">Menampilkan ${start+1}–${start+docs.length} dari ${total} pengajuan</span>${pages>1?`<div class="table-pagination" role="group" aria-label="Halaman daftar pengajuan"><button class="btn small" data-action="page-prev" ${state.page===1?'disabled':''}>${icon('left')} Sebelumnya</button><span>Halaman ${state.page} dari ${pages}</span><button class="btn small" data-action="page-next" ${state.page===pages?'disabled':''}>Berikutnya ${icon('arrow')}</button></div>`:''}</div>`:empty(active.length?'Tidak ada pengajuan yang cocok':state.documents.length?'Tidak ada pengajuan yang sedang diproses':'Belum ada pengajuan',active.length?'Ubah pencarian atau filter untuk melihat pengajuan lainnya.':state.documents.length?'Pengajuan yang selesai, ditolak, atau dibatalkan tersedia di History.':state.user.role!=='petugas'?'Pengajuan dari petugas akan muncul di sini.':'Mulai dengan memilih nasabah dan mengunggah surat.',!active.length&&state.documents.length?'<button class="btn" data-route="history">Lihat History</button>':state.user.role==='petugas'&&!state.documents.length?'<button class="btn primary" data-route="initiate">Buat pengajuan pertama</button>':'');
 labelRecordTables($('#doc-table'));bindDocumentRows($('#doc-table'));
 if(selectable&&docs.length){
  const all=$('#select-visible-documents');all.indeterminate=removable.some(d=>state.documentSelected.includes(d.id))&&!removable.every(d=>state.documentSelected.includes(d.id));
  all.addEventListener('change',e=>{const visible=new Set(removable.map(d=>d.id));state.documentSelected=state.documentSelected.filter(id=>!visible.has(id));if(e.target.checked)state.documentSelected.push(...visible);renderTable();});
  document.querySelectorAll('[data-document-select]').forEach(input=>input.addEventListener('change',e=>{const id=e.target.dataset.documentSelect;state.documentSelected=state.documentSelected.filter(value=>value!==id);if(e.target.checked)state.documentSelected.push(id);renderTable();}));
 }
}
function historyOutcome(d) {
 if(needsChecker(d)&&d.checker_status==='rejected')return {result:'failure',label:'Ditolak',reason:'Ditolak SOL'};
 if(d.customer_status==='rejected')return {result:'failure',label:'Ditolak',reason:'Ditolak nasabah'};
 if(d.sol_status==='rejected')return {result:'failure',label:'Ditolak',reason:'Ditolak AMOL'};
 if(d.sol_status==='cancelled')return {result:'failure',label:'Ditolak',reason:'Pengajuan lama dibatalkan'};
 if(d.customer_status==='confirmed'&&d.sol_status==='approved'&&(!needsChecker(d)||d.checker_status==='approved'))return {result:'success',label:'Berhasil',reason:'Disetujui nasabah dan AMOL'};
 return null;
}
function renderHistory() {
 $('#main').innerHTML=`<section class="card"><div class="card-head"><h2>History Pengajuan</h2></div><div class="filters"><div class="search-box">${icon('search')}<input id="history-search" class="input" type="search" aria-label="Cari history" placeholder="Cari nasabah, pengaju, CIF, atau ID dokumen…" value="${esc(state.historySearch)}"></div><select id="history-result" class="input" aria-label="Filter hasil history"><option value="all">Semua hasil</option><option value="success">Berhasil</option><option value="failure">Ditolak</option></select></div><div id="doc-table"></div></section>`;
 $('#history-result').value=state.historyResult;
 $('#history-search').addEventListener('input',e=>{state.historySearch=e.target.value;state.page=1;renderHistoryTable();});
 $('#history-result').addEventListener('change',e=>{state.historyResult=e.target.value;state.page=1;renderHistoryTable();});
 renderHistoryTable();
}
function renderHistoryTable() {
 const monitoring=state.user.role==='boh';
 const all=state.documents.filter(d=>historyOutcome(d));
 const query=state.historySearch.trim().toLocaleLowerCase('id-ID');
 let docs=all.filter(d=>(state.historyResult==='all'||historyOutcome(d).result===state.historyResult)&&`${d.customer_name} ${d.maker_name||''} ${d.cif} ${d.id}`.toLocaleLowerCase('id-ID').includes(query));
 const total=docs.length,pages=Math.max(1,Math.ceil(total/5));state.page=Math.max(1,Math.min(state.page,pages));const start=(state.page-1)*5;docs=docs.slice(start,start+5);
 $('#doc-table').innerHTML=docs.length?`<div class="table-wrap"><table class="table history-table"><thead><tr><th>Nasabah / Dokumen</th><th>Nominal transaksi</th><th>Status</th><th>Terakhir diperbarui</th>${monitoring?'':'<th class="history-action-heading">Dokumen</th>'}</tr></thead><tbody>${docs.map(d=>{const outcome=historyOutcome(d);return `<tr data-document-row="${esc(d.id)}"><td><strong>${documentName(d)}</strong><small class="mono">${esc(d.id)}</small></td><td><strong class="amount">${rupiah(d.nominal)}</strong></td><td><span class="badge history-${outcome.result}">${outcome.label}</span></td><td>${date(d.updated)}</td>${monitoring?'':`<td><div class="actions history-actions">${outcome.result==='success'?`<button class="btn icon small" data-action="download-execution-pdf" data-id="${esc(d.id)}" aria-label="Unduh PDF ${esc(d.id)}" title="Unduh PDF pelaksanaan">${icon('download')}</button>`:''}</div></td>`}</tr>`;}).join('')}</tbody></table></div><div class="table-footer"><span aria-live="polite">Menampilkan ${start+1}–${start+docs.length} dari ${total} pengajuan</span>${pages>1?`<div class="table-pagination" role="group" aria-label="Halaman history"><button class="btn small" data-action="page-prev" ${state.page===1?'disabled':''}>${icon('left')} Sebelumnya</button><span>Halaman ${state.page} dari ${pages}</span><button class="btn small" data-action="page-next" ${state.page===pages?'disabled':''}>Berikutnya ${icon('arrow')}</button></div>`:''}</div>`:empty(all.length?'Tidak ada history yang cocok':'Belum ada history',all.length?'Ubah pencarian atau filter hasil.':'Pengajuan yang selesai, ditolak, atau dibatalkan akan muncul di sini.');
 labelRecordTables($('#doc-table'));bindDocumentRows($('#doc-table'));
}
function renderDocumentForm(doc=null) {
 const revision=!!doc;
 if(revision&&doc.sol_status!=='revision_requested'){$('#main').innerHTML=notice('Pengajuan ini belum diminta untuk direvisi.','warn');return;}
 const chosen=revision?(state.customers.find(c=>c.cif===doc.cif)||{cif:doc.cif,name:doc.customer_name,account:doc.account,person:doc.person,email:doc.email}):null;
 $('#main').innerHTML=`${head(revision?'TINDAK LANJUT AMOL':'INISIASI DOKUMEN',revision?'Revisi surat':'Tambah Pengajuan',revision?`${esc(doc.id)} · Surat revisi akan dikirim untuk konfirmasi ulang.`:'Lengkapi detail, unggah surat, lalu kirim konfirmasi kepada nasabah.',`<button class="btn" data-route="${revision?'doc/'+esc(doc.id):'documents'}">${icon('left')} Kembali</button>`)}${revision?`<div class="stack">${notice(`<strong>Catatan AMOL</strong><p>${esc(doc.sol_notes)}</p>`,'warn')}${notice('Revisi surat memerlukan konfirmasi baru. Tautan sebelumnya otomatis dibatalkan.')}</div>`:''}<div class="form-layout"><form class="card" id="document-form"><section class="form-section"><div class="section-title"><span class="step-number">01</span><div><h3>Data Nasabah</h3></div></div><div class="field"><label for="customer-search">Nasabah / CIF <span class="required">*</span></label><div class="customer-picker"><div class="search-box">${icon('search')}<input id="customer-search" class="input" type="text" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="customer-options" autocomplete="off" placeholder="Cari dan pilih nama nasabah atau CIF…" value="${chosen?esc(chosen.cif+' · '+chosen.name):''}" ${revision?'readonly':'required'}><input id="customer-select" type="hidden" name="cif" value="${doc?esc(doc.cif):''}"></div><div id="customer-options" class="customer-options" role="listbox" aria-label="Hasil pencarian nasabah" hidden></div></div>${!revision?'<small id="customer-match-count" aria-live="polite"></small>':''}</div><div id="customer-summary"></div></section><section class="form-section"><div class="section-title"><span class="step-number">02</span><div><h3>Detail transaksi</h3></div></div><div class="form-grid"><div class="field"><label for="doc-work-unit">Kode Uker</label><input id="doc-work-unit" type="text" value="0376 - Jakarta Sudirman 1" readonly></div><div class="field"><label for="doc-kind">Jenis Dokumen <span class="required">*</span></label><select id="doc-kind" name="kind"><option ${doc?.kind==='Standing Instruction'?'selected':''}>Standing Instruction</option><option ${doc?.kind==='Warkat'?'selected':''}>Warkat</option></select></div><div class="field"><label for="doc-nominal">Nominal Transfer (Rp) <span class="required">*</span></label><input id="doc-nominal" name="nominal" type="text" inputmode="numeric" placeholder="Contoh: 250.000.000" value="${doc?new Intl.NumberFormat('id-ID').format(doc.nominal):''}" required></div><div class="field"><label for="doc-destination-bank">Bank Tujuan <span class="required">*</span></label><select id="doc-destination-bank" name="destination_bank" required><option value="">Pilih bank tujuan</option>${(state.config.destination_banks||[]).map(bank=>`<option value="${esc(bank.value)}" ${doc?.destination_bank===bank.value?'selected':''}>${esc(bank.label)}</option>`).join('')}</select></div><div class="field"><label for="doc-destination-account">Rekening Tujuan <span class="required">*</span></label><input id="doc-destination-account" name="destination_account" type="text" inputmode="numeric" pattern="[0-9]+" maxlength="16" title="Nomor rekening hanya boleh berisi angka" placeholder="Pilih bank tujuan terlebih dahulu" value="${esc(doc?.destination_account||'')}" required></div><div class="field"><label for="doc-destination-name">Nama Rekening Tujuan <span class="required">*</span></label><input id="doc-destination-name" pattern="[A-Za-z ]+" title="Hanya huruf A–Z dan spasi" data-capitalize="words" autocapitalize="words" name="destination_name" type="text" maxlength="250" placeholder="Nama pemilik rekening tujuan" value="${esc(doc?.destination_name||'')}" required></div><div class="field span-2"><label for="doc-description">Keterangan</label><textarea id="doc-description" name="description" maxlength="1500" placeholder="Tujuan atau keterangan yang perlu diketahui nasabah…">${esc(doc?.description||'')}</textarea></div>${revision?'<div class="field span-2"><label for="revision-notes">Ringkasan perbaikan <span class="required">*</span></label><textarea id="revision-notes" name="notes" maxlength="1500" placeholder="Jelaskan bagian surat yang telah diperbaiki…" required></textarea></div>':''}</div></section><section class="form-section"><div class="section-title"><span class="step-number">03</span><div><h3>${revision?'Unggah surat hasil revisi':'Unggah surat'}</h3></div></div><div class="upload-area"><div class="upload-icon">${icon('upload')}</div><div class="upload-copy"><p>PDF, JPG, atau PNG · Maksimal 5 MB</p></div><button type="button" class="btn primary" data-action="choose-file">${icon('plus')} Upload Surat</button><input type="file" class="visually-hidden" id="doc-file" aria-label="Unggah surat transaksi" aria-required="true" accept=".pdf,.jpg,.jpeg,.png"><div id="file-status" class="file-status" aria-live="polite"></div></div></section><div class="form-bottom"><label class="check"><input type="checkbox" id="doc-ack" required><span>Saya telah memeriksa data pengajuan dan surat yang akan dikirim.</span></label><div id="form-error" class="error-message" role="alert"></div><div class="form-submit"><button type="submit" class="btn primary">${icon('mail')} ${revision?'Kirim surat revisi':'Kirim konfirmasi'}</button></div></div></form></div>`;
 setupDestinationInputs();
 const select=$('#customer-select');
 if(!revision)setupCustomerPicker();
 if(chosen)showCustomer(chosen);
 $('#doc-nominal').addEventListener('input',e=>{const digits=e.target.value.replace(/\D/g,'');e.target.value=digits?new Intl.NumberFormat('id-ID').format(Number(digits)):'';});
 $('#doc-file').addEventListener('change',e=>{const f=e.target.files[0];const valid=!f||f.size<=5*1024*1024;$('#file-status').textContent=f?(valid?`${f.name} · ${(f.size/1024/1024).toFixed(2)} MB`:'File melebihi batas 5 MB. Pilih surat lain.'):'';e.target.setCustomValidity(valid?'':'File maksimal 5 MB.');$('.upload-area').classList.toggle('has-file',!!f&&valid);$('[data-action="choose-file"]').innerHTML=icon('upload')+(f?' Ganti surat':' Upload Surat');});
 $('#document-form').addEventListener('submit',async e=>{e.preventDefault();const button=$('button[type=submit]',e.target);button.disabled=true;$('#form-error').textContent='';try{const file=$('#doc-file').files[0];if(!file||file.size>5*1024*1024)throw new Error('Pilih surat PDF, JPG, atau PNG berukuran maksimal 5 MB.');const nominal=Number($('#doc-nominal').value.replace(/\D/g,''));if(!Number.isSafeInteger(nominal)||nominal<=0)throw new Error('Masukkan nominal lebih dari Rp0, tanpa desimal.');const file64=await fileBase64(file);const payload={cif:doc?.cif||select.value,kind:$('#doc-kind').value,nominal,destination_bank:$('#doc-destination-bank').value,destination_account:$('#doc-destination-account').value.trim(),destination_name:$('#doc-destination-name').value.trim(),description:$('#doc-description').value,file:{name:file.name,base64:file64}};if(revision){payload.version=doc.version;payload.notes=$('#revision-notes').value;}const customer=state.customers.find(c=>c.cif===payload.cif);showDeliveryDialog(`<p><strong>${esc(doc?.customer_name||customer?.name)}</strong> · ${rupiah(nominal)}</p><p>Bank Rekening Tujuan: <strong>${esc(payload.destination_bank)}</strong><br>Rekening tujuan: <strong>${esc(payload.destination_account)}</strong><br>Atas nama: <strong>${esc(payload.destination_name)}</strong></p>${revision?'<p>Nasabah perlu memberikan keputusan baru untuk surat revisi ini.</p>':''}`,customer,async channel=>{const result=await api(revision?'/documents/'+doc.id+'/revise':'/documents',{...payload,channel});await refreshData();toast(channel==='whatsapp'?'Pengajuan dibuat. Pesan WhatsApp siap dikirim.':'Pengajuan dibuat dan email masuk antrean.');go('doc/'+result.id);return result.whatsapp;});button.disabled=false;}catch(err){$('#form-error').textContent=err.message;button.disabled=false;}});
}
function setupDestinationInputs() {
 const bankInput=$('#doc-destination-bank'),account=$('#doc-destination-account'),name=$('#doc-destination-name');
 const update=()=>{
  const bank=(state.config.destination_banks||[]).find(bank=>bank.value===bankInput.value);
  const lengths=bank?.lengths||[],hint=lengths.join(' atau ');
  account.placeholder=bank?`${hint} digit rekening ${bank.label}`:'Pilih bank tujuan terlebih dahulu';
  account.maxLength=lengths.length?Math.max(...lengths):16;
  account.pattern=lengths.length?`(?:${lengths.map(length=>`[0-9]{${length}}`).join('|')})`:'[0-9]+';
  account.title=bank?`Nomor rekening ${bank.label} harus ${hint} digit angka`:'Nomor rekening hanya boleh berisi angka';
  account.setCustomValidity(account.value&&bank&&!lengths.includes(account.value.length)?account.title:'');
 };
 const clean=(input,pattern)=>{
  const start=input.selectionStart,value=input.value;
  input.value=value.replace(pattern,'');
  if(start!==null)input.setSelectionRange(value.slice(0,start).replace(pattern,'').length,value.slice(0,start).replace(pattern,'').length);
 };
 bankInput.addEventListener('change',update);
 account.addEventListener('input',()=>{clean(account,/[^0-9]/g);update();});
 name.addEventListener('input',()=>clean(name,/[^A-Za-z ]/g));
 update();
}
function setupCustomerPicker() {
 const input=$('#customer-search'), value=$('#customer-select'), list=$('#customer-options');
 let matches=[], active=-1;
 const close=()=>{list.hidden=true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');active=-1;};
 const highlight=()=>{list.querySelectorAll('[role="option"]').forEach((option,i)=>{option.classList.toggle('highlighted',i===active);option.setAttribute('aria-selected',String(i===active));});if(active>=0){input.setAttribute('aria-activedescendant','customer-option-'+active);list.children[active]?.scrollIntoView({block:'nearest'});}else input.removeAttribute('aria-activedescendant');};
 const render=(query)=>{const q=query.trim().toLocaleLowerCase('id-ID');const all=state.customers.filter(c=>c.name.toLocaleLowerCase('id-ID').includes(q)||c.cif.includes(q));matches=all.slice(0,50);active=-1;list.innerHTML=matches.length?matches.map((c,i)=>`<button type="button" role="option" aria-selected="false" tabindex="-1" id="customer-option-${i}" data-index="${i}"><strong>${esc(c.name)}</strong><span>CIF ${esc(c.cif)}</span></button>`).join(''):'<div class="customer-no-results">Tidak ada nasabah yang cocok.</div>';list.hidden=false;input.setAttribute('aria-expanded','true');input.removeAttribute('aria-activedescendant');$('#customer-match-count').textContent=all.length>50?all.length+' nasabah ditemukan. Ketik lebih spesifik untuk mempersempit hasil.':all.length===0?'Nasabah baru dapat ditambahkan oleh AMOL.':'';};
 const choose=(index)=>{const c=matches[index];if(!c)return;value.value=c.cif;input.value=c.cif+' · '+c.name;input.setCustomValidity('');showCustomer(c);$('#customer-match-count').textContent='';close();};
 input.addEventListener('focus',()=>render(value.value?'':input.value));
 input.addEventListener('input',()=>{value.value='';input.setCustomValidity('Pilih nasabah dari hasil pencarian.');showCustomer(null);render(input.value);});
 input.addEventListener('keydown',e=>{if(e.key==='Escape'){close();return;}if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();if(list.hidden)render(value.value?'':input.value);if(matches.length){active=active<0?(e.key==='ArrowDown'?0:matches.length-1):(active+(e.key==='ArrowDown'?1:-1)+matches.length)%matches.length;highlight();}}else if(e.key==='Enter'&&!list.hidden){e.preventDefault();choose(active<0?0:active);}else if(e.key==='Tab')close();});
 input.addEventListener('blur',close);
 list.addEventListener('pointerdown',e=>{if(e.target.closest('[role="option"]'))e.preventDefault();});
 list.addEventListener('click',e=>{const option=e.target.closest('[data-index]');if(option)choose(Number(option.dataset.index));});
 input.setCustomValidity('Pilih nasabah dari hasil pencarian.');
}
function showCustomer(c) {$('#customer-summary').innerHTML=c?`<div class="customer-summary"><div><label>Nama nasabah</label><strong>${esc(c.name)}</strong></div><div><label>Nomor rekening</label><strong>${esc(c.account)}</strong></div><div><label>Jabatan</label><strong>${esc(c.person)}</strong></div><div><label>Email penerima</label><strong>${esc(c.email)}</strong></div>${c.verification_count===2?`<div><label>Verifikator 2 · ${esc(c.second_name)}</label><strong>${esc(c.second_email)}</strong></div><div><label>Skema persetujuan</label><strong>Wajib disetujui kedua verifikator</strong></div>`:''}</div>`:'';}
function fileBase64(file) {return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(new Error('File tidak dapat dibaca.'));reader.readAsDataURL(file);});}
function confirmationAvailability(d) {
 const active=d.customer_status==='pending'&&d.sol_status==='pending'&&d.file?.expires*1000>Date.now()&&!d.file?.used_at;
 const delivery=d.delivery||{email_requested:!!d.mail&& !['whatsapp_manual','cancelled'].includes(d.mail.status),whatsapp_prepared:d.audit?.some(a=>a.version===d.version&&(a.action==='Konfirmasi WhatsApp disiapkan'||a.notes?.startsWith('Kanal: Email dan WhatsApp manual')))};
 return {email:active&&!delivery.email_requested,whatsapp:d.verification?.required!==2&&active&&!delivery.whatsapp_prepared};
}
function resendIsReady(d) {return (Number.isFinite(d.resend_available_at)&&Date.now()>=d.resend_available_at*1000)||(Number.isFinite(d.file?.expires)&&Date.now()>=d.file.expires*1000);}
function auditEntry(a,customerName) {
 const reviewer=a.actor?.includes(' · Verifikator ')?a.actor:customerName;
 const action=reviewer?a.action.replace(/^Nasabah (?=(?:menyetujui|menolak) surat$)/,()=>reviewer+' '):a.action;
 return `<div class="timeline-entry"><strong>${esc(action)}</strong><time>${date(a.at)}</time>${a.notes||a.ip?`<details class="audit-details"><summary>Detail aktivitas</summary>${a.notes?`<p>${esc(a.notes.replace(/Versi email \d+/g,'Pengiriman email konfirmasi'))}</p>`:''}${a.ip?`<p class="mono">IP ${esc(a.ip)}</p>`:''}</details>`:''}</div>`;
}
function auditHistory(entries,customerName) {
 return `<div class="timeline">${entries.slice(0,3).map(a=>auditEntry(a,customerName)).join('')}</div>${entries.length>3?`<details class="audit-older"><summary>Lihat ${entries.length-3} aktivitas sebelumnya</summary><div class="timeline">${entries.slice(3).map(a=>auditEntry(a,customerName)).join('')}</div></details>`:''}`;
}
function renderDualDocumentProgress(d) {return renderDocumentProgress(d);}
function renderDocumentProgress(d) {
 const terminal=!!historyOutcome(d),checked=needsChecker(d),dual=d.verification?.required===2;
 const steps=[{title:'Pengajuan Dokumen',status:'Dokumen diajukan',tone:'complete'}];
 const verifiers=dual?[1,2].map(position=>d.verification.verifiers?.find(v=>v.position===position)||{position,status:d.customer_status==='confirmed'?'confirmed':'pending'}):[{position:1,status:d.customer_status}];
 for(const v of verifiers){const done=v.status==='confirmed',rejected=v.status==='rejected';steps.push({title:dual?'Verifikator '+v.position:'Review nasabah',status:done?'Disetujui':rejected?'Ditolak':terminal?'Tidak dilanjutkan':'Menunggu Verifikasi',tone:rejected?'rejected':done?'complete':terminal?'':'current'});}
 if(checked){const done=d.checker_status==='approved',rejected=d.checker_status==='rejected';steps.push({title:'Review SOL',status:done?'Disetujui':rejected?'Ditolak':terminal?'Tidak dilanjutkan':d.customer_status==='confirmed'?'Menunggu Review SOL':'Menunggu Verifikator',tone:rejected?'rejected':done?'complete':!terminal&&d.customer_status==='confirmed'?'current':''});}
 const done=d.sol_status==='approved',rejected=d.sol_status==='rejected',ready=d.customer_status==='confirmed'&&(!checked||d.checker_status==='approved');
 steps.push({title:'Review AMOL',status:done?'Disetujui AMOL':rejected?'Ditolak AMOL':terminal?'Tidak dilanjutkan':ready?'Menunggu Review AMOL':d.customer_status!=='confirmed'?'Menunggu Verifikator':'Menunggu Persetujuan SOL',tone:rejected?'rejected':done?'complete':!terminal&&ready?'current':''});
 const current=steps.findIndex(step=>step.tone==='current');
 return `<ol class="status-flow status-flow-${steps.length}${dual?' status-flow-dual':''}" aria-label="Alur pengajuan">${steps.map((step,index)=>`<li class="status-step ${step.tone}" ${index===current?'aria-current="step"':''}><span class="status-step-marker">${step.tone==='rejected'?icon('close'):step.tone==='complete'?icon('check'):index+1}</span><div class="status-step-copy"><strong>${esc(step.title)}</strong><span>${esc(step.status)}</span></div></li>`).join('')}</ol>`;
}
function renderSolDecision(d) {
 const checker=state.user?.role==='checker',stage=checker?'SOL':'AMOL';
 const ready=d.customer_status==='confirmed'&&['pending','revision_requested'].includes(d.sol_status)&&(checker?needsChecker(d)&&d.checker_status==='pending':!needsChecker(d)||d.checker_status==='approved');
 const notes=checker?d.checker_notes:d.sol_notes;
 return `<div class="sol-decision-panel"><h3>${checker?'Pemeriksaan SOL':'Persetujuan AMOL'}</h3>${notes?notice(`<strong>Catatan ${stage}</strong><p>${esc(notes)}</p>`):''}${!checker&&d.checker_notes?notice(`<strong>Catatan SOL</strong><p>${esc(d.checker_notes)}</p>`):''}${ready?`<div class="review-actions"><button class="btn primary" data-action="sol-review" data-decision="approved">${icon('check')} Setujui pengajuan</button><button class="btn danger" data-action="sol-review" data-decision="rejected">${icon('close')} Tolak pengajuan</button></div>`:`<p class="muted">${d.customer_status==='rejected'?'Pengajuan ditolak nasabah.':historyOutcome(d)?'Keputusan sudah tercatat.':d.customer_status!=='confirmed'?(d.verification?.required===2?'Menunggu persetujuan kedua verifikator.':'Menunggu respons nasabah.'):!checker&&needsChecker(d)&&d.checker_status!=='approved'?'Menunggu persetujuan SOL.':'Pemeriksaan SOL sudah disetujui. Menunggu persetujuan AMOL.'}</p>`}</div>`;
}
function verificationStatus(d) {
 if(d.verification?.required===2){if(d.customer_status==='confirmed')return 'Persetujuan kedua verifikator telah tercatat.';if(d.customer_status==='rejected')return 'Pengajuan ditolak oleh salah satu verifikator.';if(d.verification.confirmed===1)return 'Menunggu persetujuan verifikator lainnya.';}
 if(d.sol_status==='cancelled')return 'Link Konfirmasi dinonaktifkan.';
 if(d.mail?.status==='sent')return `Link Konfirmasi telah dikirim pada ${date(d.mail.sent_at)}.`;
 return {whatsapp_manual:'Link Konfirmasi siap dikirim melalui WhatsApp.',local:'Link Konfirmasi tersimpan untuk pengujian lokal.',failed:'Link Konfirmasi gagal dikirim.',retry:'Pengiriman Link Konfirmasi akan dicoba ulang.',sending:'Link Konfirmasi sedang dikirim.',queued:'Link Konfirmasi menunggu pengiriman.',cancelled:'Link Konfirmasi dinonaktifkan.'}[d.mail?.status]||'Link Konfirmasi belum tersedia.';
}
function renderOfficerFollowup(d) {
 if(d.maker!==state.user.id)return `<section class="card detail-section-card review-card"><div class="card-head detail-card-head"><div class="detail-card-title"><span class="detail-card-icon blue">${icon('shield')}</span><h2>Link Verifikasi</h2></div></div><div class="card-pad stack"><div class="verification-status-row"><label class="muted">Status</label><p><strong>${esc(verificationStatus(d))}</strong></p></div><p class="muted">Tindak lanjut pengajuan dilakukan oleh ${esc(d.maker_name||'Officer pembuat')}.</p></div></section>`;
 const canResend=d.customer_status==='pending'&&d.sol_status==='pending';const available=confirmationAvailability(d);const customer=state.customers.find(c=>c.cif===d.cif);const canSend=available.email||(available.whatsapp&&!!customer?.phone);
 return `<section class="card detail-section-card review-card"><div class="card-head detail-card-head"><div class="detail-card-title"><span class="detail-card-icon blue">${icon('shield')}</span><h2>Link Verifikasi</h2></div></div><div class="card-pad stack">${d.sol_notes?notice(`<strong>Catatan AMOL</strong><p>${esc(d.sol_notes)}</p>`,d.sol_status==='revision_requested'?'warn':''):''}${canResend?'':'<p class="muted">Respons nasabah sudah tercatat.</p>'}<div class="detail-email stack"><div class="verification-status-row"><label class="muted">Status</label><p><strong>${esc(verificationStatus(d))}</strong></p></div>${d.mail?.error?notice(esc(d.mail.error),'error'):''}</div><div class="detail-followup-actions">${state.config.whatsapp_manual&&canResend?`<button class="btn primary" data-action="send-verification" ${canSend?'':'disabled'}>${icon('mail')} Kirim konfirmasi</button>`:''}${canResend?`<button class="btn" data-action="resend" ${resendIsReady(d)?'':'disabled'} title="${resendIsReady(d)?'Buat tautan konfirmasi baru':`Tersedia mulai ${date(d.resend_available_at*1000)} atau saat link kedaluwarsa`}">${icon('refresh')} Kirim ulang</button>`:''}</div></div></section>`;
}
function sendVerification() {
 const d=state.detail;const available=confirmationAvailability(d);
 const customer=state.customers.find(c=>c.cif===d.cif);
 if(!available.email&&!(available.whatsapp&&customer?.phone))return;
 showDeliveryDialog(`<p><strong>${esc(d.customer_name)}</strong><br>${esc(d.id)}</p>`,customer,async channel=>{
  const result=await api('/documents/'+d.id+'/send-confirmation',{version:d.version,channel});
  await refreshData();await renderRoute();toast(channel==='whatsapp'?'Pesan WhatsApp siap dikirim.':'Email masuk antrean.');return result.whatsapp;
 },{emailAvailable:available.email,whatsappAvailable:available.whatsapp,availableAt:d.resend_available_at,currentDelivery:true,defaultChannel:available.email?'email':'whatsapp'});
}
function showWhatsAppPreview(preview) {
 dialog.innerHTML=`<div class="whatsapp-preview"><div class="dialog-head"><h2 id="dialog-title">Kirim WhatsApp</h2><button class="btn text icon" data-action="close-dialog" aria-label="Tutup">${icon('close')}</button></div><div class="dialog-body stack"><div class="field"><label for="whatsapp-phone">Nomor WhatsApp</label><input id="whatsapp-phone" value="+${esc(preview.phone)}" readonly></div><div class="field"><label for="whatsapp-message">Pratinjau pesan</label><textarea id="whatsapp-message" class="whatsapp-message" rows="14" readonly>${esc(preview.message)}</textarea></div><p class="muted">Pesan belum dikirim. Tekan Kirim setelah WhatsApp terbuka.</p></div><div class="dialog-footer"><button class="btn" data-action="copy-whatsapp-message">${icon('copy')} Salin pesan</button><a class="btn primary" href="${esc(preview.url)}" target="_blank" rel="noopener noreferrer">${icon('chat')} Buka WhatsApp</a></div></div>`;
 dialog.showModal();
}
function renderDualCustomerData(d,field,legacyPhone,singleTitle='Verifikator 1') {
 const verifiers=d.verification?.verifiers?.length?d.verification.verifiers:[{position:1,name:d.verifier_name,person:d.person,phone:legacyPhone,email:d.email}];
 const title=v=>verifiers.length===1?singleTitle:'Verifikator '+v.position;
 return `<div class="dual-customer-data"><dl class="dual-customer-overview">${field('Nama nasabah',d.customer_name,'person')}${field('CIF',d.cif,'identity')}${field('Nomor rekening',d.account,'payment')}</dl><div class="dual-detail-verifiers${verifiers.length===1?' single-detail-verifiers':''}">${verifiers.map(v=>`<section class="dual-detail-verifier" aria-label="${esc(title(v))}"><h3>${esc(title(v))}</h3><dl>${field('Nama Verifikator',v.name,'person')}${field('Jabatan Verifikator',v.person,'briefcase')}${field('Nomor HP',v.phone||(v.position===1?legacyPhone:''),'phone')}${field('Email Verifikator',v.email,'mail')}</dl></section>`).join('')}</div></div>`;
}
function renderDetail() {
 const d=state.detail;const sol=['sol','checker'].includes(state.user.role);const canDownload=state.user.role!=='boh'&&d.sol_status==='approved'&&d.customer_status==='confirmed'&&(!needsChecker(d)||d.checker_status==='approved');
 const detailNav=historyOutcome(d)?'history':state.user.role==='boh'?'dashboard':'documents';
 document.querySelectorAll('.nav [data-route]').forEach(button=>{const active=button.dataset.route===detailNav;button.classList.toggle('active',active);if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');});
 const customer=state.customers.find(c=>c.cif===d.cif);
 const backRoute=state.detailBackRoute||(historyOutcome(d)?'history':'dashboard');
 const activities=d.audit.filter(a=>a.action!=='Email diterima server SMTP');
 const field=(label,value,symbol)=>`<div class="detail-data-row"><dt><span class="detail-field-icon">${icon(symbol)}</span><span>${label}</span></dt><dd>${esc(value||'Belum tercatat')}</dd></div>`;
 const cardHead=(title,symbol,tone='blue',extra='')=>`<div class="card-head detail-card-head"><div class="detail-card-title"><span class="detail-card-icon ${tone}">${icon(symbol)}</span><h2>${title}</h2></div>${extra}</div>`;
 $('#main').innerHTML=`<div class="detail-page-heading"><div class="detail-title-row"><button type="button" class="btn icon small" data-route="${backRoute}" aria-label="Kembali" title="Kembali">${icon('left')}</button><h1>${esc(d.customer_name)}</h1></div>${canDownload?`<div class="detail-heading-actions"><button class="btn primary small" data-action="download-execution-pdf" aria-label="Unduh Dokumen Pelaksanaan">${icon('download')} Dokumen Pelaksanaan</button></div>`:''}</div>
 ${renderDocumentProgress(d)}
 <div class="detail-card-stack">
 <section class="card detail-section-card">${cardHead('Informasi Pengajuan','file')}<div class="detail-summary-grid"><div class="detail-summary-cell"><span class="detail-summary-symbol">${icon('file')}</span><dl><dt>Nomor SI</dt><dd class="detail-id-value"><span id="detail-document-id">${esc(d.id)}</span><button class="btn icon small" data-action="copy-document-id" aria-label="Salin nomor SI" title="Salin nomor SI">${icon('copy')}</button></dd></dl></div><div class="detail-summary-cell"><span class="detail-summary-symbol">${icon('calendar')}</span><dl><dt>Dibuat pada</dt><dd>${date(d.created)}</dd></dl></div><div class="detail-summary-cell"><span class="detail-summary-symbol purple">${icon('file')}</span><dl><dt>Jenis dokumen</dt><dd>${esc(d.kind)}</dd></dl></div></div></section>
 <section class="card detail-section-card">${cardHead('Data Nasabah','people')}${renderDualCustomerData(d,field,customer?.phone||d.phone,'Verifikator')}</section>
 <section class="card detail-section-card detail-transaction-card">${cardHead('Informasi Transaksi','payment','green')}<div class="detail-paired-data"><dl>${field('Nominal transaksi',rupiah(d.nominal),'payment')}${d.destination_bank?field('Bank Rekening Tujuan',d.destination_bank,'payment'):''}</dl><dl>${field('Nama Rekening Tujuan',d.destination_name,'person')}${field('Rekening tujuan',d.destination_account,'payment')}</dl></div><dl class="detail-transaction-description">${field('Keterangan',d.description||'—','info')}</dl></section>
 <section class="card detail-section-card detail-document-card">${cardHead('Dokumen Transaksi','attachment','purple')}<div class="card-pad"><div class="detail-file-row"><span class="detail-file-icon">${icon('file')}</span><strong>${esc(d.file.filename)}</strong><div class="actions"><button class="btn small" data-action="download-file">${icon('download')} Unduh</button><button class="btn small detail-preview-button" data-action="preview-file">${icon('eye')} Lihat</button></div></div><div id="preview-container"></div></div></section>
 ${sol?`<section class="card detail-section-card detail-decision-card">${cardHead(state.user.role==='checker'?'Pemeriksaan SOL':'Persetujuan AMOL','shield')}<div class="card-pad">${renderSolDecision(d)}</div></section>`:state.user.role==='petugas'?renderOfficerFollowup(d):''}
 <section class="card detail-section-card detail-activity-card">${cardHead('Log Aktivitas','clock','blue',`<small class="muted">${activities.length} aktivitas</small>`)}${auditHistory(activities,d.customer_name)}</section></div>`;
}
function bindCustomerRows(root) {
 root.querySelectorAll('[data-customer-detail]').forEach(row=>{
  const open=()=>go('customer/'+encodeURIComponent(row.dataset.customerDetail));
  row.addEventListener('click',e=>{if(e.target.closest('a,button,input,select,textarea,label,summary')||window.getSelection()?.toString().trim())return;open();});
  row.addEventListener('keydown',e=>{if(e.target===row&&['Enter',' '].includes(e.key)){e.preventDefault();open();}});
 });
}
function renderCustomerDetail(cif) {
 const c=state.customers.find(customer=>customer.cif===cif);
 if(!c){$('#main').innerHTML=empty('Nasabah tidak ditemukan','Kembali ke Data Nasabah untuk memilih nasabah.',`<button class="btn" data-route="customers">${icon('left')} Kembali</button>`);return;}
 const field=(label,value,symbol)=>`<div class="detail-data-row"><dt><span class="detail-field-icon">${icon(symbol)}</span><span>${label}</span></dt><dd>${esc(value||'Belum tercatat')}</dd></div>`;
 const d={customer_name:c.name,cif:c.cif,account:c.account,person:c.person,email:c.email};
 const verifiers=[{position:1,name:c.verifier_name,person:c.person,phone:c.phone,email:c.email}];
 if(c.verification_count===2)verifiers.push({position:2,name:c.second_name,person:c.second_person,phone:c.second_phone,email:c.second_email});
 d.verification={required:verifiers.length,verifiers};
 $('#main').innerHTML=`<div class="detail-page-heading"><div class="detail-title-row"><button type="button" class="btn icon small" data-route="customers" aria-label="Kembali" title="Kembali">${icon('left')}</button><h1>${esc(c.name)}</h1></div></div><div class="detail-card-stack"><section class="card detail-section-card"><div class="card-head detail-card-head"><div class="detail-card-title"><span class="detail-card-icon">${icon('people')}</span><h2>Data Nasabah</h2></div></div>${renderDualCustomerData(d,field,c.phone)}</section></div>`;
}
function renderCustomers() {
 const canManage=state.user.role==='checker',canEdit=canManage;
 $('#main').innerHTML=`<section class="card customers-card"><div class="card-head customers-card-head"><h1>Data Nasabah</h1><div class="actions selection-actions">${canManage&&(state.customerDeleteMode||state.customerEditMode)?'<button class="btn" data-action="cancel-customer-selection">Batal</button>':''}${canManage&&!state.customerEditMode?`<button class="btn danger" id="delete-selected-customers" data-action="select-customers" aria-pressed="${state.customerDeleteMode}" ${state.customers.length?'':'disabled'}>Hapus</button>`:''}${canEdit&&!state.customerDeleteMode?`<button class="btn ${state.customerEditMode?'amber':''}" id="edit-selected-customer" data-action="select-customer-edit" aria-pressed="${state.customerEditMode}">Edit</button>`:''}${canManage?`<button class="btn primary" data-action="new-customer">${icon('plus')} Tambah data</button>`:''}</div></div><div class="filters customer-filters"><form id="customer-search-form" class="search-box" role="search" autocomplete="off">${icon('search')}<input id="customer-list-search" name="customer_search" class="input" type="search" autocomplete="off" spellcheck="false" aria-label="Cari nama nasabah atau CIF" placeholder="Cari nama nasabah atau CIF…" value="${esc(state.customerSearch)}"></form></div><div id="customer-table"></div><div class="customer-list-footer"><span id="customer-list-count" aria-live="polite"></span></div></section>`;
 $('#customer-search-form').addEventListener('submit',e=>e.preventDefault());
 $('#customer-list-search').addEventListener('input',e=>{state.customerSearch=e.target.value;renderCustomerTable();});
 renderCustomerTable();
}
function renderCustomerTable() {
 const editing=state.user.role==='checker'&&state.customerEditMode;const selectable=state.user.role==='checker'&&(state.customerDeleteMode||editing);
 const pending=cif=>state.customerUpdates.some(r=>r.cif===cif&&r.status==='pending');
 const query=state.customerSearch.trim().toLocaleLowerCase('id-ID');const rows=state.customers.filter(c=>c.name.toLocaleLowerCase('id-ID').includes(query)||c.cif.includes(query));
 state.customerSelected=state.customerSelected.filter(cif=>state.customers.some(c=>c.cif===cif)&&!pending(cif));
 $('#customer-list-count').textContent=rows.length+' dari '+state.customers.length+' nasabah';
 const edit=$('#edit-selected-customer');if(edit)edit.disabled=!state.customers.some(c=>!pending(c.cif));
 const remove=$('#delete-selected-customers');if(remove)remove.disabled=!state.customers.some(c=>!pending(c.cif));
 $('#customer-table').innerHTML=rows.length?`<div class="table-wrap"><table class="table customer-table customer-directory-table"><colgroup>${selectable?'<col class="customer-checkbox-col">':''}<col class="customer-name-col"><col class="customer-account-col"><col class="customer-cif-col"><col class="customer-verifier-col"></colgroup><thead><tr>${selectable?`<th class="customer-select"><span class="visually-hidden">Pilih nasabah untuk ${editing?'diedit':'dihapus'}</span></th>`:''}<th>Nama Nasabah</th><th>Nomor Rekening</th><th>CIF</th><th>Jumlah Verifikator</th></tr></thead><tbody>${rows.map(c=>`<tr class="${selectable&&state.customerSelected.includes(c.cif)?'customer-row-selected':''}" ${selectable&&!pending(c.cif)?`data-customer-pick="${esc(c.cif)}" tabindex="0" aria-label="${editing?'Edit':'Hapus'} nasabah ${esc(c.name)}"`:!selectable?`data-customer-detail="${esc(c.cif)}" tabindex="0" aria-label="Lihat detail nasabah ${esc(c.name)}"`:''}>${selectable?`<td class="customer-select"><input type="radio" name="customer-to-select" data-customer-select="${esc(c.cif)}" ${pending(c.cif)?'disabled':''} aria-label="Pilih nasabah ${esc(c.name)}" ${state.customerSelected.includes(c.cif)?'checked':''}></td>`:''}<td><strong>${selectable?esc(c.name):`<a class="document-row-link" href="#customer/${encodeURIComponent(c.cif)}" aria-label="Lihat detail nasabah ${esc(c.name)}">${esc(c.name)}</a>`}</strong>${pending(c.cif)?'<small class="muted">Menunggu AMOL</small>':''}</td><td class="mono">${esc(c.account)}</td><td class="mono">${esc(c.cif)}</td><td>${c.verification_count===2?2:1}</td></tr>`).join('')}</tbody></table></div>`:empty(query?'Nasabah tidak ditemukan':'Belum ada nasabah',query?'Coba nama atau CIF yang berbeda.':'Tambahkan nasabah untuk memulai pengajuan.');
 labelRecordTables($('#customer-table'));bindCustomerRows($('#customer-table'));
 if(!selectable||!rows.length)return;
 const choose=cif=>{const customer=state.customers.find(c=>c.cif===cif);if(!customer||pending(cif))return;state.customerSelected=[cif];renderCustomerTable();if(editing)newCustomer(customer);else confirmCustomerDeletion([customer]);};
 document.querySelectorAll('[data-customer-select]').forEach(input=>input.addEventListener('click',()=>{if(!input.disabled)choose(input.dataset.customerSelect);}));
 document.querySelectorAll('[data-customer-pick]').forEach(row=>{
  row.addEventListener('click',e=>{if(!e.target.closest('input'))choose(row.dataset.customerPick);});
  row.addEventListener('keydown',e=>{if(e.target===row&&['Enter',' '].includes(e.key)){e.preventDefault();choose(row.dataset.customerPick);}});
 });
}
const customerFieldLabels={name:'Nama nasabah',account:'Nomor rekening',person:'Jabatan',email:'Alamat email',phone:'Nomor HP',verification_count:'Jumlah verifikator',verifier_name:'Nama verifikator 1',second_name:'Nama verifikator 2',second_person:'Jabatan verifikator 2',second_email:'Email verifikator 2',second_phone:'Nomor HP verifikator 2'};
const customerUpdateLabels={pending:'Menunggu',approved:'Disetujui',rejected:'Ditolak',cancelled:'Dibatalkan'};
function customerChanges(request) {return Object.keys(customerFieldLabels).filter(key=>request.operation==='delete'?request.old_data[key]!==''&&request.old_data[key]!=null:request.operation==='create'?request.new_data[key]!==''&&request.new_data[key]!=null:request.old_data[key]!==request.new_data[key]);}
function customerUpdateBadge(status) {return badge({pending:'pending',approved:'confirmed',rejected:'rejected',cancelled:'grey'}[status]||'grey',customerUpdateLabels[status]||status);}
function renderCustomerUpdates() {
 const rows=state.customerUpdates.filter(r=>state.customerUpdateFilter==='all'||r.status===state.customerUpdateFilter);
 $('#main').innerHTML=`<section class="card"><div class="card-head customer-updates-head"><h2>Permintaan Data Nasabah</h2><select id="customer-update-filter" class="input" aria-label="Filter pembaruan nasabah"><option value="all">Semua status</option>${Object.entries(customerUpdateLabels).map(([value,label])=>`<option value="${value}" ${state.customerUpdateFilter===value?'selected':''}>${label}</option>`).join('')}</select></div>${rows.length?`<div class="table-wrap"><table class="table customer-updates-table"><thead><tr><th>Nasabah / CIF</th><th>Jenis permintaan</th><th>Status</th><th>Diajukan pada</th><th>Aksi</th></tr></thead><tbody>${rows.map(r=>`<tr><td><strong>${esc(r.old_data.name||r.new_data.name)}</strong><small class="mono">CIF ${esc(r.cif)}</small></td><td>${r.operation==='create'?'Tambah nasabah':r.operation==='delete'?'Hapus nasabah':customerChanges(r).map(key=>customerFieldLabels[key]).join(', ')}</td><td>${customerUpdateBadge(r.status)}</td><td>${date(r.created)}</td><td><button class="btn icon small" data-action="view-customer-update" data-id="${esc(r.id)}" aria-label="Lihat perubahan ${esc(r.old_data.name||r.new_data.name)}" title="Lihat perubahan">${icon('eye')}</button></td></tr>`).join('')}</tbody></table></div>`:empty('Belum ada pembaruan',state.customerUpdateFilter==='all'?'Permintaan tambah, edit, dan hapus nasabah dari SOL akan tampil di sini.':'Tidak ada pembaruan dengan status ini.')}</section>`;
 labelRecordTables($('#main'));
 $('#customer-update-filter').addEventListener('change',e=>{state.customerUpdateFilter=e.target.value;renderCustomerUpdates();});
}
function viewCustomerUpdate(id) {
 const request=state.customerUpdates.find(r=>r.id===id);if(!request)return;
 const isCreate=request.operation==='create',isDelete=request.operation==='delete';
 const canReview=state.user.role==='sol'&&request.status==='pending'&&request.requested_by!==state.user.id;
 dialog.innerHTML=`<div class="dialog-head"><h2 id="dialog-title">${isCreate?'Tambah nasabah':isDelete?'Hapus nasabah':'Update Data'}</h2><button class="btn text icon" data-action="close-dialog" aria-label="Tutup">${icon('close')}</button></div><div class="dialog-body stack"><div class="spread"><div><strong>${esc(request.old_data.name||request.new_data.name)}</strong><p class="muted">CIF ${esc(request.cif)}</p></div>${customerUpdateBadge(request.status)}</div>${isDelete?'<p class="muted">Persetujuan akan menghapus data nasabah permanen. Riwayat pengajuan tetap tersimpan.</p>':''}<div class="table-wrap"><table class="table customer-change-comparison"><thead><tr><th>Data</th><th>${isCreate?'Belum terdaftar':isDelete?'Data nasabah':'Data sebelumnya'}</th>${isDelete?'':'<th>Usulan SOL</th>'}</tr></thead><tbody>${customerChanges(request).map(key=>`<tr><td>${customerFieldLabels[key]}</td><td>${esc(isCreate?'—':request.old_data[key]||'Belum diisi')}</td>${isDelete?'':`<td><strong>${esc(request.new_data[key])}</strong></td>`}</tr>`).join('')}</tbody></table></div><div class="field"><label for="customer-update-reason">Alasan permintaan</label><textarea id="customer-update-reason" rows="3" readonly>${esc(request.reason)}</textarea><small>${esc(request.requested_name)} · ${date(request.created)}</small></div>${canReview?'<div class="field"><label for="customer-review-notes">Catatan AMOL</label><textarea id="customer-review-notes" maxlength="1500" placeholder="Wajib diisi jika menolak permintaan."></textarea></div>':request.reviewed_at?`<div class="field"><label for="customer-update-decision">Keputusan</label><textarea id="customer-update-decision" rows="3" readonly>${esc(request.review_notes||'Tidak ada catatan tambahan.')}</textarea><small>${esc(request.reviewed_name)} · ${date(request.reviewed_at)}</small></div>`:`<p class="muted">${isCreate?'Nasabah akan terdaftar setelah AMOL menyetujui permintaan ini.':isDelete?'Nasabah akan dihapus setelah AMOL menyetujui. Riwayat pengajuan tetap tersimpan.':'Data nasabah tetap menggunakan data lama sampai AMOL menyetujui perubahan.'}</p>`}<div id="dialog-error" class="error-message" role="alert"></div></div><div class="dialog-footer customer-update-footer"><button class="btn" data-action="close-dialog">Tutup</button>${canReview?`<button class="btn danger" data-customer-review="rejected">Tolak</button><button class="btn ${isDelete?'danger':'primary'}" data-customer-review="approved">${isCreate?'Setujui nasabah':isDelete?'Setujui penghapusan':'Setujui perubahan'}</button>`:''}</div>`;
 dialog.showModal();
 dialog.querySelectorAll('[data-customer-review]').forEach(button=>button.addEventListener('click',async()=>{
  const decision=button.dataset.customerReview,notes=$('#customer-review-notes').value.trim();$('#dialog-error').textContent='';
  if(decision==='rejected'&&!notes){$('#dialog-error').textContent='Isi alasan penolakan terlebih dahulu.';$('#customer-review-notes').focus();return;}
  const buttons=dialog.querySelectorAll('[data-customer-review]');buttons.forEach(b=>b.disabled=true);
  try{await api('/customer-edit-requests/'+id+'/review',{decision,notes});await refreshData();dialog.close();renderCustomerUpdates();toast(isDelete?(decision==='approved'?'Penghapusan disetujui. Riwayat pengajuan tetap tersimpan.':'Penghapusan ditolak. Data nasabah tetap tersimpan.'):isCreate?(decision==='approved'?'Nasabah disetujui dan berhasil ditambahkan.':'Penambahan nasabah ditolak. Data belum ditambahkan.'):(decision==='approved'?'Pembaruan disetujui. Data nasabah sudah diperbarui.':'Pembaruan ditolak. Data nasabah tetap menggunakan data lama.'));}
  catch(err){$('#dialog-error').textContent=err.message;buttons.forEach(b=>b.disabled=false);}
 }));
}
async function renderArchive(kind) {
 if(kind!=='documents'){go('dashboard');return;}
 const result=await api('/'+kind+'/archived');
 if(state.route!=='archive/'+kind)return;
 const label=kind==='customers'?'nasabah':'pengajuan';
 $('#main').innerHTML=`${head('ARSIP DATA','Arsip '+label,'Pulihkan data ke daftar aktif atau hapus permanen jika sudah tidak diperlukan.',`<button class="btn" data-route="${kind==='customers'?'customers':'documents'}">${icon('left')} Kembali</button>`)}<section class="card"><div class="card-head"><h2>${result.items.length} ${label} diarsipkan</h2></div><div class="card-pad stack">${result.items.length?result.items.map(c=>{const key=c.cif||c.id;return `<div class="archive-row"><div><strong>${esc(c.name)}</strong><small class="muted">${esc(key)} · Dihapus ${date(c.archived_at)}</small></div><div class="actions"><button class="btn primary small" data-action="archive-restore" data-kind="${kind}" data-key="${esc(key)}" data-name="${esc(c.name)}">Pulihkan</button><button class="btn danger small" data-action="archive-purge" data-kind="${kind}" data-key="${esc(key)}" data-name="${esc(c.name)}">Hapus permanen</button></div></div>`;}).join(''):empty('Arsip kosong','Data yang dihapus akan muncul di sini.')}</div></section>`;
}
function confirmCustomerDeletion(selected) {
 if(state.user.role!=='checker'||!selected.length)return;
 showDialog('Ajukan hapus nasabah',`<div class="customer-delete"><p class="customer-delete-question">Ajukan penghapusan ${selected.length===1?'nasabah ini':selected.length+' nasabah ini'} ke AMOL?</p><div class="customer-delete-list">${selected.map(c=>`<div class="customer-delete-item"><div><span>Nama nasabah</span><strong>${esc(c.name)}</strong></div><div><span>Nomor rekening</span><strong class="mono">${esc(c.account)}</strong></div></div>`).join('')}</div><p class="customer-delete-note">Data nasabah dihapus setelah AMOL menyetujui. Riwayat pengajuan tetap tersimpan.</p><div class="field"><label for="customer-delete-reason">Alasan penghapusan <span class="required">*</span></label><textarea id="customer-delete-reason" maxlength="1500" required></textarea></div></div>`,async()=>{const reason=$('#customer-delete-reason').value.trim();if(!reason){$('#customer-delete-reason').focus();throw new Error('Isi alasan penghapusan terlebih dahulu.');}await api('/customer-delete-requests',{customers:selected.map(c=>({cif:c.cif,revision:c.revision})),reason});state.customerSelected=[];state.customerDeleteMode=false;await refreshData();renderCustomers();toast('Penghapusan nasabah menunggu persetujuan AMOL.');},'Ajukan ke AMOL','danger');
}
function newCustomer(customer=null) {
 if(state.user.role!=='checker')return;
 const submitForApproval=true;
 dialog.innerHTML=`<form id="customer-form"><div class="dialog-head"><h2 id="dialog-title">${customer?'Edit nasabah':'Tambah nasabah'}</h2><button type="button" class="btn text icon" data-action="close-dialog" aria-label="Tutup">${icon('close')}</button></div><div class="dialog-body stack"><div class="form-grid"><div class="field"><label for="c-cif">CIF</label><input id="c-cif" name="cif" value="${esc(customer?.cif||'')}" ${customer?'readonly':''} inputmode="numeric" pattern="[0-9]{3,30}" maxlength="30" required></div><div class="field"><label for="c-account">Nomor Rekening</label><input id="c-account" name="account" value="${esc(customer?.account||'')}" type="text" inputmode="numeric" pattern="[0-9]{15}" minlength="15" maxlength="15" title="Nomor rekening tepat 15 digit angka" required></div><div class="field span-2"><label for="c-name">Nama Nasabah / Perusahaan</label><input id="c-name" data-capitalize="words" autocapitalize="words" name="name" value="${esc(customer?.name||'')}" maxlength="250" required></div><div class="field span-2"><label for="c-verification-count">Jumlah Verifikator</label><select id="c-verification-count" name="verification_count"><option value="1">1</option><option value="2" ${customer?.verification_count===2?'selected':''}>2</option></select></div><fieldset id="c-first-verifier" class="span-2 verifier-fields"><legend id="c-first-verifier-title">Verifikator 1</legend><div class="field" id="c-verifier-name-field"><label for="c-verifier-name">Nama Verifikator</label><input id="c-verifier-name" name="verifier_name" value="${esc(customer?.verifier_name||'')}" maxlength="250"></div><div class="field"><label for="c-person">Jabatan</label><input id="c-person" data-capitalize="words" autocapitalize="words" name="person" value="${esc(customer?.person||'')}" maxlength="250" required></div><div class="field"><label for="c-phone">Nomor HP</label><input id="c-phone" name="phone" value="${esc(customer?.phone||'')}" type="tel" inputmode="tel" maxlength="16" pattern="(0[0-9]{9,12}|\\+?[1-9][0-9]{9,14})" placeholder="Contoh: 081234567890" title="Gunakan 10-15 digit, misalnya 081234567890 atau +6281234567890" required></div><div class="field"><label for="c-email">Email Verifikasi</label><input id="c-email" type="email" name="email" value="${esc(customer?.email||'')}" maxlength="254" required></div></fieldset><fieldset id="c-second-verifier" class="span-2 verifier-fields"><legend>Verifikator 2</legend><div class="field"><label for="c-second-name">Nama Verifikator</label><input id="c-second-name" name="second_name" value="${esc(customer?.second_name||'')}" maxlength="250" required></div><div class="field"><label for="c-second-person">Jabatan Verifikator</label><input id="c-second-person" name="second_person" value="${esc(customer?.second_person||'')}" maxlength="250" required></div><div class="field"><label for="c-second-phone">Nomor HP</label><input id="c-second-phone" name="second_phone" value="${esc(customer?.second_phone||'')}" type="tel" inputmode="tel" maxlength="16" pattern="(0[0-9]{9,12}|\\+?[1-9][0-9]{9,14})" placeholder="Contoh: 081234567890" title="Gunakan 10-15 digit, misalnya 081234567890 atau +6281234567890" required></div><div class="field"><label for="c-second-email">Email Verifikator</label><input id="c-second-email" name="second_email" type="email" value="${esc(customer?.second_email||'')}" maxlength="254" required></div><small>Setiap verifikator wajib menggunakan alamat email yang berbeda dan akan menerima link verifikasi pribadi.</small></fieldset>${customer?'<div class="field span-2"><label for="c-reason">Alasan perubahan</label><textarea id="c-reason" name="reason" maxlength="1500" required></textarea></div>':''}</div>${submitForApproval?'<p class="muted">Data nasabah akan disimpan setelah AMOL menyetujui permintaan ini.</p>':''}<div id="dialog-error" class="error-message" role="alert"></div></div><div class="dialog-footer"><button type="button" class="btn" data-action="close-dialog">Batal</button><button type="submit" class="btn primary">${submitForApproval?'Ajukan ke AMOL':'Simpan nasabah'}</button></div></form>`;dialog.showModal();
 const toggleVerifiers=()=>{const dual=$('#c-verification-count').value==='2';$('#customer-form').classList.toggle('dual-verifiers',dual);$('#c-first-verifier-title').hidden=!dual;$('#c-verifier-name-field').hidden=!dual;$('#c-verifier-name').disabled=!dual;$('#c-verifier-name').required=dual;$('#c-second-verifier').hidden=!dual;$('#c-second-verifier').disabled=!dual;$('label[for="c-person"]').textContent=dual?'Jabatan Verifikator':'Jabatan';$('label[for="c-email"]').textContent=dual?'Email Verifikator':'Email Verifikasi';};
 $('#c-verification-count').addEventListener('change',toggleVerifiers);toggleVerifiers();
 $('#customer-form').addEventListener('submit',async e=>{e.preventDefault();const button=$('button[type=submit]',e.target);button.disabled=true;try{const payload=Object.fromEntries(new FormData(e.target));payload.verification_count=Number(payload.verification_count);if(customer)payload.revision=customer.revision;await api(customer?'/customers/'+customer.cif+'/edit-requests':'/customer-create-requests',payload);await refreshData();dialog.close();state.customerEditMode=false;state.customerDeleteMode=false;state.customerSelected=[];renderCustomers();toast(submitForApproval?(customer?'Pembaruan nasabah menunggu persetujuan AMOL.':'Penambahan nasabah menunggu persetujuan AMOL.'):'Data nasabah berhasil disimpan.');}catch(err){$('#dialog-error').textContent=err.message;button.disabled=false;}});
}
function renderEmails() {
 if(!state.messages.find(m=>m.id===state.mailId))state.mailId=state.messages[0]?.id;
 const m=state.messages.find(m=>m.id===state.mailId);const link=m?.body.match(/https?:\/\/\S+\/#confirm\/[^\s]+/)?.[0];
 $('#main').innerHTML=`${head('PENGUJIAN ALUR EMAIL','Kotak email lokal','Pratinjau email untuk pengujian, tanpa pengiriman ke alamat nasabah.')}${notice('Email pengujian lokal. Tidak dikirim ke alamat nasabah.','warn')}<br>${m?`<div class="email-grid"><section class="card email-list">${state.messages.map(msg=>`<button class="email-item ${msg.id===m.id?'active':''}" data-mail="${esc(msg.id)}"><strong>${esc(msg.customer_name)}</strong><p>${esc(msg.doc_id)}</p><span class="badge grey">${esc(mailLabels[msg.status])}</span></button>`).join('')}</section><section class="card"><div class="card-head"><div><h2>Email konfirmasi</h2><p>${esc(m.recipient)}</p></div><button class="btn small" data-route="doc/${esc(m.doc_id)}">Detail surat</button></div><div class="card-pad stack"><div><strong>${esc(m.subject)}</strong><p class="email-meta">Kepada: ${esc(m.recipient)}<br>Dibuat: ${date(m.created)}</p></div><pre class="email-body">${esc(m.body)}</pre>${link?`<a class="btn primary" href="${esc(link)}" target="_blank" rel="noopener noreferrer">${icon('arrow')} Buka halaman konfirmasi nasabah</a>`:''}</div></section></div>`:empty('Belum ada email','Buat pengajuan terlebih dahulu. Email konfirmasi akan muncul di sini.')}`;
}
function renderSettings() {
 $('#main').innerHTML=`<div class="settings-page"><section class="card settings-card"><div class="card-head"><h2>Ubah kata sandi</h2></div><form id="password-form" class="card-pad stack"><div class="field"><label for="old-password">Kata sandi saat ini</label><input id="old-password" type="password" name="current" autocomplete="current-password" required></div><div class="field"><label for="new-password">Kata sandi baru</label><input id="new-password" type="password" name="password" minlength="12" autocomplete="new-password" aria-describedby="password-help" required><small id="password-help">Gunakan minimal 12 karakter dan hindari kata sandi yang dipakai di akun lain.</small></div><div class="field"><label for="repeat-password">Konfirmasi kata sandi baru</label><input id="repeat-password" type="password" minlength="12" autocomplete="new-password" required></div>${notice('Setelah kata sandi diubah, sesi di perangkat lain akan berakhir. Anda tetap masuk di perangkat ini.')}<div id="password-error" class="error-message" role="alert"></div><div class="settings-actions"><button class="btn primary" type="submit">${icon('check')} Simpan kata sandi</button></div></form></section></div>`;
 $('#password-form').addEventListener('submit',async e=>{e.preventDefault();const button=$('button',e.target);button.disabled=true;$('#password-error').textContent='';try{if($('#new-password').value!==$('#repeat-password').value)throw new Error('Konfirmasi kata sandi belum cocok. Ketik kembali kata sandi baru Anda.');await api('/password',Object.fromEntries(new FormData(e.target)));e.target.reset();toast('Kata sandi berhasil diperbarui.');}catch(err){$('#password-error').textContent=err.message;}finally{button.disabled=false;}});
}
function showDialog(title,body,onConfirm,confirmLabel='Ya, lanjutkan',variant='primary') {
 if(variant==='danger'&&confirmLabel.startsWith('Hapus'))body+=`<form id="action-password-form" autocomplete="off"><input type="text" name="username" autocomplete="username" value="${esc(state.user.email)}" readonly class="visually-hidden" tabindex="-1" aria-hidden="true"><div class="field"><label for="action-password">Kata sandi akun AMOL</label><input id="action-password" name="password" type="password" autocomplete="current-password" required><small>Masukkan kata sandi AMOL Anda untuk melanjutkan penghapusan.</small></div></form>`;
 dialog.innerHTML=`<div class="dialog-head"><h2 id="dialog-title">${esc(title)}</h2><button class="btn text icon" data-action="close-dialog" aria-label="Tutup">${icon('close')}</button></div><div class="dialog-body">${body}<div id="dialog-error" class="error-message" role="alert"></div></div><div class="dialog-footer"><button class="btn" data-action="close-dialog">Batal</button><button class="btn ${variant}" id="dialog-confirm">${esc(confirmLabel)}</button></div>`;
 $('#action-password-form')?.addEventListener('submit',e=>e.preventDefault());
 dialog.showModal();$('#dialog-confirm').addEventListener('click',async()=>{const b=$('#dialog-confirm');b.disabled=true;try{await onConfirm();dialog.close();}catch(err){if($('#dialog-error'))$('#dialog-error').textContent=err.message;b.disabled=false;}});
}
function showDeliveryDialog(body,customer,onConfirm,options={}) {
 const dual=(options.verificationCount??customer?.verification_count)===2;
 const hasWhatsApp=state.config.whatsapp_manual&&!dual; body+=dual?'<p class="muted">Email berisi link pribadi dikirim ke masing-masing verifikator. Review SOL menunggu persetujuan keduanya, lalu dilanjutkan ke AMOL.</p>':'';
 const hasPhone=!!customer?.phone;
 const available={email:options.emailAvailable!==false,whatsapp:!dual&&hasPhone&&options.whatsappAvailable!==false,both:!dual&&hasPhone&&options.emailAvailable!==false&&options.whatsappAvailable!==false};
 const preferred=options.defaultChannel||'email';
 const initial=available[preferred]?preferred:Object.keys(available).find(key=>available[key])||'email';
 const note=choice=>{
  const lines=[];
  if(options.currentDelivery){
   if(options.emailAvailable===false&&options.whatsappAvailable===false)lines.push(`Email dan WhatsApp belum bisa dikirim ulang. Gunakan Kirim ulang mulai ${date(options.availableAt*1000)} atau saat link kedaluwarsa.`);
   else if(options.emailAvailable===false)lines.push('Email sudah diproses untuk link ini dan tidak bisa dipilih lagi.');
   else if(options.whatsappAvailable===false)lines.push('WhatsApp sudah dipilih untuk link ini dan tidak bisa dipilih lagi.');
  }else{
   if(options.emailAvailable===false)lines.push(`Email dan WhatsApp belum bisa dikirim ulang. Tersedia mulai ${date(options.availableAt*1000)} atau saat link kedaluwarsa.`);
   if(options.whatsappAvailable===false)lines.push('Tautan sudah kedaluwarsa.');
  }
  if(!hasPhone)lines.push('Nomor HP belum tersedia.');
  if(available[choice]){lines.push(choice==='email'?'Email dikirim melalui sistem.':choice==='both'?'Email dikirim melalui sistem. WhatsApp dikirim manual setelah dibuka.':'WhatsApp dikirim manual setelah dibuka.');if(options.renewLink&&(choice!=='whatsapp'||!options.reuseWhatsApp))lines.push('Tautan sebelumnya akan diganti.');}
  return lines.join(' ');
 };
 dialog.innerHTML=`<div class="dialog-head"><h2 id="dialog-title">Kirim konfirmasi</h2><button class="btn text icon" data-action="close-dialog" aria-label="Tutup">${icon('close')}</button></div><div class="dialog-body stack">${body}${hasWhatsApp?`<fieldset class="delivery-picker"><legend>Kirim melalui</legend><div class="delivery-options">${[['email','Email','mail'],['whatsapp','WhatsApp','chat'],['both','Keduanya','check']].map(([value,label,symbol])=>`<label class="delivery-option"><input type="radio" name="delivery-channel" value="${value}" ${value===initial?'checked':''} ${!available[value]?'disabled':''}>${icon(symbol)}<span>${label}</span></label>`).join('')}</div></fieldset><p id="delivery-note" class="muted" aria-live="polite">${esc(note(initial))}</p>`:''}<div id="dialog-error" class="error-message" role="alert"></div></div><div class="dialog-footer"><button class="btn" data-action="close-dialog">Batal</button><button class="btn primary" id="delivery-confirm" ${!available[initial]?'disabled':''}>Lanjutkan</button></div>`;
 dialog.showModal();
 const channel=()=>$('input[name="delivery-channel"]:checked',dialog)?.value||'email';
 $('.delivery-picker',dialog)?.addEventListener('change',()=>{const choice=channel();$('#delivery-note').textContent=note(choice);$('#delivery-confirm').disabled=!available[choice];});
 $('#delivery-confirm').addEventListener('click',async()=>{const choice=channel();if(!available[choice])return;const controls=[...dialog.querySelectorAll('button:not(:disabled),input:not(:disabled)')];controls.forEach(el=>el.disabled=true);$('#dialog-error').textContent='';try{const preview=await onConfirm(choice);dialog.close();if(preview)showWhatsAppPreview(preview);}catch(err){$('#dialog-error').textContent=err.message;controls.forEach(el=>el.disabled=false);}});
}
async function review(decision) {
 if(!['approved','rejected'].includes(decision))return;
 const d=state.detail,needsReason=decision==='rejected';
 showDialog(needsReason?'Tolak pengajuan?':'Setujui pengajuan?',`<p>${esc(d.id)}<br><strong>${esc(d.customer_name)} · ${rupiah(d.nominal)}</strong></p>${needsReason?'<div class="field"><label for="sol-review-reason">Alasan penolakan <span class="required">*</span></label><textarea id="sol-review-reason" maxlength="1500" required placeholder="Jelaskan alasan penolakan"></textarea></div>':'<p>Keputusan akan dicatat untuk surat ini.</p>'}`,async()=>{
  const input=$('#sol-review-reason'),notes=needsReason?input.value.trim():'';
  if(needsReason&&!notes){input.focus();throw new Error('Isi alasan penolakan terlebih dahulu.');}
  await api('/documents/'+d.id+(state.user.role==='checker'?'/checker-review':'/review'),{version:d.version,decision,notes});await refreshData();toast('Keputusan '+(state.user.role==='checker'?'SOL':'AMOL')+' berhasil dicatat.');await renderRoute();
 },needsReason?'Tolak pengajuan':'Ya, setujui',needsReason?'danger':'primary');
 if(needsReason){const input=$('#sol-review-reason');input.focus();input.addEventListener('input',()=>{$('#dialog-error').textContent='';});}
}
let previewUrl=null;
async function viewFile(download=false,portalToken=null) {
 if(previewUrl){URL.revokeObjectURL(previewUrl);previewUrl=null;}
 const blob=portalToken?await api('/portal/file',{token:portalToken},true):await api('/documents/'+state.detail.id+'/file',undefined,true);
 previewUrl=URL.createObjectURL(blob);
 if(download){const a=document.createElement('a');a.href=previewUrl;a.download=portalToken?state.portal.file.filename:state.detail.file.filename;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1500);}
 else{const mime=portalToken?state.portal.file.mime:state.detail.file.mime;$('#preview-container').innerHTML=mime==='application/pdf'?`<iframe class="file-preview" title="Pratinjau surat PDF" src="${previewUrl}"></iframe>`:`<img class="image-preview" alt="Pratinjau surat" src="${previewUrl}">`;}
}
function portalHeader() {
 return `<header class="portal-header"><div class="portal-logo"><img src="/assets/bri-vista-login-logo.png" width="2120" height="742" alt="BRI VISTA — Verification, Integration &amp; Secure Tracking Application" fetchpriority="high"></div><span class="portal-private">${icon('lock')} Link Pribadi</span></header>`;
}
function portalFooter() {
 return `<footer class="portal-footer"><p>${icon('lock')} Selalu jaga kerahasiaan link dan informasi transaksi Anda.</p><p>BRI VISTA</p></footer>`;
}
function portalCardHeading(title,symbol) {
 return `<div class="card-head detail-card-head"><div class="detail-card-title"><span class="detail-card-icon">${icon(symbol)}</span><h2>${title}</h2></div></div>`;
}
async function renderPortal() {
 const token=routeNow().slice('confirm/'.length);state.route=routeNow();
 app.innerHTML=`<div class="customer-portal"><main class="portal">${portalHeader()}<section class="card portal-loading" role="status">Memuat surat Anda…</section></main></div>`;
 try{const result=await api('/portal',{token});if(routeNow()!=='confirm/'+token)return;state.portal=result;state.portalToken=token;renderPortalForm();}catch(err){if(routeNow()!=='confirm/'+token)return;app.innerHTML=`<div class="customer-portal"><main class="portal">${portalHeader()}<section class="card portal-result"><div class="portal-result-symbol">${icon('lock')}</div><h1>Tautan tidak tersedia</h1><p>${esc(err.message)}</p><div class="portal-result-guidance">Hubungi petugas untuk meminta tautan konfirmasi baru.</div></section>${portalFooter()}</main></div>`;}
}
function renderPortalForm() {
 const {document:d,file,expires,verifier}=state.portal;
 const field=(label,value,symbol)=>`<div class="detail-data-row"><dt><span class="detail-field-icon">${icon(symbol)}</span><span>${label}</span></dt><dd>${esc(value||'Belum tercatat')}</dd></div>`;
 app.innerHTML=`<div class="customer-portal"><main class="portal">${portalHeader()}
 <div class="portal-intro"><div><h1>Verifikasi Transaksi</h1><p>Pastikan data transaksi dan dokumen sudah sesuai sebelum memberikan konfirmasi.</p></div><div class="portal-expiry">${icon('calendar')}<div><span>Berlaku hingga</span><strong>${date(expires*1000)} WIB</strong></div></div></div>
 <div class="detail-card-stack portal-cards">
 <section class="card portal-information">${portalCardHeading('Informasi Transaksi','payment')}
 <div class="detail-summary-grid"><div class="detail-summary-cell"><span class="detail-summary-symbol">${icon('payment')}</span><dl><dt>Nominal transaksi</dt><dd>${rupiah(d.nominal)}</dd></dl></div><div class="detail-summary-cell"><span class="detail-summary-symbol">${icon('file')}</span><dl><dt>Nomor Pengajuan</dt><dd>${esc(d.id)}</dd></dl></div><div class="detail-summary-cell"><span class="detail-summary-symbol purple">${icon('file')}</span><dl><dt>Jenis dokumen</dt><dd>${esc(d.kind)}</dd></dl></div></div>
 <dl class="portal-transaction-data${d.destination_bank?'':' without-bank'}">${field('Nama nasabah',d.customer_name,'person')}${field('Jabatan',d.person,'briefcase')}${d.destination_bank?field('Bank Rekening Tujuan',d.destination_bank,'payment'):''}${field('Rekening tujuan',d.destination_account,'payment')}${field('Nama Rekening Tujuan',d.destination_name,'person')}</dl><dl class="portal-description">${field('Keterangan',d.description||'—','info')}</dl></section>
 <section class="card portal-document">${portalCardHeading('Dokumen Transaksi','attachment')}<div class="card-pad"><div class="detail-file-row"><span class="detail-file-icon">${icon('file')}</span><strong>${esc(file.filename)}</strong><div class="actions"><button class="btn small" data-action="portal-download">${icon('download')} Unduh</button><button class="btn small detail-preview-button" data-action="portal-preview">${icon('eye')} Lihat</button></div></div><div id="preview-container"></div></div></section>
 <section class="card portal-confirmation">${portalCardHeading('Konfirmasi Nasabah','shield')}<form class="card-pad stack" id="portal-form">${verifier?`<p class="muted">Verifikator ${verifier.position}: <strong>${esc(verifier.name)}</strong> · ${esc(d.person)}</p>`:''}<div class="field"><label for="portal-notes">Catatan <span class="portal-notes-hint">Wajib diisi jika menolak surat</span></label><textarea id="portal-notes" maxlength="1500" rows="3" placeholder="Tuliskan catatan Anda…"></textarea></div><label class="check portal-acknowledgement"><input type="checkbox" id="portal-ack" required><span>Saya adalah pihak yang berwenang. Saya telah memeriksa surat, detail transaksi, rekening tujuan, dan nominal <strong>${rupiah(d.nominal)}</strong>.</span></label><div id="portal-error" class="error-message" role="alert"></div><div class="actions portal-decision-actions"><button type="submit" class="btn danger" name="decision" value="rejected">${icon('close')} Tolak surat</button><button type="submit" class="btn primary" name="decision" value="confirmed">${icon('check')} Setujui surat</button></div></form></section>
 </div>${portalFooter()}</main></div>`;
 $('#portal-form').addEventListener('submit',e=>{e.preventDefault();const decision=e.submitter?.value;if(!decision)return;const notes=$('#portal-notes').value.trim();$('#portal-error').textContent='';if(decision==='rejected'&&!notes){$('#portal-error').textContent='Tuliskan alasan penolakan agar petugas dapat menindaklanjuti.';$('#portal-notes').focus();return;}
 showDialog(decision==='confirmed'?'Setujui surat ini?':'Tolak surat ini?',`<p>${esc(d.id)}<br><strong>${rupiah(d.nominal)}</strong></p><p>${d.destination_bank?`Bank Rekening Tujuan: <strong>${esc(d.destination_bank)}</strong><br>`:''}Rekening tujuan: <strong>${esc(d.destination_account||'Belum tercatat')}</strong><br>Atas nama: <strong>${esc(d.destination_name||'Belum tercatat')}</strong></p><p>${decision==='confirmed'?'Anda menyatakan bahwa surat dan nominal transaksi sudah sesuai.':'Penolakan dan alasan Anda akan diteruskan kepada petugas dan AMOL.'}</p>`,async()=>{const result=await api('/portal/decision',{token:state.portalToken,decision,notes,acknowledged:$('#portal-ack').checked});renderPortalResult(decision,d,result);},decision==='confirmed'?'Ya, setujui surat':'Ya, tolak surat',decision==='confirmed'?'primary':'danger');
 });
}
function renderPortalResult(decision,d,result={}) {
 const confirmed=decision==='confirmed';
 app.innerHTML=`<div class="customer-portal"><main class="portal">${portalHeader()}<section class="card portal-result"><div class="portal-result-symbol ${confirmed?'confirmed':'rejected'}">${icon(confirmed?'check':'close')}</div><h1>${confirmed?'Persetujuan telah tercatat':'Penolakan telah tercatat'}</h1><p>${confirmed?(result.verification?.required===2&&result.customer_status==='pending'?'Persetujuan Anda telah tercatat. Menunggu persetujuan verifikator lainnya sebelum review AMOL.':'Persetujuan surat Anda diteruskan kepada SOL untuk diperiksa, lalu AMOL untuk persetujuan akhir.'):'Petugas dan AMOL dapat melihat penolakan beserta catatan Anda.'}</p><dl class="portal-result-summary"><div><dt>Nomor Pengajuan</dt><dd>${esc(d.id)}</dd></div><div><dt>Nominal transaksi</dt><dd>${rupiah(d.nominal)}</dd></div>${d.destination_bank?`<div><dt>Bank Rekening Tujuan</dt><dd>${esc(d.destination_bank)}</dd></div>`:''}<div><dt>Rekening tujuan</dt><dd>${esc(d.destination_account||'Belum tercatat')}</dd></div><div><dt>Nama Rekening Tujuan</dt><dd>${esc(d.destination_name||'Belum tercatat')}</dd></div></dl><div class="portal-result-guidance">Link telah digunakan.</div></section>${portalFooter()}</main></div>`;
}
async function handleAction(e) {
 const target=e.target.closest('[data-route],[data-action],[data-mail]');if(!target)return;
 if(target.dataset.route){e.preventDefault();if(target.closest('dialog'))dialog.close();state.page=1;go(target.dataset.route);return;}
 if(target.dataset.mail){state.mailId=target.dataset.mail;renderEmails();return;}
 const action=target.dataset.action;
 try{
 if(action==='view-kpi')viewKpi(target.dataset.kpi);
 else if(action==='kpi-open-document'){dialog.close();go('doc/'+target.dataset.id);}
 else if(action==='page-prev'||action==='page-next'){state.page+=action==='page-next'?1:-1;renderTable();}
 else if(action==='view-attention'){if(state.user.role==='boh')return;state.search='';state.kind='all';state.dateFrom='';state.dateTo='';state.status=state.user.role==='checker'?'checker':state.user.role==='sol'?'review':'pending';state.page=1;go('documents');}
 else if(action==='demo'){$('#login-email').value=target.dataset.role+'@bpip.local';$('#login-password').value=target.dataset.role==='petugas'?'PetugasDemo!2026':'SolDemo!2026';}
 else if(action==='reload')location.reload();
 else if(action==='menu')setMenuOpen(!$('#sidebar').classList.contains('open'),true);
 else if(action==='close-dialog')dialog.close();
 else if(action==='new-customer'){if(state.user.role!=='checker')return;state.customerEditMode=false;state.customerDeleteMode=false;state.customerSelected=[];renderCustomers();newCustomer();}
 else if(action==='send-verification')sendVerification();
 else if(action==='copy-document-id'){try{await navigator.clipboard.writeText(state.detail.id);toast('Nomor SI disalin.');}catch{const range=document.createRange();range.selectNodeContents($('#detail-document-id'));const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);toast('Nomor SI dipilih. Gunakan fitur salin perangkat Anda.');}}
 else if(action==='copy-whatsapp-message'){const message=$('#whatsapp-message');try{await navigator.clipboard.writeText(message.value);toast('Pesan disalin.');}catch{message.focus();message.select();toast('Teks dipilih. Gunakan fitur salin perangkat Anda.');}}
 else if(action==='choose-file')$('#doc-file').click();
 else if(action==='select-customer-edit'){if(state.user.role!=='checker')return;state.customerEditMode=true;state.customerDeleteMode=false;state.customerSelected=[];renderCustomers();}
 else if(action==='view-customer-update'){viewCustomerUpdate(target.dataset.id);}
 else if(action==='select-customers'){if(state.user.role!=='checker')return;state.customerEditMode=false;state.customerDeleteMode=true;state.customerSelected=[];renderCustomers();}
 else if(action==='cancel-customer-selection'){state.customerDeleteMode=false;state.customerEditMode=false;state.customerSelected=[];renderCustomers();}
 else if(action==='archive-restore'||action==='archive-purge'){const kind=target.dataset.kind,key=target.dataset.key,name=target.dataset.name,purge=action==='archive-purge';if(kind!=='documents')return;showDialog(purge?'Hapus permanen?':'Pulihkan data?',`<p><strong>${esc(name)}</strong><br>${esc(key)}</p><p>${purge?(kind==='customers'?'Data master nasabah tidak dapat dipulihkan. Surat dan riwayat pengajuan lama tetap tersimpan.':'Surat dan data pengajuan dihapus permanen dan tidak dapat dipulihkan. Catatan audit pengelolaan tetap tersimpan.'):'Data ini akan kembali muncul di daftar. Tautan konfirmasi pengajuan lama tetap tidak berlaku.'}</p>${purge?`<div class="field"><label for="purge-confirmation">Ketik ${esc(key)} untuk konfirmasi</label><input id="purge-confirmation" autocomplete="off" required></div>`:''}`,async()=>{await api('/'+kind+'/'+encodeURIComponent(key)+'/'+(purge?'purge':'restore'),purge?{password:$('#action-password').value,confirmation:$('#purge-confirmation').value}:{});await refreshData();await renderArchive(kind);toast(purge?'Data dihapus permanen.':'Data dipulihkan.');},purge?'Hapus permanen':'Pulihkan',purge?'danger':'primary');}
 else if(action==='logout'){showDialog('Keluar dari ruang kerja?','<p class="logout-message">Anda dapat masuk kembali menggunakan akun yang sama.</p>',async()=>{await api('/logout',{});state.documents=[];state.customers=[];state.detail=null;renderLogin();},'Keluar','danger');}
 else if(action==='refresh'){target.disabled=true;await refreshData();await renderRoute();toast('Data sudah diperbarui.');target.disabled=false;}
 else if(action==='sol-review')review(target.dataset.decision);
 else if(action==='download-execution-pdf'){target.disabled=true;try{const id=target.dataset.id||state.detail.id;const blob=await api('/documents/'+id+'/execution-pdf',undefined,true);const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='konfirmasi-pelaksanaan-'+id+'.pdf';a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);toast('PDF pelaksanaan berhasil diunduh.');}finally{target.disabled=false;}}
 else if(action==='download-version'){target.disabled=true;const blob=await api('/documents/'+state.detail.id+'/versions/'+target.dataset.version+'/file',undefined,true);const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=state.detail.versions.find(v=>String(v.version)===target.dataset.version).filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);target.disabled=false;}
 else if(action==='preview-file'||action==='download-file'){target.disabled=true;await viewFile(action==='download-file');target.disabled=false;}
 else if(action==='portal-preview'||action==='portal-download'){target.disabled=true;await viewFile(action==='portal-download',state.portalToken);target.disabled=false;}
 else if(action==='archive-document'){const d=state.detail;showDialog('Hapus pengajuan dari daftar?',`<p>${esc(d.id)} akan dipindahkan ke arsip. Surat dan riwayat tetap tersimpan dan dapat dipulihkan oleh AMOL. Tautan nasabah dinonaktifkan; email yang sudah terkirim tidak dapat ditarik kembali.</p>`,async()=>{await api('/documents/'+d.id+'/archive',{version:d.version,password:$('#action-password').value});await refreshData();go('documents');toast('Pengajuan dipindahkan ke arsip.');},'Hapus pengajuan','danger');}
 else if(action==='select-documents'){state.documentDeleteMode=true;state.documentSelected=[];renderDashboard(true);}
 else if(action==='cancel-document-selection'){state.documentDeleteMode=false;state.documentSelected=[];renderDashboard(true);}
 else if(action==='archive-selected-documents'){const selected=state.documents.filter(d=>state.documentSelected.includes(d.id));if(!selected.length)return;showDialog('Hapus pengajuan',`<div class="customer-delete"><p class="customer-delete-question">Apakah Anda yakin akan menghapus ${selected.length===1?'pengajuan ini':selected.length+' pengajuan ini'}?</p><div class="customer-delete-list">${selected.map(d=>`<div class="customer-delete-item"><div><span>Nama nasabah</span><strong>${esc(d.customer_name)}</strong></div><div><span>Nomor pengajuan</span><strong class="mono">${esc(d.id)}</strong></div></div>`).join('')}</div><p class="customer-delete-note">Pengajuan dihapus dari daftar aktif. Surat dan catatan aktivitas tetap tersimpan. Tautan konfirmasi dinonaktifkan.</p></div>`,async()=>{await api('/documents/archive-selected',{documents:selected.map(d=>({id:d.id,version:d.version})),password:$('#action-password').value});state.documentSelected=[];state.documentDeleteMode=false;await refreshData();renderDashboard(true);toast('Pengajuan terpilih berhasil dihapus dari daftar.');},'Hapus pengajuan','danger');}

 else if(action==='resend'){const d=state.detail;showDeliveryDialog('<p>Tautan sebelumnya akan dibatalkan dan diganti dengan tautan konfirmasi baru.</p>',state.customers.find(c=>c.cif===d.cif),async channel=>{const result=await api('/documents/'+d.id+'/resend',{version:d.version,channel});await refreshData();await renderRoute();toast(channel==='whatsapp'?'Pesan WhatsApp baru siap dikirim.':'Email baru masuk antrean.');return result.whatsapp;},{verificationCount:d.verification?.required});}
 }catch(err){target.disabled=false;toast(err.message,true);if(err.status===401&&!state.route.startsWith('confirm/'))renderLogin();}
}
app.addEventListener('click',handleAction);dialog.addEventListener('click',handleAction);
window.addEventListener('hashchange',()=>{if(previewUrl){URL.revokeObjectURL(previewUrl);previewUrl=null;}renderRoute();});
// Refresh changed records only, so an open filter or focused action stays stable.
setInterval(async()=>{
 if(!state.user||state.route.startsWith('confirm/')||dialog.open)return;
 try{
  const before={documents:JSON.stringify(state.documents),customers:JSON.stringify(state.customers),updates:JSON.stringify(state.customerUpdates)};
  await refreshData();
  if(['dashboard','documents','history'].includes(state.route)){
   if(before.documents!==JSON.stringify(state.documents))renderTable();
   if(state.route==='dashboard'){
    const counts=dashboardCounts(state.documents);
    document.querySelectorAll('[data-stat]').forEach(el=>{el.textContent=counts[el.dataset.stat];});
    const sol=state.user.role==='sol';
    const attention=state.user.role==='checker'?counts.checker:sol?counts.review:0;
    const task=$('#dashboard-task');
    if(task&&task.dataset.count!==String(attention)){task.dataset.count=attention;task.hidden=!attention;$('strong',task).textContent=attention;}
   }

  }else if(state.route==='customer-updates'){
   if(before.updates!==JSON.stringify(state.customerUpdates))renderCustomerUpdates();
  }else if(state.route==='customers'){
   if(before.customers!==JSON.stringify(state.customers)||before.updates!==JSON.stringify(state.customerUpdates))renderCustomerTable();
  }else if(state.route.startsWith('doc/')){
   const result=await api('/documents/'+state.detail.id);
   if(result.document.maker_name!==state.detail.maker_name||JSON.stringify(result.document.delivery)!==JSON.stringify(state.detail.delivery)||result.document.updated!==state.detail.updated||result.document.mail?.status!==state.detail.mail?.status||result.document.resend_available_at!==state.detail.resend_available_at||($('#main [data-action="resend"]')?.disabled&&resendIsReady(result.document))){state.detail=result.document;renderDetail();}
  }
 }catch(err){if(err.status===401)renderLogin();}
},10000);
boot();
