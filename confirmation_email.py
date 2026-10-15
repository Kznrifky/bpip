"""Customer-facing verification copy and email-safe, escaped HTML."""
import html
import re
from datetime import datetime, timezone, timedelta

MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des')
SIGNATURE = 'BRI Jakarta Sudirman 1'
INTRO = 'Mohon Bapak/Ibu memverifikasi dokumen dan rincian transaksi berikut sebelum memberikan persetujuan.'


def expiry_label(expires):
    stamp = datetime.fromtimestamp(expires, timezone(timedelta(hours=7)))
    return f'{stamp.day} {MONTHS[stamp.month - 1]} {stamp.year} pukul {stamp:%H.%M} WIB'


def confirmation_body(doc, link, expires, ttl_hours=24):
    amount = f"Rp {doc['nominal']:,}".replace(',', '.')
    values = {key: ' '.join(str(doc[key] or 'Belum tercatat').splitlines()) for key in ('customer_name', 'id', 'kind', 'destination_account', 'destination_name')}
    position = doc['person'] if 'person' in doc.keys() else None
    role = ' '.join(str(position or 'Bapak/Ibu').split())
    role = role[:1].upper() + role[1:]
    verifier_name = ' '.join(str(doc.get('verifier_name', '')).split()) if isinstance(doc, dict) else ''
    greeting = f"Yth. {verifier_name} ({role} {values['customer_name']})," if verifier_name else f"Yth. {role} {values['customer_name']},"
    return f"""{greeting}

{INTRO}

Nasabah: {values['customer_name']}
Nominal transaksi: {amount}
Nomor pengajuan: {values['id']}
Jenis dokumen: {values['kind']}
Rekening tujuan: {values['destination_account']}
Nama Rekening Tujuan: {values['destination_name']}

Verifikasi Transaksi:
{link}

Berlaku hingga: {expiry_label(expires)}

Informasi keamanan:
- Link verifikasi berlaku selama {ttl_hours} jam sejak pengajuan dikirim.
- Link verifikasi hanya dapat digunakan satu kali untuk memberikan keputusan.
- Membuka link verifikasi tidak secara otomatis memberikan persetujuan.
- Jaga kerahasiaan link verifikasi ini dan jangan membagikannya kepada pihak lain.

Jika Anda tidak mengenali pengajuan ini atau memerlukan bantuan, hubungi petugas melalui kontak resmi. BRI VISTA tidak meminta kata sandi, PIN, atau OTP melalui email.

Terima kasih atas perhatian dan konfirmasi Anda.

Hormat kami,
{SIGNATURE}
"""


