/* ============================================
   ADCA - Automated Document Confirmation Agent
   Main Application Logic
   ============================================ */

'use strict';

/* ── Utilities (must be defined first) ── */
function formatRupiah(num) {
  if (!num && num !== 0) return '';
  return 'Rp ' + Number(num).toLocaleString('id-ID', { minimumFractionDigits: 0 });
}

function formatDate(isoStr) {
  const d = new Date(isoStr);
  return d.toLocaleString('id-ID', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function generateDocId(type) {
  const prefix = type === 'Standing Instruction' ? 'SI' : 'WK';
  const year = new Date().getFullYear();
  const seq = String(Math.floor(Math.random() * 899999) + 100001);
  return `${prefix}-${year}-${seq}`;
}

/* ── Cryptographically-styled Single-Use Verification Token Generator ── */
function generateVerificationToken() {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let rand = '';
  for (let i = 0; i < 14; i++) {
    rand += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return `vtok_${rand}`;
}

/* ── Real Accessible Verification URL Generator ── */
function getVerificationUrl(token) {
  if (typeof window !== 'undefined' && window.location) {
    // Gunakan lokasi URL file/web saat ini sehingga link bisa langsung dibuka di browser!
    const base = window.location.href.split('?')[0].split('#')[0];
    return `${base}?token=${token}`;
  }
  return `file:///Users/kznrifky/Documents/BPIP/web/index.html?token=${token}`;
}

/* ── Notification Template Generator with One Single-Time Link ── */
function buildNotifBody(channel, docId, customerName, apName, docType, nominal, token = null) {
  const apFirstName = apName.split(' ')[0];
  const nominalStr  = formatRupiah(nominal);
  const secureToken = token || ('vtok_' + docId.toLowerCase().replace(/[^a-z0-9]/g, ''));
  // URL nyata yang bisa diklik langsung di browser:
  const secureLink  = getVerificationUrl(secureToken);
  const dateStr     = formatDate(new Date().toISOString());

  if (channel === 'Email' || channel === 'WhatsApp & Email') {
    return {
      channel: 'Email',
      subject: `[ADCA] Permintaan Konfirmasi Dokumen ${docType} — ${docId}`,
      body: `Kepada Yth. ${apName},

Bank Pembangunan Indonesia mengajukan permintaan konfirmasi atas dokumen berikut:

━━━━━━━━━━━━━━━━━━━━━━━━━
📄  DETAIL TRANSAKSI
━━━━━━━━━━━━━━━━━━━━━━━━━
🔑  Document ID   : ${docId}
🏢  Nama Nasabah  : ${customerName}
📋  Jenis Dokumen : ${docType}
💰  Nominal       : ${nominalStr}
📅  Tanggal       : ${dateStr}
━━━━━━━━━━━━━━━━━━━━━━━━━

Tautan Verifikasi Resmi (Sekali Pakai / Single-Use Token):
🔗 ${secureLink}

⚠️ PENTING:
• Tautan di atas adalah "One Single-Time Verification Link" yang hanya dapat digunakan 1 (satu) kali.
• Setelah Anda memilih "Setujui" atau "Tolak", tautan otomatis hangus dan tidak dapat diakses kembali.
• Berlaku selama 24 jam. JANGAN bagikan tautan ini kepada siapapun demi keamanan rekening Anda.

Jika Anda tidak merasa mengajukan dokumen ini, segera hubungi kami di:
📞 1500-XXX | 📧 customercare@bpi.co.id

Hormat kami,
Tim Operasional — Bank Pembangunan Indonesia`,
    };
  }

  // WhatsApp format
  return {
    channel: 'WhatsApp',
    body: `🏦 *Bank Pembangunan Indonesia*
_Automated Document Confirmation Agent_

Kepada Yth. *${apFirstName}*,

Kami memerlukan konfirmasi resmi Anda atas dokumen berikut:

🔑 *No. Dokumen:* \`${docId}\`
🏢 *Nasabah:* ${customerName}
📋 *Jenis:* ${docType}
💰 *Nominal:* *${nominalStr}*
📅 *Tanggal:* ${dateStr}

Silakan beri konfirmasi melalui Tautan Sekali-Pakai (One-Time Link) berikut:
👉 ${secureLink}

🔒 _Tautan bersifat *sekali-pakai* (single-use) & otomatis hangus setelah dikonfirmasi. Berlaku 24 jam. Rahasiakan dari pihak lain._

Info: 1500-XXX | customercare@bpi.co.id`,
  };
}

/* ── Mock Database ── */
const DB = {
  customers: {
    '1234567': {
      cif: '1234567',
      name: 'PT. Maju Bersama Tbk',
      accountNo: '001-234-567-890',
      contactPerson: 'Budi Santoso',
      phone: '+62 812-3456-7890',
      email: 'budi.santoso@majubersama.co.id',
      authorizedPersons: ['Budi Santoso (Direktur Utama)', 'Siti Rahayu (Direktur Keuangan)'],
    },
    '9876543': {
      cif: '9876543',
      name: 'CV. Karya Mandiri',
      accountNo: '002-987-654-321',
      contactPerson: 'Ahmad Fadli',
      phone: '+62 878-9012-3456',
      email: 'ahmad.fadli@karyamandiri.id',
      authorizedPersons: ['Ahmad Fadli (Direktur)'],
    },
    '5551234': {
      cif: '5551234',
      name: 'PT. Sentra Niaga Global',
      accountNo: '003-555-123-4567',
      contactPerson: 'Dewi Lestari',
      phone: '+62 856-7890-1234',
      email: 'dewi.lestari@seniaga.com',
      authorizedPersons: ['Dewi Lestari (Komisaris)', 'Hendra Wijaya (Direktur)', 'Rina Kusuma (CFO)'],
    },
  },

  documents: [
    {
      id: 'SI-2026-004521',
      cif: '1234567',
      customerName: 'PT. Maju Bersama Tbk',
      type: 'Standing Instruction',
      nominal: 250000000,
      status: 'pending',
      channel: 'WhatsApp',
      authorizedPerson: 'Budi Santoso',
      createdAt: '2026-10-06T08:15:00',
      updatedAt: '2026-10-06T08:18:00',
      officer: 'Rina W.',
      notifDelivery: 'delivered',   // sending | delivered | read | failed
      notifSentAt: '2026-10-06T08:18:02',
      notifReadAt: null,
      solStatus: 'pending',          // pending | approved | rejected (Khusus Akun SOL)
      solReviewedBy: null,
      solReviewedAt: null,
      solNotes: '',
      // Single-Use Verification Token
      verificationToken: {
        token: 'vtok_7f8a9b2c3d4e',
        isUsed: false,
        usedAt: null,
        usedAction: null,
        expiresAt: new Date(Date.now() + 24 * 3600 * 1000).toISOString(),
      },
      auditTrail: [
        { time: '2026-10-06T08:15:00', action: 'Dokumen dibuat oleh Petugas (Maker)', actor: 'Rina W. (Petugas)', icon: '📋', type: 'created' },
        { time: '2026-10-06T08:18:00', action: 'Notifikasi & Single-Use Link terkirim via WhatsApp', actor: 'System', icon: '📤', type: 'sent',
          notifBody: buildNotifBody('WhatsApp', 'SI-2026-004521', 'PT. Maju Bersama Tbk', 'Budi Santoso', 'Standing Instruction', 250000000, 'vtok_7f8a9b2c3d4e') },
      ],
    },
    {
      id: 'WK-2026-003210',
      cif: '9876543',
      customerName: 'CV. Karya Mandiri',
      type: 'Warkat',
      nominal: 75500000,
      status: 'confirmed',
      channel: 'Email',
      authorizedPerson: 'Ahmad Fadli',
      createdAt: '2026-10-05T14:30:00',
      updatedAt: '2026-10-05T15:02:00',
      officer: 'Dedi P.',
      notifDelivery: 'read',
      notifSentAt: '2026-10-05T14:35:10',
      notifReadAt: '2026-10-05T14:58:44',
      solStatus: 'approved',
      solReviewedBy: 'Bambang Haryanto (SOL)',
      solReviewedAt: '2026-10-05T15:10:00',
      solNotes: 'Dokumen warkat fisik dan spesimen tanda tangan nasabah cocok.',
      // Single-Use Token: Already used
      verificationToken: {
        token: 'vtok_1a2b3c4d5e6f',
        isUsed: true,
        usedAt: '2026-10-05T15:02:00',
        usedAction: 'confirm',
        expiresAt: '2026-10-06T14:30:00',
      },
      auditTrail: [
        { time: '2026-10-05T14:30:00', action: 'Dokumen dibuat oleh Petugas (Maker)', actor: 'Dedi P. (Petugas)', icon: '📋', type: 'created' },
        { time: '2026-10-05T14:35:00', action: 'Notifikasi & Single-Use Link terkirim via Email', actor: 'System', icon: '📤', type: 'sent',
          notifBody: buildNotifBody('Email', 'WK-2026-003210', 'CV. Karya Mandiri', 'Ahmad Fadli', 'Warkat', 75500000, 'vtok_1a2b3c4d5e6f') },
        { time: '2026-10-05T14:58:44', action: 'Email dibuka/dibaca oleh nasabah', actor: 'Ahmad Fadli', icon: '👁️', type: 'read' },
        { time: '2026-10-05T15:02:00', action: 'Dikonfirmasi via Single-Use Link (Token Hangus)', actor: 'Ahmad Fadli (Nasabah)', icon: '✅', type: 'confirmed' },
        { time: '2026-10-05T15:10:00', action: 'Disetujui oleh SOL (Checker Approval)', actor: 'Bambang Haryanto (SOL)', icon: '🛡️', type: 'approved' },
      ],
    },
    {
      id: 'SI-2026-004498',
      cif: '5551234',
      customerName: 'PT. Sentra Niaga Global',
      type: 'Standing Instruction',
      nominal: 1800000000,
      status: 'rejected',
      channel: 'WhatsApp',
      authorizedPerson: 'Dewi Lestari',
      createdAt: '2026-10-05T09:00:00',
      updatedAt: '2026-10-05T10:15:00',
      officer: 'Yuli A.',
      notifDelivery: 'read',
      notifSentAt: '2026-10-05T09:05:03',
      notifReadAt: '2026-10-05T10:10:21',
      solStatus: 'rejected',
      solReviewedBy: 'Bambang Haryanto (SOL)',
      solReviewedAt: '2026-10-05T10:20:00',
      solNotes: 'Nasabah membatalkan transaksi karena perubahan klausul internal.',
      // Single-Use Token: Already used for rejection
      verificationToken: {
        token: 'vtok_9z8y7x6w5v4u',
        isUsed: true,
        usedAt: '2026-10-05T10:15:00',
        usedAction: 'reject',
        expiresAt: '2026-10-06T09:00:00',
      },
      auditTrail: [
        { time: '2026-10-05T09:00:00', action: 'Dokumen dibuat oleh Petugas (Maker)', actor: 'Yuli A. (Petugas)', icon: '📋', type: 'created' },
        { time: '2026-10-05T09:05:00', action: 'Notifikasi & Single-Use Link terkirim via WhatsApp', actor: 'System', icon: '📤', type: 'sent',
          notifBody: buildNotifBody('WhatsApp', 'SI-2026-004498', 'PT. Sentra Niaga Global', 'Dewi Lestari', 'Standing Instruction', 1800000000, 'vtok_9z8y7x6w5v4u') },
        { time: '2026-10-05T10:10:21', action: 'Pesan WhatsApp dibaca oleh nasabah', actor: 'Dewi Lestari', icon: '👁️', type: 'read' },
        { time: '2026-10-05T10:15:00', action: 'Ditolak via Single-Use Link (Token Hangus)', actor: 'Dewi Lestari (Nasabah)', icon: '❌', type: 'rejected' },
        { time: '2026-10-05T10:20:00', action: 'Pemberitahuan ditolak diproses oleh SOL', actor: 'Bambang Haryanto (SOL)', icon: '🛡️', type: 'rejected' },
      ],
    },
    {
      id: 'WK-2026-004010',
      cif: '1234567',
      customerName: 'PT. Maju Bersama Tbk',
      type: 'Warkat',
      nominal: 500000000,
      status: 'sending',
      channel: 'WhatsApp',
      authorizedPerson: 'Siti Rahayu',
      createdAt: '2026-10-06T09:45:00',
      updatedAt: '2026-10-06T09:47:00',
      officer: 'Rina W.',
      notifDelivery: 'sending',
      notifSentAt: null,
      notifReadAt: null,
      solStatus: 'pending',
      solReviewedBy: null,
      solReviewedAt: null,
      solNotes: '',
      verificationToken: {
        token: 'vtok_5k6l7m8n9o0p',
        isUsed: false,
        usedAt: null,
        usedAction: null,
        expiresAt: new Date(Date.now() + 24 * 3600 * 1000).toISOString(),
      },
      auditTrail: [
        { time: '2026-10-06T09:45:00', action: 'Dokumen dibuat oleh Petugas (Maker)', actor: 'Rina W. (Petugas)', icon: '📋', type: 'created' },
        { time: '2026-10-06T09:47:00', action: 'Notifikasi sedang dikirim...', actor: 'System', icon: '⏳', type: 'sent' },
      ],
    },
  ],
};


/* ── Role Management (RBAC: Maker vs Checker) ── */
let currentRole = 'petugas'; // 'petugas' (Maker) | 'sol' (Checker & Approver)

const ROLES = {
  petugas: {
    name: 'Rina Wulandari',
    roleTitle: 'Petugas CS · Cabang Utama (Maker)',
    avatar: 'RW',
  },
  sol: {
    name: 'Bambang Haryanto',
    roleTitle: 'Section Operations Lead (SOL) · Approver',
    avatar: 'BH',
  },
};

function switchRole(role) {
  currentRole = role;
  const user = ROLES[role];
  const nameEl   = document.getElementById('sidebar-user-name');
  const roleEl   = document.getElementById('sidebar-user-role');
  const avatarEl = document.getElementById('sidebar-user-avatar');
  const btnNew   = document.getElementById('btn-new-doc');
  const badgeSol = document.getElementById('sol-mode-badge');
  const navInit  = document.getElementById('nav-initiate');

  if (nameEl)   nameEl.textContent   = user.name;
  if (roleEl)   roleEl.textContent   = user.roleTitle;
  if (avatarEl) avatarEl.textContent = user.avatar;

  if (role === 'sol') {
    if (btnNew)   btnNew.style.display = 'none';
    if (badgeSol) badgeSol.style.display = 'inline-flex';
    if (navInit) {
      navInit.style.opacity = '0.4';
      navInit.title = 'Hanya Petugas (Maker) yang dapat membuat dokumen';
    }
    // If SOL is in initiate page, return to dashboard
    if (currentPage === 'initiate') {
      navigate('dashboard');
    }
    showToast('Beralih ke Akun SOL (Bambang Haryanto · Approver)', 'info', '🛡️');
  } else {
    if (btnNew)   btnNew.style.display = 'inline-flex';
    if (badgeSol) badgeSol.style.display = 'none';
    if (navInit) {
      navInit.style.opacity = '1';
      navInit.title = '';
    }
    showToast('Beralih ke Akun Petugas (Rina Wulandari · Maker)', 'info', '👤');
  }

  renderDashboard();
}

/* ── Navigation ── */
let currentPage = 'dashboard';

function navigate(page) {
  // RBAC Enforcement: SOL cannot access initiate page
  if (page === 'initiate' && currentRole === 'sol') {
    showToast('⛔ Akses Ditolak: Fitur Buat Dokumen hanya untuk Akun Petugas (Maker).', 'error');
    return;
  }

  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const target = document.getElementById(`page-${page}`);
  if (target) target.classList.add('active');

  const navItem = document.querySelector(`[data-page="${page}"]`);
  if (navItem) navItem.classList.add('active');

  const titles = {
    dashboard: ['Dashboard', 'Monitoring, Audit Trail & Otorisasi SOL'],
    initiate: ['Inisiasi Dokumen', 'Buat permintaan konfirmasi baru (Petugas CS)'],
    portal: ['Portal Konfirmasi', 'Simulasi tampilan nasabah (Validasi Nominal)'],
  };
  const [title, sub] = titles[page] || ['', ''];
  document.getElementById('topbar-title').textContent = title;
  document.getElementById('topbar-sub').textContent = sub;

  currentPage = page;
  window.scrollTo(0, 0);
}

/* ── Toast Notifications ── */
function showToast(message, type = 'info', icon = null) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icon || icons[type]}</span>
    <span class="toast-text">${message}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('removing');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

/* ── Dashboard ── */
function renderDashboard() {
  const docs = DB.documents;
  const pending   = docs.filter(d => d.status === 'pending' || d.status === 'sending').length;
  const confirmed = docs.filter(d => d.status === 'confirmed').length;
  const rejected  = docs.filter(d => d.status === 'rejected').length;
  const total     = docs.length;

  document.getElementById('stat-total').textContent    = total;
  document.getElementById('stat-pending').textContent  = pending;
  document.getElementById('stat-confirmed').textContent = confirmed;
  document.getElementById('stat-rejected').textContent = rejected;

  renderTable(docs);
}

/* ── Status Badges ── */
function notifDeliveryBadge(doc) {
  const d = doc.notifDelivery;
  if (!d || d === 'sending') return `<span style="font-size:11px;color:var(--text-muted)">⏳ Mengirim...</span>`;
  if (d === 'failed')    return `<span style="font-size:11px;color:var(--accent-red)" title="Pengiriman gagal">✗ Gagal</span>`;
  if (d === 'delivered') return `<span style="font-size:11px;color:var(--accent-teal)" title="Terkirim ke perangkat">✓ Terkirim</span>`;
  if (d === 'read')      return `<span style="font-size:11px;color:var(--accent-green)" title="Sudah dibaca nasabah">✓✓ Dibaca</span>`;
  return '';
}

function solStatusBadge(doc) {
  const s = doc.solStatus || 'pending';
  const isCustConfirmed = doc.status === 'confirmed';
  const isCustRejected  = doc.status === 'rejected';

  if (s === 'approved') {
    return `<span class="badge" style="background:rgba(139,92,246,0.18);color:var(--accent-purple);border:1px solid rgba(139,92,246,0.4)" title="Disetujui oleh: ${doc.solReviewedBy || 'SOL'}">🛡️ Disetujui SOL</span>`;
  }
  if (s === 'rejected') {
    return `<span class="badge" style="background:rgba(239,68,68,0.18);color:var(--accent-red);border:1px solid rgba(239,68,68,0.4)" title="Ditolak oleh: ${doc.solReviewedBy || 'SOL'}">⛔ Ditolak SOL</span>`;
  }
  if (isCustRejected) {
    return `<span class="badge" style="background:rgba(239,68,68,0.12);color:var(--accent-red);border:1px solid rgba(239,68,68,0.3)">❌ Ditolak Nasabah</span>`;
  }
  if (!isCustConfirmed) {
    // Nasabah belum approve (masih pending / sending)
    return `<span class="badge" style="background:rgba(255,255,255,0.05);color:var(--text-muted);border:1px solid var(--border)" title="Menunggu persetujuan nasabah melalui link verifikasi">🔒 Menunggu Nasabah</span>`;
  }
  // Nasabah sudah approve! Sekarang giliran SOL
  return `<span class="badge pulse" style="background:rgba(245,158,11,0.18);color:var(--accent-amber);border:1px solid rgba(245,158,11,0.4)" title="Nasabah sudah setuju! Menunggu verifikasi SOL">⏳ Siap Review SOL</span>`;
}

function showSolLockedNotice(docId) {
  showToast('🔒 Otorisasi Terkunci: SOL baru bisa melakukan review & approval SETELAH nasabah menyetujui transaksi via link verifikasi.', 'error');
}

function renderTable(docs) {
  const tbody = document.getElementById('doc-table-body');
  tbody.innerHTML = '';
  if (docs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align:center;color:var(--text-muted);padding:32px">Tidak ada data dokumen.</td></tr>`;
    return;
  }
  docs.forEach(doc => {
    const statusBadge = {
      pending:   '<span class="badge badge-pending">Pending</span>',
      sending:   '<span class="badge badge-sending pulse">Mengirim...</span>',
      confirmed: '<span class="badge badge-confirmed">Confirmed</span>',
      rejected:  '<span class="badge badge-rejected">Rejected</span>',
    }[doc.status] || '';

    // Action buttons depending on active role & sequential workflow
    let actionButtons = '';
    if (currentRole === 'sol') {
      const isCustConfirmed = doc.status === 'confirmed';
      const isSolPending    = doc.solStatus === 'pending' || !doc.solStatus;

      if (!isCustConfirmed && isSolPending) {
        // Nasabah belum approve -> SOL terkunci
        actionButtons = `
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            <button class="btn btn-secondary btn-sm" onclick="showSolLockedNotice('${doc.id}')" 
                    style="opacity:0.5;cursor:not-allowed;background:rgba(255,255,255,0.02)" title="Terkunci: Menunggu nasabah approve via link">
              🔒 Review SOL
            </button>
            <button class="btn btn-secondary btn-sm" onclick="showAuditTrail('${doc.id}')" title="Lihat riwayat lengkap">🔍 Audit</button>
          </div>
        `;
      } else {
        // Nasabah sudah approve atau dokumen sudah selesai diproses -> SOL bisa review
        actionButtons = `
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            <button class="btn ${isSolPending ? 'btn-primary' : 'btn-secondary'} btn-sm ${isSolPending ? 'pulse' : ''}" 
                    style="${isSolPending ? 'background:linear-gradient(135deg,var(--accent-purple),var(--accent-blue));border-color:transparent' : ''}" 
                    onclick="openSolApproval('${doc.id}')" title="Nasabah sudah setuju! Klik untuk review & approval SOL">
              🛡️ ${isSolPending ? 'Review SOL' : 'Detail SOL'}
            </button>
            <button class="btn btn-secondary btn-sm" onclick="showAuditTrail('${doc.id}')" title="Lihat riwayat lengkap">🔍 Audit</button>
          </div>
        `;
      }
    } else {
      // Petugas (Maker)
      actionButtons = `
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <button class="btn btn-secondary btn-sm" onclick="showAuditTrail('${doc.id}')" title="Lihat riwayat lengkap">🔍 Audit</button>
          <button class="btn btn-secondary btn-sm" onclick="showNotifPreview('${doc.id}')" title="Lihat dan kirim pesan ke Gmail/WhatsApp">✉️ Pesan</button>
          <button class="btn btn-secondary btn-sm" onclick="openPortalForDoc('${doc.id}')" title="Buka tautan verifikasi sekali-pakai sebagai nasabah" style="color:var(--accent-teal);border-color:rgba(20,184,166,0.3)">🔗 Portal</button>
        </div>
      `;
    }

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><span class="doc-id">${doc.id}</span></td>
      <td>
        <div style="font-weight:600;font-size:13px">${doc.customerName}</div>
        <div style="font-size:11px;color:var(--text-muted)">CIF: ${doc.cif}</div>
      </td>
      <td>${doc.type}</td>
      <td style="font-family:'JetBrains Mono',monospace;font-weight:600;color:var(--accent-amber)">${formatRupiah(doc.nominal)}</td>
      <td>${statusBadge}</td>
      <td>${solStatusBadge(doc)}</td>
      <td>
        <div style="font-size:12px;font-weight:600">${doc.channel}</div>
        <div style="margin-top:2px">${notifDeliveryBadge(doc)}</div>
        ${doc.notifReadAt ? `<div style="font-size:10px;color:var(--text-muted)">Dibaca: ${formatDate(doc.notifReadAt)}</div>` : ''}
      </td>
      <td>
        <div style="font-size:12px">${doc.authorizedPerson}</div>
      </td>
      <td style="font-size:12px;color:var(--text-secondary)">${formatDate(doc.createdAt)}</td>
      <td>${actionButtons}</td>
    `;
    tbody.appendChild(tr);
  });
}

function filterDocs() {
  const searchVal  = document.getElementById('filter-search').value.toLowerCase();
  const statusVal  = document.getElementById('filter-status').value;
  const typeVal    = document.getElementById('filter-type').value;

  let filtered = DB.documents.filter(doc => {
    const matchSearch = !searchVal ||
      doc.id.toLowerCase().includes(searchVal) ||
      doc.customerName.toLowerCase().includes(searchVal) ||
      doc.cif.includes(searchVal);
    const matchStatus = !statusVal || doc.status === statusVal;
    const matchType   = !typeVal || doc.type === typeVal;
    return matchSearch && matchStatus && matchType;
  });
  renderTable(filtered);
}

/* ── SOL Approval Modal & Logic ── */
window.currentSolDocId = null;

function openSolApproval(docId) {
  const doc = DB.documents.find(d => d.id === docId);
  if (!doc) return;

  window.currentSolDocId = doc.id;
  document.getElementById('sol-doc-id').textContent       = doc.id;
  document.getElementById('sol-doc-type').textContent     = doc.type;
  document.getElementById('sol-doc-customer').textContent = `${doc.customerName} (CIF: ${doc.cif})`;
  document.getElementById('sol-doc-nominal').textContent  = formatRupiah(doc.nominal);
  document.getElementById('sol-doc-officer').textContent  = doc.officer || 'Petugas CS (Maker)';

  const customerStatusMap = {
    pending:   '<span class="badge badge-pending">Menunggu Konfirmasi Nasabah</span>',
    sending:   '<span class="badge badge-sending">Notifikasi Sedang Dikirim</span>',
    confirmed: '<span class="badge badge-confirmed">✅ Sudah Dikonfirmasi Nasabah</span>',
    rejected:  '<span class="badge badge-rejected">❌ Ditolak oleh Nasabah</span>',
  };
  document.getElementById('sol-doc-customer-status').innerHTML = customerStatusMap[doc.status] || doc.status;
  document.getElementById('sol-notes').value = doc.solNotes || '';

  // Guard: Hanya bisa di-approve jika status nasabah === 'confirmed'
  const isCustomerConfirmed = doc.status === 'confirmed';
  const guardAlert  = document.getElementById('sol-customer-guard-alert');
  const btnApprove  = document.getElementById('btn-sol-approve-action');

  if (!isCustomerConfirmed) {
    if (guardAlert) guardAlert.style.display = 'block';
    if (btnApprove) {
      btnApprove.disabled = true;
      btnApprove.style.opacity = '0.35';
      btnApprove.style.cursor = 'not-allowed';
      btnApprove.title = 'Nasabah belum menyetujui transaksi ini.';
    }
  } else {
    if (guardAlert) guardAlert.style.display = 'none';
    if (btnApprove) {
      btnApprove.disabled = false;
      btnApprove.style.opacity = '1';
      btnApprove.style.cursor = 'pointer';
      btnApprove.title = '';
    }
  }

  openModal('modal-sol-approval');
}

function submitSolApproval(decision) {
  const docId = window.currentSolDocId;
  const doc = DB.documents.find(d => d.id === docId);
  if (!doc) return;

  // Strict check: Tidak boleh approve jika nasabah belum confirm
  if (decision === 'approved' && doc.status !== 'confirmed') {
    showToast('⛔ Tidak dapat menyetujui: Nasabah belum memberikan persetujuan via link!', 'error');
    return;
  }

  const notes = document.getElementById('sol-notes').value.trim();
  const now = new Date().toISOString();
  const solName = ROLES.sol.name;

  doc.solStatus      = decision; // 'approved' | 'rejected'
  doc.solReviewedBy  = `${solName} (SOL)`;
  doc.solReviewedAt  = now;
  doc.solNotes       = notes;

  const actionText = decision === 'approved'
    ? `Disetujui oleh SOL (${solName}) setelah konfirmasi nasabah diverifikasi`
    : `Ditolak oleh SOL (${solName})`;
  const actionIcon = decision === 'approved' ? '🛡️' : '⛔';

  doc.auditTrail.push({
    time: now,
    action: actionText + (notes ? ` — Catatan: "${notes}"` : ''),
    actor: `${solName} (Section Operations Lead)`,
    icon: actionIcon,
    type: decision === 'approved' ? 'confirmed' : 'rejected',
  });

  saveDBToStorage();
  closeModal('modal-sol-approval');
  renderDashboard();

  if (decision === 'approved') {
    showToast(`Dokumen ${doc.id} BERHASIL DISETUJUI & DIOTORISASI oleh SOL!`, 'success', '🛡️');
  } else {
    showToast(`Dokumen ${doc.id} DITOLAK oleh SOL!`, 'error', '❌');
  }
}

/* ── Audit Trail Modal ── */
function showAuditTrail(docId) {
  const doc = DB.documents.find(d => d.id === docId);
  if (!doc) return;

  document.getElementById('audit-doc-id').textContent      = doc.id;
  document.getElementById('audit-customer').textContent    = doc.customerName;
  document.getElementById('audit-type').textContent        = doc.type;
  document.getElementById('audit-nominal').textContent     = formatRupiah(doc.nominal);
  document.getElementById('audit-ap').textContent          = doc.authorizedPerson;
  document.getElementById('audit-delivery').innerHTML      = notifDeliveryBadge(doc);
  document.getElementById('audit-sent-at').textContent     = doc.notifSentAt ? formatDate(doc.notifSentAt) : '—';
  document.getElementById('audit-read-at').textContent     = doc.notifReadAt  ? formatDate(doc.notifReadAt)  : '—';

  const timeline = document.getElementById('audit-timeline');
  timeline.innerHTML = doc.auditTrail.map(entry => `
    <div class="timeline-item">
      <div class="timeline-dot ${entry.type}">
        ${entry.icon}
      </div>
      <div class="timeline-content">
        <div class="time">${formatDate(entry.time)}</div>
        <div class="action">${entry.action}</div>
        <div class="detail">${entry.actor}</div>
        ${entry.notifBody ? `<button class="btn btn-secondary btn-sm" style="margin-top:8px" onclick="showNotifPreviewDirect(${JSON.stringify(entry.notifBody).replace(/"/g, '&quot;')})">✉️ Lihat Isi Pesan</button>` : ''}
      </div>
    </div>
  `).join('');

  openModal('modal-audit');
}

/* ── Notif Preview Modal with Real Gmail & WhatsApp Compose ── */
function showNotifPreview(docId) {
  const doc = DB.documents.find(d => d.id === docId);
  if (!doc) return;
  const customer = DB.customers[doc.cif] || {};
  const sentEntry = doc.auditTrail.find(e => e.notifBody);
  const notifData = sentEntry ? sentEntry.notifBody : buildNotifBody(doc.channel, doc.id, doc.customerName, doc.authorizedPerson, doc.type, doc.nominal);
  showNotifPreviewDirect(notifData, customer.email, customer.phone);
}

function showNotifPreviewDirect(notifBody, targetEmail = '', targetPhone = '') {
  const isEmail = notifBody.channel === 'Email';
  document.getElementById('notif-channel-badge').textContent = isEmail ? '📧 Email' : '📱 WhatsApp';
  document.getElementById('notif-channel-badge').style.background = isEmail ? 'rgba(59,130,246,0.15)' : 'rgba(34,197,94,0.12)';
  document.getElementById('notif-channel-badge').style.color = isEmail ? 'var(--accent-blue)' : 'var(--accent-green)';

  if (isEmail) {
    document.getElementById('notif-subject-row').style.display = 'flex';
    document.getElementById('notif-subject').textContent = notifBody.subject || '';
  } else {
    document.getElementById('notif-subject-row').style.display = 'none';
  }

  const bodyEl = document.getElementById('notif-body');
  bodyEl.textContent = notifBody.body;
  bodyEl.className = isEmail ? 'notif-body-email' : 'notif-body-wa';

  // Real Gmail Web Compose Link
  const btnGmail = document.getElementById('btn-open-gmail-direct');
  if (btnGmail) {
    const toEmail = targetEmail || 'nasabah@bpi.co.id';
    const encodedSubject = encodeURIComponent(notifBody.subject || 'Konfirmasi Dokumen Bank');
    const encodedBody = encodeURIComponent(notifBody.body || '');
    btnGmail.href = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(toEmail)}&su=${encodedSubject}&body=${encodedBody}`;
    btnGmail.style.display = 'inline-flex';
  }

  // Real WhatsApp Web Compose Link
  const btnWa = document.getElementById('btn-open-wa-direct');
  if (btnWa) {
    const cleanPhone = (targetPhone || '').replace(/[^0-9]/g, '');
    const encodedText = encodeURIComponent(notifBody.body || '');
    btnWa.href = cleanPhone ? `https://wa.me/${cleanPhone}?text=${encodedText}` : `https://web.whatsapp.com/send?text=${encodedText}`;
    btnWa.style.display = 'inline-flex';
  }

  openModal('modal-notif');
}

function copyNotifBody() {
  const bodyText = document.getElementById('notif-body').textContent;
  if (!bodyText) return;
  navigator.clipboard.writeText(bodyText).then(() => {
    showToast('Isi pesan berhasil disalin ke clipboard! 📋', 'success');
  }).catch(() => {
    showToast('Pesan berhasil disalin!', 'success');
  });
}

/* ── Modals ── */
function openModal(id) {
  document.getElementById(id).classList.add('show');
  document.body.style.overflow = 'hidden';
}
function closeModal(id) {
  document.getElementById(id).classList.remove('show');
  document.body.style.overflow = '';
}

/* ── Form: Step Navigation ── */
let formStep = 1;
let selectedCustomer = null;
let generatedDocId = null;

function setStep(step) {
  formStep = step;
  for (let i = 1; i <= 3; i++) {
    const circle = document.getElementById(`step-circle-${i}`);
    const label  = document.getElementById(`step-label-${i}`);
    const stepEl = document.getElementById(`step-${i}`);
    const section = document.getElementById(`form-section-${i}`);

    if (i < step) {
      stepEl.className = 'step done';
      circle.textContent = '✓';
    } else if (i === step) {
      stepEl.className = 'step active';
      circle.textContent = i;
    } else {
      stepEl.className = 'step';
      circle.textContent = i;
    }

    if (section) section.style.display = i === step ? 'flex' : 'none';
  }
}

function nextStep() {
  if (formStep === 1) {
    if (!selectedCustomer) {
      showToast('Harap cari dan pilih nasabah terlebih dahulu.', 'error');
      return;
    }
  }
  if (formStep === 2) {
    const docType = document.getElementById('doc-type').value;
    const nominal = document.getElementById('nominal-input').value;
    if (!docType) { showToast('Pilih jenis dokumen.', 'error'); return; }
    if (!nominal || isNaN(parseFloat(nominal.replace(/[^0-9]/g, ''))) || parseFloat(nominal.replace(/[^0-9]/g, '')) <= 0) {
      showToast('Nominal transaksi wajib diisi dengan angka yang valid.', 'error');
      return;
    }
  }
  if (formStep < 3) setStep(formStep + 1);
  if (formStep === 3) renderReview();
}

function prevStep() {
  if (formStep > 1) setStep(formStep - 1);
}

/* ── CIF Search ── */
function searchCIF() {
  const cifInput = document.getElementById('cif-input').value.trim();
  if (!cifInput) { showToast('Masukkan CIF atau nomor rekening.', 'error'); return; }

  const customer = DB.customers[cifInput] ||
    Object.values(DB.customers).find(c => c.accountNo.replace(/-/g, '') === cifInput.replace(/-/g, ''));

  if (!customer) {
    showToast('Nasabah tidak ditemukan. Coba CIF: 1234567, 9876543, atau 5551234', 'error', '🔍');
    document.getElementById('customer-info-panel').classList.add('hidden');
    selectedCustomer = null;
    return;
  }

  selectedCustomer = customer;
  document.getElementById('info-name').textContent      = customer.name;
  document.getElementById('info-account').textContent   = customer.accountNo;
  document.getElementById('info-contact').textContent   = customer.contactPerson;
  document.getElementById('info-phone').textContent     = customer.phone;
  document.getElementById('info-email').textContent     = customer.email;

  // Fill authorized person dropdown
  const apSelect = document.getElementById('authorized-person');
  apSelect.innerHTML = '<option value="">-- Pilih Authorized Person --</option>';
  customer.authorizedPersons.forEach(ap => {
    const opt = document.createElement('option');
    opt.value = ap; opt.textContent = ap;
    apSelect.appendChild(opt);
  });

  document.getElementById('customer-info-panel').classList.remove('hidden');
  showToast(`Data nasabah ditemukan: ${customer.name}`, 'success', '🏢');
}

/* ── Nominal Input Formatter ── */
function formatNominalInput(e) {
  const raw = e.target.value.replace(/[^0-9]/g, '');
  const num = parseInt(raw || '0', 10);
  if (raw === '') { e.target.value = ''; document.getElementById('nominal-display').textContent = '—'; updateTemplatePreview(); return; }
  e.target.value = num.toLocaleString('id-ID');
  document.getElementById('nominal-display').textContent = formatRupiah(num);
  updateTemplatePreview();
}

/* ── Live Template Preview (Step 2) ── */
function updateTemplatePreview() {
  if (!selectedCustomer) return;
  const docType  = document.getElementById('doc-type').value;
  const nominalRaw = document.getElementById('nominal-input').value.replace(/[^0-9]/g, '');
  const nominal  = parseInt(nominalRaw || '0', 10);
  const ap       = document.getElementById('authorized-person').value || 'Yth. Nasabah';
  const channel  = document.getElementById('channel').value;
  const draftId  = generatedDocId || `${docType === 'Standing Instruction' ? 'SI' : 'WK'}-${new Date().getFullYear()}-XXXXXX`;

  const previewEl = document.getElementById('template-preview-box');
  const previewSection = document.getElementById('template-preview-section');
  if (!previewEl || !previewSection) return;

  if (!docType || nominal === 0) {
    previewSection.style.display = 'none';
    return;
  }

  previewSection.style.display = 'block';

  const body = buildNotifBody(channel === 'WhatsApp & Email' ? 'WhatsApp' : channel, draftId, selectedCustomer.name, ap, docType, nominal);
  const isEmail = channel === 'Email';

  document.getElementById('preview-channel-label').textContent = channel === 'WhatsApp' ? '📱 WhatsApp' : channel === 'Email' ? '📧 Email' : '📱📧 WhatsApp & Email';

  if (isEmail && body.subject) {
    document.getElementById('preview-subject-row').style.display = 'flex';
    document.getElementById('preview-subject-val').textContent = body.subject;
  } else {
    document.getElementById('preview-subject-row').style.display = 'none';
  }

  previewEl.textContent = body.body;
  previewEl.className = isEmail ? 'notif-body-email' : 'notif-body-wa';
}

/* ── File Upload ── */
function handleFileUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  const preview = document.getElementById('file-preview');
  const size = file.size > 1024*1024 ? `${(file.size/1024/1024).toFixed(2)} MB` : `${(file.size/1024).toFixed(1)} KB`;
  document.getElementById('file-name').textContent = file.name;
  document.getElementById('file-size').textContent = size;
  document.getElementById('file-icon-el').textContent = file.type.includes('pdf') ? '📄' : '🖼️';
  preview.classList.remove('hidden');
  showToast(`File "${file.name}" siap diupload.`, 'success', '📎');
}

/* ── Review Step ── */
function renderReview() {
  const docType  = document.getElementById('doc-type').value;
  const nominalRaw = document.getElementById('nominal-input').value.replace(/[^0-9]/g, '');
  const nominal  = parseInt(nominalRaw || '0', 10);
  const ap       = document.getElementById('authorized-person').value;
  const channel  = document.getElementById('channel').value;
  const notes    = document.getElementById('notes').value;

  generatedDocId = generateDocId(docType);

  document.getElementById('rev-doc-id').textContent       = generatedDocId;
  document.getElementById('rev-customer').textContent     = selectedCustomer.name;
  document.getElementById('rev-account').textContent      = selectedCustomer.accountNo;
  document.getElementById('rev-type').textContent         = docType;
  document.getElementById('rev-nominal').textContent      = formatRupiah(nominal);
  document.getElementById('rev-ap').textContent           = ap || '—';
  document.getElementById('rev-channel').textContent      = channel;
  document.getElementById('rev-notes').textContent        = notes || '—';
  document.getElementById('rev-date').textContent         = formatDate(new Date().toISOString());
}

/* ── Submit Form ── */
function submitForm() {
  const docType    = document.getElementById('doc-type').value;
  const nominalRaw = document.getElementById('nominal-input').value.replace(/[^0-9]/g, '');
  const nominal    = parseInt(nominalRaw || '0', 10);
  const ap         = document.getElementById('authorized-person').value;
  const channel    = document.getElementById('channel').value;
  const notes      = document.getElementById('notes').value;
  const now        = new Date().toISOString();

  // Build token and personalized message with single-use link
  const tokenStr = generateVerificationToken();
  const notifBody = buildNotifBody(channel === 'WhatsApp & Email' ? 'WhatsApp' : channel, generatedDocId, selectedCustomer.name, ap || 'Nasabah', docType, nominal, tokenStr);

  const newDoc = {
    id: generatedDocId,
    cif: selectedCustomer.cif,
    customerName: selectedCustomer.name,
    type: docType,
    nominal,
    status: 'sending',
    channel,
    authorizedPerson: ap || 'N/A',
    createdAt: now,
    updatedAt: now,
    officer: 'Rina W. (Petugas)',
    notes,
    notifDelivery: 'sending',
    notifSentAt: null,
    notifReadAt: null,
    solStatus: 'pending',       // Menunggu review & persetujuan SOL
    solReviewedBy: null,
    solReviewedAt: null,
    solNotes: '',
    // Single-Use Verification Token
    verificationToken: {
      token: tokenStr,
      isUsed: false,
      usedAt: null,
      usedAction: null,
      expiresAt: new Date(Date.now() + 24 * 3600 * 1000).toISOString(),
    },
    auditTrail: [
      { time: now, action: 'Dokumen dibuat oleh Petugas CS (Maker)', actor: 'Rina W. (Petugas)', icon: '📋', type: 'created' },
      { time: now, action: `Notifikasi & Single-Use Link (${tokenStr}) sedang dikirim via ${channel}...`, actor: 'System', icon: '⏳', type: 'sent' },
    ],
  };
  DB.documents.unshift(newDoc);

  // Simulate: delivered after 3s, then read after 8s
  const savedId = generatedDocId;
  setTimeout(() => {
    const docInDB = DB.documents.find(d => d.id === savedId);
    if (docInDB) {
      const sentAt = new Date().toISOString();
      docInDB.status = 'pending';
      docInDB.notifDelivery = 'delivered';
      docInDB.notifSentAt   = sentAt;
      docInDB.auditTrail[1] = {
        time: sentAt,
        action: `Notifikasi terkirim via ${channel}`,
        actor: 'System', icon: '📤', type: 'sent',
        notifBody,
      };
      if (currentPage === 'dashboard') renderDashboard();
      showToast('Notifikasi berhasil terkirim ke nasabah ✓', 'success', '📤');
    }
  }, 3000);

  setTimeout(() => {
    const docInDB = DB.documents.find(d => d.id === savedId);
    if (docInDB && docInDB.notifDelivery === 'delivered') {
      const readAt = new Date().toISOString();
      docInDB.notifDelivery = 'read';
      docInDB.notifReadAt   = readAt;
      docInDB.auditTrail.push({ time: readAt, action: `Pesan ${channel} dibaca oleh nasabah`, actor: docInDB.authorizedPerson, icon: '👁️', type: 'read' });
      if (currentPage === 'dashboard') renderDashboard();
      showToast('Pesan sudah dibaca oleh nasabah ✓✓', 'info', '👁️');
    }
  }, 8000);

  showToast(`Dokumen ${generatedDocId} dibuat! Mengirim notifikasi...`, 'info', '🚀');
  const savedDoc = { ...newDoc };
  resetForm();
  navigate('dashboard');
  renderDashboard();

  // Pre-fill portal for demo
  setTimeout(() => loadPortalDoc(savedId, DB.documents.find(d => d.id === savedId) || savedDoc), 3100);
  populatePortalSelector();
}

function resetForm() {
  selectedCustomer = null;
  generatedDocId   = null;
  document.getElementById('cif-input').value = '';
  document.getElementById('customer-info-panel').classList.add('hidden');
  document.getElementById('doc-type').value = '';
  document.getElementById('nominal-input').value = '';
  document.getElementById('nominal-display').textContent = '—';
  const previewSection = document.getElementById('template-preview-section');
  if (previewSection) previewSection.style.display = 'none';
  document.getElementById('authorized-person').innerHTML = '<option value="">-- Pilih Authorized Person --</option>';
  document.getElementById('channel').value = 'WhatsApp';
  document.getElementById('notes').value = '';
  document.getElementById('file-preview').classList.add('hidden');
  setStep(1);
}

/* ── Portal Confirmation Page (Single-Use Token Enforcement) ── */
function loadPortalDoc(docId, docData) {
  const doc = docData || DB.documents.find(d => d.id === docId);
  if (!doc) return;

  const vToken = doc.verificationToken || {
    token: 'vtok_' + doc.id.toLowerCase().replace(/[^a-z0-9]/g, ''),
    isUsed: doc.status === 'confirmed' || doc.status === 'rejected',
    usedAt: doc.updatedAt,
    usedAction: doc.status,
  };

  // Bind values
  document.getElementById('portal-doc-id').textContent      = doc.id;
  document.getElementById('portal-customer').textContent    = doc.customerName;
  document.getElementById('portal-type').textContent        = doc.type;
  document.getElementById('portal-date').textContent        = formatDate(doc.createdAt);
  document.getElementById('portal-ap').textContent          = doc.authorizedPerson;
  document.getElementById('portal-ap-detail').textContent   = doc.authorizedPerson;
  document.getElementById('portal-channel').textContent     = doc.channel;
  document.getElementById('portal-nominal-big').textContent = formatRupiah(doc.nominal);

  document.getElementById('portal-doc-icon-text').textContent = doc.type === 'Standing Instruction' ? '📋' : '📝';
  document.getElementById('portal-type-header').textContent   = doc.type;
  document.getElementById('portal-doc-id-header').textContent = doc.id;

  // Single-Use Token Header Info
  document.getElementById('portal-token-text').textContent = vToken.token;

  const tokenBadge    = document.getElementById('portal-token-badge');
  const consumedCard  = document.getElementById('portal-token-consumed-card');
  const greetingBox   = document.getElementById('portal-greeting-box');
  const actionArea    = document.getElementById('portal-action-area');
  const resultCard    = document.getElementById('portal-result');

  resultCard.style.display = 'none';
  resultCard.innerHTML = '';

  // Single-Use Enforcement Guard:
  if (vToken.isUsed) {
    // LINK SUDAH HANGUS / EXPIRED KARENA SUDAH DIRESPON
    tokenBadge.innerHTML = '🔴 Tautan Hangus (Sudah Digunakan)';
    tokenBadge.style.background = 'rgba(239,68,68,0.12)';
    tokenBadge.style.color = 'var(--accent-red)';
    tokenBadge.style.borderColor = 'rgba(239,68,68,0.3)';

    consumedCard.style.display = 'block';
    greetingBox.style.display  = 'none';
    actionArea.style.display   = 'none';

    document.getElementById('ptc-action').textContent = vToken.usedAction === 'confirm' ? '✅ Disetujui' : '❌ Ditolak';
    document.getElementById('ptc-time').textContent   = vToken.usedAt ? formatDate(vToken.usedAt) : '—';
    document.getElementById('ptc-actor').textContent  = doc.authorizedPerson;
  } else {
    // LINK FRESH / AKTIF (BELUM DIPAKAI)
    tokenBadge.innerHTML = '🟢 Tautan Aktif (1x Pakai)';
    tokenBadge.style.background = 'rgba(34,197,94,0.12)';
    tokenBadge.style.color = 'var(--accent-green)';
    tokenBadge.style.borderColor = 'rgba(34,197,94,0.3)';

    consumedCard.style.display = 'none';
    greetingBox.style.display  = 'block';
    actionArea.style.display   = 'block';
  }

  // Set current portal doc id for confirm/reject
  window.currentPortalDocId = doc.id;
}

function openPortalForDoc(docId) {
  loadPortalDoc(docId);
  const sel = document.getElementById('portal-doc-selector');
  if (sel) sel.value = docId;
  navigate('portal');
  showToast(`Membuka Tautan Verifikasi Dokumen ${docId}`, 'info', '🔗');
}

function copyPortalLink() {
  const docId = window.currentPortalDocId;
  const doc = DB.documents.find(d => d.id === docId);
  if (!doc) return;
  const token = doc.verificationToken ? doc.verificationToken.token : 'vtok_' + doc.id.toLowerCase();
  const link = getVerificationUrl(token);

  navigator.clipboard.writeText(link).then(() => {
    showToast(`Single-Use Link berhasil disalin: ${token} 📋`, 'success');
  }).catch(() => {
    showToast(`Link: ${link}`, 'success');
  });
}

/* ── Persistence & Cross-Tab Live Synchronization (LocalStorage) ── */
const STORAGE_KEY = 'ADCA_DOCUMENTS_V1';

function saveDBToStorage() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(DB.documents));
  } catch (err) {
    console.warn('Storage save failed:', err);
  }
}

function loadDBFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        DB.documents = parsed;
      }
    } else {
      // First run: save default seed documents
      saveDBToStorage();
    }
  } catch (err) {
    console.warn('Storage load failed:', err);
  }
}

// Live listener: When customer confirms in another tab, dashboard updates immediately!
window.addEventListener('storage', (e) => {
  if (e.key === STORAGE_KEY) {
    loadDBFromStorage();
    renderDashboard();
    populatePortalSelector();
    showToast('Pembaruan data transaksi diterima secara real-time! 🔄', 'info');
  }
});

/* ── URL Token Detection (Standalone Customer Portal View) ── */
function checkTokenInUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  const tokenParam = urlParams.get('token');
  if (tokenParam) {
    // Find matching document by verification token
    const targetDoc = DB.documents.find(d => d.verificationToken?.token === tokenParam);
    if (targetDoc) {
      // Standalone mode: hide sidebar & topbar, show clean customer view
      document.body.classList.add('portal-standalone');
      navigate('portal');
      loadPortalDoc(targetDoc.id);
      showToast(`Membuka Portal Verifikasi Dokumen ${targetDoc.id}`, 'info', '🔑');
      return true;
    } else {
      showToast('Token verifikasi tidak ditemukan dalam database bank.', 'error');
    }
  }
  return false;
}

