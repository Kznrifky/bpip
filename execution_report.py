"""Authenticated approval dossier; original upload remains attached byte for byte."""
from io import BytesIO
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape
from PIL import Image as PillowImage

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, Flowable


class ReportError(ValueError):
    pass


def report_image(original):
    """Bound the raster rendered on A4; keep the untouched upload as attachment."""
    try:
        with PillowImage.open(BytesIO(original)) as source:
            if source.width * source.height > 64_000_000:
                raise ReportError('Resolusi gambar terlalu besar untuk PDF pelaksanaan. Hubungi pengelola aplikasi.')
            # JPEG can decode at reduced resolution. PNG is reduced before
            # ReportLab expands it into multiple full-size RGB buffers.
            source.draft('RGB', (1240, 1754))
            scale = min(1240 / source.width, 1754 / source.height, 1)
            target_size = (max(1, round(source.width * scale)), max(1, round(source.height * scale)))
            # Process narrow strips so RGBA premultiplication never creates a
            # second full-size 200+ MB image. The original remains attached.
            with PillowImage.new('RGB', target_size, 'white') as preview:
                strip_height = max(1, 1_000_000 // source.width)
                for top in range(0, source.height, strip_height):
                    bottom = min(source.height, top + strip_height)
                    y0, y1 = round(top * target_size[1] / source.height), round(bottom * target_size[1] / source.height)
                    if y1 <= y0:
                        continue
                    with source.crop((0, top, source.width, bottom)) as strip:
                        with strip.convert('RGBA') as rgba:
                            with rgba.resize((target_size[0], y1-y0), PillowImage.Resampling.LANCZOS) as resized:
                                preview.paste(resized, (0, y0), resized.getchannel('A'))
                output = BytesIO()
                preview.save(output, format='JPEG', quality=90)
                return output.getvalue(), preview.size
    except ReportError:
        raise
    except Exception as exc:
        raise ReportError('Gambar surat tidak dapat dibaca. Hubungi pengelola aplikasi.') from exc


def timestamp(value):
    if not value:
        return 'Tidak tercatat'
    return datetime.fromisoformat(value).astimezone(ZoneInfo('Asia/Jakarta')).strftime('%d/%m/%Y %H:%M:%S WIB')


def build_execution_report(doc, version, audit, maker):
    if doc['sol_status'] != 'approved' or doc['customer_status'] != 'confirmed':
        raise ReportError('PDF tersedia setelah nasabah dan AMOL menyetujui pengajuan.')
    audit = [{**entry, 'action': re.sub(r'\bSOL\b', 'AMOL', entry['action']), 'actor': entry['actor'].replace(' (SOL)', ' (AMOL)')} for entry in audit]
    maker = next((a['actor'] for a in audit if a['action'] == 'Pengajuan dikirim untuk konfirmasi nasabah'), maker)
    approvals = [a for a in audit if a['version'] == doc['version']]
    customer = next((a for a in reversed(approvals) if a['action'] == 'Nasabah menyetujui surat'), None)
    sol = next((a for a in reversed(approvals) if a['action'] == 'AMOL menyetujui pengajuan'), None)
    if not customer or not sol:
        raise ReportError('Catatan persetujuan belum lengkap. Hubungi pengelola aplikasi.')
    verifiers = doc.get('verifiers', [])
    if doc.get('verifier_config') and (len(verifiers) != 2 or any(v['status'] != 'confirmed' for v in verifiers)):
        raise ReportError('Persetujuan kedua verifikator belum lengkap.')
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
        image_preview, image_size = report_image(original)

    blue = colors.HexColor('#0756BD')
    grey = colors.HexColor('#657895')
    ink = colors.HexColor('#142C52')
    line = colors.HexColor('#DCE7F5')
    pale = colors.HexColor('#F6F9FF')
    green = colors.HexColor('#166534')
    width, inner, gap = 495, 475, 10
    styles = getSampleStyleSheet()
    for name, size, leading, color, bold in (
        ('ReportBody',9,13,ink,False), ('ReportTitle',16,20,ink,True),
        ('ReportLabel',8,11,grey,False), ('ReportValue',9.5,13,ink,True),
        ('ReportSmall',7.5,10.5,grey,False), ('ReportHeader',8,11,blue,True),
        ('ReportPanelTitle',10,14,ink,True), ('ReportApproved',8,11,green,True),
    ):
        styles.add(ParagraphStyle(name,fontName='Helvetica-Bold' if bold else 'Helvetica',fontSize=size,leading=leading,textColor=color,spaceAfter=0,splitLongWords=True))
    def para(text, style='ReportBody'):
        return Paragraph(escape(str(text or 'Belum tercatat')).replace('\n','<br/>'),styles[style])

    class Symbol(Flowable):
        def __init__(self, kind, size=24):
            Flowable.__init__(self); self.kind=kind; self.width=self.height=size
        def draw(self):
            c=self.canv; c.saveState(); c.setFillColor(colors.HexColor('#E7F1FF')); c.roundRect(0,0,self.width,self.height,6,stroke=0,fill=1)
            c.translate(self.width/2,self.height/2); c.setStrokeColor(blue); c.setLineWidth(1)
            if self.kind=='person':
                c.circle(0,3,3,stroke=1,fill=0); path=c.beginPath(); path.moveTo(-6,-7); path.curveTo(-6,2,6,2,6,-7); c.drawPath(path)
            elif self.kind=='payment':
                c.roundRect(-7,-5,14,10,1,stroke=1,fill=0); c.line(-7,1,7,1); c.line(-4,-2,0,-2)
            elif self.kind=='calendar':
                c.roundRect(-6,-6,12,12,1,stroke=1,fill=0); c.line(-6,2,6,2); c.line(-3,8,-3,4); c.line(3,8,3,4)
            elif self.kind=='briefcase':
                c.roundRect(-7,-5,14,10,1,stroke=1,fill=0); c.rect(-3,5,6,3,stroke=1,fill=0); c.line(-7,0,7,0)
            elif self.kind=='mail':
                c.roundRect(-7,-5,14,10,1,stroke=1,fill=0); c.line(-7,5,0,0); c.line(0,0,7,5)
            elif self.kind=='identity':
                c.roundRect(-7,-5,14,10,1,stroke=1,fill=0); c.circle(-3,1,1.5,stroke=1,fill=0); c.line(-5,-2,-1,-2); c.line(1,2,5,2); c.line(1,-1,5,-1)
            elif self.kind=='phone':
                path=c.beginPath(); path.moveTo(-4,7); path.lineTo(-7,4); path.curveTo(-7,-1,1,-7,5,-6); path.lineTo(7,-3); path.lineTo(3,0); path.lineTo(1,-2); path.lineTo(-3,2); path.lineTo(-1,4); path.close(); c.drawPath(path)
            elif self.kind=='info':
                c.circle(0,0,7,stroke=1,fill=0); c.line(0,-4,0,1); c.circle(0,4,.6,stroke=1,fill=0)
            elif self.kind=='check':
                c.setStrokeColor(green); path=c.beginPath(); path.moveTo(-5,0); path.lineTo(-1,-4); path.lineTo(6,5); c.drawPath(path)
            else:
                c.roundRect(-5,-7,10,14,1,stroke=1,fill=0); c.line(-2,2,2,2); c.line(-2,-2,2,-2)
            c.restoreState()

    class SectionHeader(Flowable):
        def __init__(self,title,symbol):
            Flowable.__init__(self); self.width=width; self.height=36; self.title=title; self.symbol=symbol
        def draw(self):
            c=self.canv; c.saveState(); c.setFillColor(blue); c.rect(0,0,width,36,fill=1,stroke=0)
            c.setFillColor(colors.HexColor('#376FC0')); c.circle(26,18,12,fill=1,stroke=0)
            c.setFillColor(colors.white); c.setFont('Helvetica-Bold',11); c.drawString(46,14,self.title)
            c.setStrokeColor(colors.white); c.setLineWidth(1.1)
            if self.symbol=='person':
                c.circle(26,21,3,fill=0,stroke=1); path=c.beginPath(); path.moveTo(20,11); path.curveTo(20,19,32,19,32,11); c.drawPath(path)
            else:
                c.roundRect(22,11,8,14,1,fill=0,stroke=1); c.line(24,21,28,21); c.line(24,17,28,17)
            c.restoreState()

    def box(label,value,symbol,box_width,height=None):
        item=Table([[Symbol(symbol),[para(label,'ReportLabel'),Spacer(1,3),para(value,'ReportValue')]]],colWidths=[32,box_width-32],rowHeights=[height] if height else None,hAlign='LEFT',splitInRow=1,cornerRadii=[6,6,6,6])
        item.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),pale),('BOX',(0,0),(-1,-1),.5,line),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(0,-1),0),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        if height:
            item.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP')]))
        return item
    def row(items,row_width=inner,equal_height=False):
        cell_width=(row_width-gap*(len(items)-1))/len(items)
        height=max(box(*item,cell_width).wrap(cell_width,10000)[1] for item in items) if equal_height else None
        cells=[]; widths=[]
        for index,item in enumerate(items):
            if index: cells.append(''); widths.append(gap)
            cells.append(box(*item,cell_width,height=height)); widths.append(cell_width)
        result=Table([cells],colWidths=widths,hAlign='LEFT',splitInRow=1)
        result.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
        return result
    def card(title,content,symbol='file'):
        result=Table([[SectionHeader(title,symbol)],[content]],colWidths=[width],hAlign='LEFT',repeatRows=1,splitInRow=1,cornerRadii=[8,8,8,8])
        result.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),blue),('BACKGROUND',(0,1),(-1,-1),colors.white),('BOX',(0,0),(-1,-1),.6,line),('LEFTPADDING',(0,0),(-1,0),0),('RIGHTPADDING',(0,0),(-1,0),0),('TOPPADDING',(0,0),(-1,0),0),('BOTTOMPADDING',(0,0),(-1,0),0),('LEFTPADDING',(0,1),(-1,-1),10),('RIGHTPADDING',(0,1),(-1,-1),10),('TOPPADDING',(0,1),(-1,-1),10),('BOTTOMPADDING',(0,1),(-1,-1),10)]))
        return result
    identities=verifiers or [dict(position=1,name=re.sub(r' \(Nasabah\)$','',customer['actor']),person=doc['person'],email=doc['email'],phone='',used_at=customer['at'])]
    def verifier_panel(verifier,panel_width):
        title='Verifikator '+str(verifier['position']) if len(identities)>1 else 'Verifikator'
        content=[para(title,'ReportPanelTitle'),Spacer(1,7)]
        for label,value,symbol in [('Nama Verifikator',verifier['name'],'person'),('Jabatan Verifikator',verifier['person'],'briefcase'),('Nomor HP',verifier.get('phone',''),'phone'),('Email Verifikator',verifier['email'],'mail')]:
            content.extend([box(label,value,symbol,panel_width-16),Spacer(1,5)])
        panel=Table([[content]],colWidths=[panel_width],hAlign='LEFT',splitInRow=1,cornerRadii=[6,6,6,6])
        panel.setStyle(TableStyle([('BOX',(0,0),(-1,-1),.5,line),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
        return panel
    panel_width=(inner-gap*(len(identities)-1))/len(identities)
    panel_cells=[];panel_widths=[]
    for index,verifier in enumerate(identities):
        if index: panel_cells.append('');panel_widths.append(gap)
        panel_cells.append(verifier_panel(verifier,panel_width));panel_widths.append(panel_width)
    panels=Table([panel_cells],colWidths=panel_widths,hAlign='LEFT',splitInRow=1)
    panels.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    overview=[row([('Nama nasabah',doc['customer_name'],'person')]),Spacer(1,7),row([('CIF',doc['cif'],'identity'),('Nomor rekening',doc['account'],'payment')]),Spacer(1,12),panels]
    amount=f"Rp {doc['nominal']:,}".replace(',','.')
    transaction=[row([('Nominal transaksi',amount,'payment'),('Nama Rekening Tujuan',doc['destination_name'],'person')]),Spacer(1,7),row([('Bank Rekening Tujuan',doc.get('destination_bank'),'payment'),('Rekening tujuan',doc['destination_account'],'payment')]),Spacer(1,7),row([('Keterangan',doc['description'] or '-', 'info')])]
    approval_content=[]
    for verifier in identities:
        title='Verifikator '+str(verifier['position']) if len(identities)>1 else 'Verifikator'
        approval_content.extend([row([(title,verifier['name'],'person'),('Disetujui',timestamp(verifier['used_at']),'check')]),Spacer(1,6)])
    approval_content.extend([row([('AMOL',sol['actor'],'person'),('Disetujui',timestamp(sol['at']),'check')]),Spacer(1,8),para('Sebagai pihak berwenang, verifikator telah memeriksa dan menyetujui surat serta nominal transaksi.','ReportSmall')])
    if sol['notes']: approval_content.extend([Spacer(1,6),para('Catatan AMOL: '+sol['notes'],'ReportSmall')])
    log_rows=[[para(label,'ReportHeader') for label in ('Waktu (WIB)','Pelaku','Aktivitas','Catatan')]]
    for entry in audit:
        note=re.sub(r'Versi email \d+','Pengiriman email konfirmasi',entry['notes'] or '')
        log_rows.append([para(timestamp(entry['at']).replace(' ', '\n',1).replace(' WIB',''),'ReportSmall'),para(entry['actor'],'ReportSmall'),para(entry['action'],'ReportSmall'),para(note or '-','ReportSmall')])
    log=Table(log_rows,colWidths=[76,89,143,167],repeatRows=1,hAlign='LEFT',splitInRow=1)
    log.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),pale),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,-1),.4,line)]))
    story=[para('SURAT KONFIRMASI PELAKSANAAN','ReportTitle'),Spacer(1,5),para(doc['customer_name'],'ReportPanelTitle'),Spacer(1,6),para('Pengajuan telah dikonfirmasi seluruh verifikator dan disetujui AMOL.','ReportSmall'),Spacer(1,16),card('Informasi Pengajuan',[row([('Nomor SI',doc['id'],'file'),('Dibuat pada',timestamp(doc['created']),'calendar'),('Jenis dokumen',doc['kind'],'file')],equal_height=True)]),Spacer(1,14),card('Data Nasabah',overview,'person'),Spacer(1,12),para('Dokumen ini merupakan bukti persetujuan, bukan bukti transaksi telah dilaksanakan.','ReportSmall'),PageBreak(),card('Informasi Transaksi',transaction),Spacer(1,14),card('RIWAYAT PERNYATAAN DAN PERSETUJUAN',approval_content),Spacer(1,14),card('LOG AKTIVITAS',[para('Pembuat pengajuan: '+maker,'ReportSmall'),Spacer(1,8),log])]
    if reader is None:
        story.extend([PageBreak(),para('LAMPIRAN SURAT TRANSAKSI','ReportTitle'),Spacer(1,12),para(version['filename'],'ReportSmall'),Spacer(1,14)])
        image_width,image_height=image_size
        scale=min(width/image_width,580/image_height)
        story.append(Image(BytesIO(image_preview),width=image_width*scale,height=image_height*scale))
    output = BytesIO()
    def footer(canvas, document):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor('#F2F7FF'))
        canvas.rect(0,45,A4[0],A4[1]-45,fill=1,stroke=0)
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
        writer.append(reader, outline_item='Dokumen SI yang diunggah', import_outline=False, excluded_fields=['/Annots', '/B'])
    writer.add_attachment(version['filename'], original)
    writer.add_metadata({'/Title': 'Konfirmasi Pelaksanaan - ' + doc['id'], '/Author': 'BRI VISTA'})
    combined = BytesIO()
    writer.write(combined)
    return combined.getvalue()
