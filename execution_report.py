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
    ink = colors.HexColor('#3C3C3C')
    line = colors.HexColor('#DCE6F3')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('ReportBody', fontName='Helvetica', fontSize=10, leading=15, spaceAfter=8, textColor=ink, splitLongWords=True))
    styles.add(ParagraphStyle('ReportTitle', parent=styles['ReportBody'], fontName='Helvetica-Bold', fontSize=16, leading=21, textColor=blue, spaceAfter=12))
    styles.add(ParagraphStyle('ReportHeading', parent=styles['ReportBody'], fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=blue, spaceBefore=14, spaceAfter=7))
    styles.add(ParagraphStyle('ReportCell', parent=styles['ReportBody'], fontSize=9, leading=13, spaceAfter=0))
    styles.add(ParagraphStyle('ReportLabel', parent=styles['ReportCell'], textColor=grey))
    styles.add(ParagraphStyle('ReportSmall', parent=styles['ReportBody'], fontSize=8, leading=12, textColor=grey, spaceAfter=6))
    styles.add(ParagraphStyle('ReportHeader', parent=styles['ReportCell'], fontName='Helvetica-Bold', textColor=blue))
    def para(text, style='ReportBody'):
        return Paragraph(escape(str(text or '-')).replace('\n', '<br/>'), styles[style])
    def table(rows):
        result = Table([[para(k, 'ReportLabel'), para(v, 'ReportCell')] for k, v in rows], colWidths=[135, 360], hAlign='LEFT')
        result.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F6FF')), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10), ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8), ('LINEBELOW', (0, 0), (-1, -1), .4, line)]))
        return result
    amount = f"Rp {doc['nominal']:,}".replace(',', '.')
    detail = [('Nasabah', doc['customer_name']), ('CIF', doc['cif']), ('Nomor rekening', doc['account']), ('Jabatan', doc['person']), ('Jenis dokumen', doc['kind']), ('Nominal transaksi', amount), ('Rekening tujuan', doc['destination_account'] or 'Belum tercatat'), ('Atas nama rekening tujuan', doc['destination_name'] or 'Belum tercatat')]
    if doc['description']:
        detail.append(('Keterangan', doc['description']))
    story = [para('SURAT KONFIRMASI PELAKSANAAN', 'ReportTitle'), para('Nomor pengajuan: ' + doc['id'], 'ReportSmall'), para('Pengajuan berikut telah dikonfirmasi nasabah dan disetujui SOL.'), para('RINGKASAN TRANSAKSI', 'ReportHeading'), table(detail), para('PERSETUJUAN', 'ReportHeading'), table([('Nasabah', customer['actor'] + '\n' + timestamp(customer['at'])), ('SOL', sol['actor'] + '\n' + timestamp(sol['at']))]), Spacer(1, 14), para('Dokumen ini merupakan bukti persetujuan, bukan bukti transaksi telah dilaksanakan.', 'ReportSmall'), para('Diterbitkan otomatis berdasarkan catatan BRI VISTA.', 'ReportSmall'), PageBreak(), para('RIWAYAT PERNYATAAN DAN PERSETUJUAN', 'ReportTitle')]
    approval_rows = [('Pembuat pengajuan', maker + '\n' + timestamp(doc['created'])), ('Konfirmasi nasabah', customer['actor'] + '\n' + timestamp(customer['at'])), ('Email konfirmasi', doc['email']), ('Pernyataan nasabah', 'Sebagai pihak berwenang, telah memeriksa dan menyetujui surat serta nominal transaksi.'), ('Persetujuan SOL', sol['actor'] + '\n' + timestamp(sol['at']))]
    if sol['notes']:
        approval_rows.append(('Catatan SOL', sol['notes']))
    story.extend([table(approval_rows), para('LOG AKTIVITAS', 'ReportHeading')])
    log_rows = [[para(label, 'ReportHeader') for label in ('Waktu (WIB)', 'Pelaku', 'Aktivitas', 'Catatan')]]
    for entry in audit:
        note = re.sub(r'Versi email \d+', 'Pengiriman email konfirmasi', entry['notes'] or '')
        log_rows.append([para(timestamp(entry['at']).replace(' ', '\n', 1).replace(' WIB', ''), 'ReportCell'), para(entry['actor'], 'ReportCell'), para(entry['action'], 'ReportCell'), para(note, 'ReportCell')])
    log = Table(log_rows, colWidths=[83, 92, 155, 165], repeatRows=1, hAlign='LEFT')
    log.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F6FF')), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8), ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8), ('LINEBELOW', (0, 0), (-1, -1), .4, line)]))
    story.append(log)
    if reader is None:
        story.extend([PageBreak(), para('LAMPIRAN SURAT TRANSAKSI', 'ReportTitle'), para(version['filename'], 'ReportSmall')])
        width, height = image_size
        scale = min(495 / width, 580 / height)
        story.append(Image(BytesIO(original), width=width * scale, height=height * scale))
    output = BytesIO()
    def footer(canvas, document):
        canvas.saveState()
        canvas.setFillColor(blue)
        canvas.setFont('Helvetica-Bold', 12)
        canvas.drawString(50, 801, 'BRI VISTA')
        canvas.setFillColor(grey)
        canvas.setFont('Helvetica', 9)
        canvas.drawRightString(545, 801, 'BRI Jakarta Sudirman 1')
        canvas.setStrokeColor(line)
        canvas.line(50, 788, 545, 788)
        canvas.line(50, 40, 545, 40)
        canvas.setFont('Helvetica', 8)
        canvas.drawString(50, 27, doc['id'])
        canvas.drawRightString(545, 27, 'Halaman ' + str(document.page))
        canvas.restoreState()
    SimpleDocTemplate(output, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=75, bottomMargin=58, title='Konfirmasi Pelaksanaan - ' + doc['id'], author='BRI VISTA').build(story, onFirstPage=footer, onLaterPages=footer)
    writer = PdfWriter()
    writer.append(BytesIO(output.getvalue()), import_outline=False)
    if reader is not None:
        writer.append(reader, outline_item='Dokumen SI yang diunggah', import_outline=False, excluded_fields=['/Annots'])
    writer.add_attachment(version['filename'], original)
    writer.add_metadata({'/Title': 'Konfirmasi Pelaksanaan - ' + doc['id'], '/Author': 'BRI VISTA'})
    combined = BytesIO()
    writer.write(combined)
    return combined.getvalue()