def render_confirmation_html(body, base_url, logo_cid=None):
    """Recognize current and legacy outbox bodies; never link arbitrary content."""
    escape = lambda value: html.escape(str(value), quote=True)
    link_pattern = re.compile(re.escape(base_url.rstrip('/')) + r'/#confirm/[A-Za-z0-9_-]+')
    paragraphs = body.strip().split('\n\n')
    link = next((line for line in body.splitlines() if link_pattern.fullmatch(line)), '')
    fields = []
    for paragraph in paragraphs:
        if paragraph.startswith('Nasabah: ') and all(': ' in line for line in paragraph.splitlines()):
            fields = [line.split(': ', 1) for line in paragraph.splitlines()]
            break
    greeting = paragraphs[0] if paragraphs and paragraphs[0].startswith('Yth.') else 'Yth. Bapak/Ibu,'
    security_points = next(([line.removeprefix('- ') for line in paragraph.splitlines()[1:] if line.startswith('- ')] for paragraph in paragraphs if paragraph.startswith('Informasi keamanan:')), [])
    if not security_points:
        security_points = ['Link verifikasi hanya dapat digunakan satu kali untuk memberikan keputusan.', 'Membuka link verifikasi tidak secara otomatis memberikan persetujuan.', 'Jaga kerahasiaan link verifikasi ini dan jangan membagikannya kepada pihak lain.']
    signature = next((paragraph.split('\n', 1)[1] for paragraph in paragraphs if paragraph.startswith('Hormat kami,\n')), SIGNATURE)
    branding = (f'<img src="cid:{escape(logo_cid)}" width="252" height="88" alt="BRI VISTA — Verification, Integration &amp; Secure Tracking Application" style="display:block;width:252px;max-width:100%;height:auto;border:0">'
                if logo_cid else '<strong style="display:block;font-size:26px;line-height:32px;color:#0756bd">BRI VISTA</strong><span style="display:block;font-size:11px;line-height:17px;color:#657895">Verification, Integration &amp; Secure Tracking Application</span>')
    rows = []
    for label, value in sorted(fields, key=lambda field: {'nasabah': 0, 'nominal transaksi': 1}.get(field[0].lower(), 2)):
        if label.lower() == 'status':
            continue
        label = 'Nama Rekening Tujuan' if label.lower() == 'atas nama rekening tujuan' else label
        rows.append(f'<tr><td class="summary-label" valign="top" width="38%" style="padding:11px 14px;border-top:1px solid #e3edf9;font-size:13px;line-height:20px;color:#657895">{escape(label)}</td><td class="summary-value" valign="top" style="padding:11px 14px;border-top:1px solid #e3edf9;font-size:14px;line-height:20px;font-weight:600;color:#142c52;word-break:break-word">{escape(value)}</td></tr>')
    if fields:
        summary = '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #dce7f5;border-radius:10px;border-spacing:0;background:#f8fbff;margin:20px 0 24px"><tr><td colspan="2" bgcolor="#0756bd" style="padding:13px 14px;background:#0756bd;border-radius:9px 9px 0 0;color:#fff;font-size:15px;font-weight:700;line-height:22px">Rincian Transaksi</td></tr>'
        summary += ''.join(rows) + '</table>'
        intro = INTRO
    else:
        # Preserve custom or older unstructured content, fully escaped.
        remaining = [paragraph for paragraph in paragraphs if paragraph != greeting and not any(link_pattern.fullmatch(line) for line in paragraph.splitlines())]
        summary = ''.join(f'<p style="margin:16px 0;line-height:22px">{escape(paragraph).replace(chr(10), "<br>")}</p>' for paragraph in remaining)
        intro = 'Periksa dokumen dan data transaksi sebelum memberikan konfirmasi.'
    action = ''
    if link:
        safe_link = escape(link)
        action = f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" bgcolor="#166534" style="border-radius:8px;background:#166534"><a href="{safe_link}" style="display:block;border:1px solid #166534;border-radius:8px;padding:14px 18px;color:#fff;background:#166534;font-size:16px;line-height:22px;font-weight:700;text-decoration:none;text-align:center;mso-padding-alt:0">Verifikasi Transaksi</a></td></tr></table>'''
    legacy_points = {
        'Tautan hanya dapat digunakan untuk satu keputusan.': 'Link verifikasi hanya dapat digunakan satu kali untuk memberikan keputusan.',
        'Membuka tautan tidak berarti Anda memberikan persetujuan.': 'Membuka link verifikasi tidak secara otomatis memberikan persetujuan.',
        'Jangan membagikan tautan ini kepada pihak lain.': 'Jaga kerahasiaan link verifikasi ini dan jangan membagikannya kepada pihak lain.',
    }
    security_items = []
    for point in security_points:
        point = legacy_points.get(point, point)
        point = re.sub(r'^Tautan berlaku (\d+) jam sejak pengajuan dikirim\.$', r'Link verifikasi berlaku selama \1 jam sejak pengajuan dikirim.', point)
        formatted = escape(point)
        formatted = re.sub(r'(?<=selama )(\d+ jam)', r'<strong>\1</strong>', formatted, count=1)
        for phrase in ('satu kali untuk memberikan keputusan', 'tidak secara otomatis memberikan persetujuan', 'jangan membagikannya kepada pihak lain'):
            formatted = formatted.replace(phrase, '<strong>' + phrase + '</strong>')
        security_items.append(f'<li style="margin:0 0 10px;padding-left:2px">{formatted}</li>')
    security_items = ''.join(security_items)
    return f'''<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>Verifikasi Transaksi — BRI VISTA</title><style>@media only screen and (max-width:520px){{.email-outer{{padding:16px 8px!important}}.email-content{{padding:22px 18px!important}}.email-brand{{padding:16px 18px!important}}.summary-label,.summary-value{{display:block!important;width:auto!important;padding:7px 14px!important}}.summary-value{{border-top:0!important;padding-top:0!important;padding-bottom:12px!important}}}}</style></head>
<body style="margin:0;padding:0;background:#f2f7fe;color:#142c52;font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:22px">
<div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all">Tinjau dokumen dan konfirmasikan transaksi Anda melalui BRI VISTA.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#f2f7fe"><tr><td class="email-outer" align="center" style="padding:28px 12px">
<!--[if mso]><table role="presentation" width="600" align="center"><tr><td><![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#ffffff" style="max-width:600px;border:1px solid #dce7f5;border-radius:12px;background:#fff;border-spacing:0">
<tr><td class="email-brand" style="padding:16px 26px">{branding}</td></tr>
<tr><td bgcolor="#0756bd" style="padding:19px 26px;background:#0756bd;color:#fff"><h1 style="margin:0;color:#fff;font-size:24px;line-height:32px;font-weight:700">Verifikasi Transaksi</h1></td></tr>
<tr><td class="email-content" style="padding:26px"><p style="margin:0 0 12px;font-size:14px;line-height:22px">{escape(greeting).replace(chr(10), '<br>')}</p><p style="margin:0;font-size:14px;line-height:22px;color:#334c6b">{intro}</p>{summary}{action}
<table class="email-security" role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#edf5ff" style="margin-top:24px;background:#edf5ff;border:1px solid #dce7f5;border-radius:10px"><tr><td style="padding:20px;font-size:14px;line-height:23px;color:#334c6b"><h2 style="margin:0 0 14px;font-size:18px;line-height:26px;color:#0756bd">Informasi keamanan</h2><ul style="margin:0 0 22px;padding-left:21px">{security_items}</ul>
<p style="margin:0 0 22px;font-size:14px;line-height:23px">Jika Anda tidak mengenali pengajuan ini atau memerlukan bantuan, hubungi petugas melalui kontak resmi. BRI VISTA tidak meminta kata sandi, PIN, atau OTP melalui email.</p>
<p style="margin:0 0 22px;font-size:14px;line-height:23px">Terima kasih atas perhatian dan konfirmasi Anda.</p>
<p style="margin:0;font-size:14px;line-height:23px">Hormat kami,<br>{escape(signature).replace(chr(10), '<br>')}</p></td></tr></table>
<p style="margin:22px 0 0;padding-top:20px;border-top:1px solid #dce7f5;text-align:center;font-size:13px;line-height:21px;color:#657895">BRI VISTA<br>Verification, Integration &amp; Secure Tracking Application</p>
</td></tr>
</table><!--[if mso]></td></tr></table><![endif]-->
</td></tr></table></body></html>'''