function exitStandalonePortal() {
  document.body.classList.remove('portal-standalone');
  window.history.replaceState({}, '', window.location.pathname);
  navigate('dashboard');
  showToast('Kembali ke Dashboard Internal Bank', 'info', '🏢');
}

function initPortal() {
  // Default: load first pending doc with active token
  const pending = DB.documents.find(d => !d.verificationToken?.isUsed);
  if (pending) loadPortalDoc(pending.id);
  else loadPortalDoc(null, DB.documents[0]);
}

function confirmPortal(action) {
  const modalId = action === 'confirm' ? 'modal-confirm' : 'modal-reject';
  openModal(modalId);
}

function executeConfirm(action) {
  const docId = window.currentPortalDocId;
  const doc = DB.documents.find(d => d.id === docId);
  if (!doc) return;

  const now = new Date().toISOString();

  // ATOMIC TOKEN INVALIDATION (Menghanguskan Token Sekali Pakai)
  if (!doc.verificationToken) {
    doc.verificationToken = { token: 'vtok_' + doc.id.toLowerCase() };
  }
  doc.verificationToken.isUsed     = true;
  doc.verificationToken.usedAt     = now;
  doc.verificationToken.usedAction = action;

  doc.status    = action === 'confirm' ? 'confirmed' : 'rejected';
  doc.updatedAt = now;

  const entry = action === 'confirm'
    ? { time: now, action: `Dikonfirmasi via Single-Use Link (${doc.verificationToken.token})`, actor: `${doc.authorizedPerson} (Nasabah)`, icon: '✅', type: 'confirmed' }
    : { time: now, action: `Ditolak via Single-Use Link (${doc.verificationToken.token})`, actor: `${doc.authorizedPerson} (Nasabah)`, icon: '❌', type: 'rejected' };
  doc.auditTrail.push(entry);

  // SAVE TO LOCALSTORAGE: SINKRONISASI REAL-TIME KE DASHBOARD & AKUN SOL
  saveDBToStorage();

  closeModal(action === 'confirm' ? 'modal-confirm' : 'modal-reject');

  // Update Portal UI
  const resultCard = document.getElementById('portal-result');
  resultCard.style.display = 'block';
  if (action === 'confirm') {
    resultCard.innerHTML = `
      <div style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.25);border-radius:var(--radius-lg);padding:28px;text-align:center;animation:fadeIn 0.4s ease">
        <div style="font-size:52px;margin-bottom:12px">✅</div>
        <h3 style="font-size:18px;font-weight:800;color:var(--accent-green);margin-bottom:8px">Konfirmasi Persetujuan Berhasil!</h3>
        <p style="color:var(--text-secondary);font-size:13.5px;max-width:520px;margin:0 auto">
          Terima kasih. Persetujuan Anda sebesar <strong>${formatRupiah(doc.nominal)}</strong> telah direkam secara sah pada ${formatDate(now)}. 
        </p>
        <div style="margin-top:14px;padding:8px 16px;background:rgba(0,0,0,0.2);display:inline-block;border-radius:var(--radius-sm);font-size:11.5px;color:var(--text-muted)">
          🔒 Tautan verifikasi ini otomatis hangus dan tidak dapat digunakan lagi.
        </div>
      </div>
    `;
    showToast('Dokumen berhasil disetujui! Status nasabah terupdate & siap di-review SOL.', 'success', '✅');
  } else {
    resultCard.innerHTML = `
      <div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.25);border-radius:var(--radius-lg);padding:28px;text-align:center;animation:fadeIn 0.4s ease">
        <div style="font-size:52px;margin-bottom:12px">❌</div>
        <h3 style="font-size:18px;font-weight:800;color:var(--accent-red);margin-bottom:8px">Penolakan Transaksi Telah Direkam</h3>
        <p style="color:var(--text-secondary);font-size:13.5px;max-width:520px;margin:0 auto">
          Anda telah menolak transaksi sebesar <strong>${formatRupiah(doc.nominal)}</strong>. Petugas bank akan segera menghubungi Anda.
        </p>
        <div style="margin-top:14px;padding:8px 16px;background:rgba(0,0,0,0.2);display:inline-block;border-radius:var(--radius-sm);font-size:11.5px;color:var(--text-muted)">
          🔒 Tautan verifikasi ini otomatis hangus dan tidak dapat digunakan lagi.
        </div>
      </div>
    `;
    showToast('Dokumen berhasil ditolak. Tautan otomatis hangus.', 'error', '❌');
  }

  // Update token badge
  const tokenBadge = document.getElementById('portal-token-badge');
  tokenBadge.innerHTML = '🔴 Tautan Hangus (Sudah Digunakan)';
  tokenBadge.style.background = 'rgba(239,68,68,0.12)';
  tokenBadge.style.color = 'var(--accent-red)';
  tokenBadge.style.borderColor = 'rgba(239,68,68,0.3)';

  document.getElementById('portal-action-area').style.display = 'none';
  if (currentPage === 'dashboard') renderDashboard();
}

