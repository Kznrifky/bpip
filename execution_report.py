"""Authenticated approval dossier; original upload remains attached byte for byte."""
from io import BytesIO
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image


class ReportError(ValueError):
    pass


def timestamp(value):
    if not value:
        return 'Tidak tercatat'
    return datetime.fromisoformat(value).astimezone(ZoneInfo('Asia/Jakarta')).strftime('%d/%m/%Y %H:%M:%S WIB')


def build_execution_report(doc, version, audit, maker):
    if doc['sol_status'] != 'approved' or doc['customer_status'] != 'confirmed':
        raise ReportError('PDF tersedia setelah nasabah dan SOL menyetujui pengajuan.')
    maker = next((a['actor'] for a in audit if a['action'] == 'Pengajuan dikirim untuk konfirmasi nasabah'), maker)
    approvals = [a for a in audit if a['version'] == doc['version']]
    customer = next((a for a in reversed(approvals) if a['action'] == 'Nasabah menyetujui surat'), None)
    sol = next((a for a in reversed(approvals) if a['action'] == 'SOL menyetujui pengajuan'), None)
    if not customer or not sol:
        raise ReportError('Catatan persetujuan belum lengkap. Hubungi pengelola aplikasi.')
    original = bytes(version['content'])
    reader = None
    if version['mime'] == 'application/pdf':
        try:
            reader = PdfReader(BytesIO(original))
            if reader.is_encrypted or not len(reader.pages):
                raise ValueError('Encrypted or empty PDF')
        except Exception as exc:
            raise ReportError('Dokumen unggahan tidak dapat digabungkan. Gunakan PDF yang valid tanpa kata sandi.') from exc
    else:
        try:
            image_size = ImageReader(BytesIO(original)).getSize()
        except Exception as exc:
            raise ReportError('Gambar surat tidak dapat dibaca. Hubungi pengelola aplikasi.') from exc

    blue = colors.HexColor('#0857C3')
    grey = colors.HexColor('#5B7188')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('ReportBody', fontName='Helvetica', fontSize=10, leading=15, spaceAfter=10, textColor=colors.HexColor('#3C3C3C'), splitLongWords=True))
    styles.add(ParagraphStyle('ReportTitle', parent=styles['ReportBody'], fontName='Helvetica-Bold', fontSize=17, leading=23, textColor=blue, spaceAfter=16))
    styles.add(ParagraphStyle('ReportSmall', parent=styles['ReportBody'], fontSize=8, leading=12, textColor=grey))
    def para(text, style='ReportBody'):
        return Paragraph(escape(str(text or '-')).replace('\n', '<br/>'), styles[style])
    def table(rows):
        result = Table([[para(k), para(v)] for k, v in rows], colWidths=[135, 360], hAlign='LEFT')
        result.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0F6FF')), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 12), ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 4), ('LINEBELOW', (0, 0), (-1, -1), .4, colors.HexColor('#DCE6F3'))]))
        return result
    amount = f"Rp {doc['nominal']:,}".replace(',', '.')
    story = [para('BRI VISTA - Verification, Integration & Secure Tracking Application', 'ReportSmall'), para('SURAT KONFIRMASI PELAKSANAAN', 'ReportTitle'), para('Nomor pengajuan: ' + doc['id'], 'ReportSmall'), para('Berdasarkan konfirmasi nasabah dan persetujuan SOL yang tercatat pada BRI VISTA, pengajuan berikut telah disetujui untuk pelaksanaan sesuai surat yang dilampirkan.'), table([('Nasabah', doc['customer_name']), ('CIF', doc['cif']), ('Nomor rekening', doc['account']), ('Jabatan', doc['person']), ('Jenis dokumen', doc['kind']), ('Nominal transaksi', amount), ('Keterangan transaksi', doc['description'] or 'Tidak ada keterangan tambahan'), ('Persetujuan SOL', timestamp(sol['at']))]), Spacer(1, 18), para('Konfirmasi nasabah diterima melalui tautan pribadi yang dikirim ke ' + doc['email'] + '. SOL telah menyetujui pengajuan ini setelah konfirmasi nasabah tercatat.'), para('Dokumen ini mengonfirmasi selesainya tahapan persetujuan. Pelaksanaan transaksi tetap mengikuti prosedur operasional yang berlaku dan perlu dicatat secara terpisah.'), para('Diterbitkan secara otomatis oleh BRI VISTA berdasarkan catatan sistem; tidak memuat tanda tangan basah atau tanda tangan digital tersertifikasi.', 'ReportSmall'), PageBreak(), para('RIWAYAT PERNYATAAN DAN PERSETUJUAN', 'ReportTitle'), table([('Pembuat pengajuan', maker), ('Dibuat pada', timestamp(doc['created'])), ('Konfirmasi nasabah', customer['actor']), ('Email penerima tautan', doc['email']), ('Waktu konfirmasi', timestamp(customer['at'])), ('Pernyataan nasabah', 'Menyatakan sebagai pihak berwenang dan telah memeriksa surat, detail transaksi, serta nominal sebelum memilih Setujui.'), ('Persetujuan SOL', sol['actor']), ('Waktu persetujuan SOL', timestamp(sol['at'])), ('Catatan SOL', sol['notes'] or 'Tidak ada catatan tambahan')]), Spacer(1, 16), para('Identitas pihak nasabah dicatat sesuai data pihak berwenang pada pengajuan dan konfirmasi melalui tautan pribadi. Tautan rahasia tidak dicantumkan dalam PDF.', 'ReportSmall'), para('LOG AKTIVITAS', 'ReportTitle')]
    for entry in audit:
        story.extend([para(entry['action']), para(timestamp(entry['at']) + ' | ' + entry['actor'], 'ReportSmall')])
        if entry['notes']:
            story.append(para(re.sub(r'Versi email \d+', 'Pengiriman email konfirmasi', entry['notes']), 'ReportSmall'))
        story.append(Spacer(1, 7))
    story.extend([PageBreak(), para('DOKUMEN SI / SURAT TRANSAKSI', 'ReportTitle'), para('Dokumen berikut adalah surat yang dikonfirmasi nasabah dan disetujui SOL.'), table([('Nama file', version['filename']), ('SHA-256', version['sha256'])]), Spacer(1, 16), para('File asli juga disertakan sebagai lampiran di dalam PDF untuk menjaga keutuhan dokumen unggahan.', 'ReportSmall')])
    if reader is None:
        width, height = image_size
        scale = min(495 / width, 490 / height)
        story.append(Image(BytesIO(original), width=width * scale, height=height * scale))
    output = BytesIO()
    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(blue)
        canvas.line(50, 40, 545, 40)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(grey)
        canvas.drawString(50, 27, 'BRI VISTA | ' + doc['id'])
        canvas.drawRightString(545, 27, str(document.page))
        canvas.restoreState()
    SimpleDocTemplate(output, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=45, bottomMargin=58, title='Konfirmasi Pelaksanaan - ' + doc['id'], author='BRI VISTA').build(story, onFirstPage=footer, onLaterPages=footer)
    writer = PdfWriter()
    writer.append(BytesIO(output.getvalue()), import_outline=False)
    if reader is not None:
        writer.append(reader, outline_item='Dokumen SI yang diunggah', import_outline=False, excluded_fields=['/Annots'])
    writer.add_attachment(version['filename'], original)
    writer.add_metadata({'/Title': 'Konfirmasi Pelaksanaan - ' + doc['id'], '/Author': 'BRI VISTA'})
    combined = BytesIO()
    writer.write(combined)
    return combined.getvalue()