/* ── Portal Doc Selector ── */
function loadPortalFromSelector() {
  const sel = document.getElementById('portal-doc-selector');
  const docId = sel.value;
  if (!docId) return;
  loadPortalDoc(docId);
}

function populatePortalSelector() {
  const sel = document.getElementById('portal-doc-selector');
  if (!sel) return;
  sel.innerHTML = '';
  DB.documents.forEach(doc => {
    const isUsed = doc.verificationToken?.isUsed;
    const opt = document.createElement('option');
    opt.value = doc.id;
    opt.textContent = `${doc.id} — ${doc.customerName} [${isUsed ? '🔒 HANGUS' : '🟢 AKTIF'}] (${formatRupiah(doc.nominal)})`;
    sel.appendChild(opt);
  });
  if (DB.documents.length) sel.value = DB.documents[0].id;
}

/* ── Init ── */
document.addEventListener('DOMContentLoaded', () => {
  // 1. Load saved data from localStorage if available
  loadDBFromStorage();

  // 2. Nav
  document.querySelectorAll('.nav-item[data-page]').forEach(btn => {
    btn.addEventListener('click', () => navigate(btn.dataset.page));
  });

  // 3. Form steps
  document.getElementById('btn-next-1')?.addEventListener('click', nextStep);
  document.getElementById('btn-next-2')?.addEventListener('click', nextStep);
  document.getElementById('btn-back-2')?.addEventListener('click', prevStep);
  document.getElementById('btn-back-3')?.addEventListener('click', prevStep);
  document.getElementById('btn-submit')?.addEventListener('click', submitForm);

  // 4. CIF search
  document.getElementById('btn-search-cif')?.addEventListener('click', searchCIF);
  document.getElementById('cif-input')?.addEventListener('keydown', e => { if (e.key === 'Enter') searchCIF(); });

  // 5. Nominal input formatter
  document.getElementById('nominal-input')?.addEventListener('input', formatNominalInput);

  // 6. File upload
  document.getElementById('doc-file')?.addEventListener('change', handleFileUpload);

  // 7. Drag and drop
  const uploadZone = document.querySelector('.upload-zone');
  if (uploadZone) {
    uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
    uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
    uploadZone.addEventListener('drop', e => {
      e.preventDefault();
      uploadZone.classList.remove('drag-over');
      const file = e.dataTransfer.files[0];
      if (file) {
        const dt = new DataTransfer();
        dt.items.add(file);
        document.getElementById('doc-file').files = dt.files;
        handleFileUpload({ target: document.getElementById('doc-file') });
      }
    });
  }

  // 8. Dashboard filters
  document.getElementById('filter-search')?.addEventListener('input', filterDocs);
  document.getElementById('filter-status')?.addEventListener('change', filterDocs);
  document.getElementById('filter-type')?.addEventListener('change', filterDocs);

  // 9. Live template preview triggers
  document.getElementById('doc-type')?.addEventListener('change', updateTemplatePreview);
  document.getElementById('authorized-person')?.addEventListener('change', updateTemplatePreview);
  document.getElementById('channel')?.addEventListener('change', updateTemplatePreview);

  // 10. Portal actions
  document.getElementById('btn-confirm-portal')?.addEventListener('click', () => confirmPortal('confirm'));
  document.getElementById('btn-reject-portal')?.addEventListener('click',  () => confirmPortal('reject'));
  document.getElementById('btn-do-confirm')?.addEventListener('click', () => executeConfirm('confirm'));
  document.getElementById('btn-do-reject')?.addEventListener('click',  () => executeConfirm('reject'));
  document.getElementById('portal-doc-selector')?.addEventListener('change', loadPortalFromSelector);

  // 11. Close modals on overlay click
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) closeModal(overlay.id);
    });
  });

  // 12. Topbar new doc button
  document.getElementById('btn-new-doc')?.addEventListener('click', () => navigate('initiate'));

  // 13. Render initial views
  setStep(1);
  renderDashboard();
  populatePortalSelector();
  initPortal();

  // 14. Check if opened via verification link (e.g. ?token=vtok_...)
  const isTokenOpened = checkTokenInUrl();
  if (!isTokenOpened) {
    navigate('dashboard');
  }
});

// Explicit window bindings for inline HTML handlers
window.switchRole             = switchRole;
window.openSolApproval        = openSolApproval;
window.submitSolApproval      = submitSolApproval;
window.showSolLockedNotice    = showSolLockedNotice;
window.showAuditTrail         = showAuditTrail;
window.showNotifPreview       = showNotifPreview;
window.showNotifPreviewDirect = showNotifPreviewDirect;
window.copyNotifBody          = copyNotifBody;
window.closeModal             = closeModal;
window.openModal              = openModal;
window.navigate               = navigate;
window.confirmPortal          = confirmPortal;
window.executeConfirm         = executeConfirm;
window.filterDocs             = filterDocs;
window.openPortalForDoc       = openPortalForDoc;
window.copyPortalLink         = copyPortalLink;
window.exitStandalonePortal   = exitStandalonePortal;


