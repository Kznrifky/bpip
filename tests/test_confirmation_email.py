import unittest
from datetime import datetime, timezone
from html.parser import HTMLParser
from confirmation_email import confirmation_body, expiry_label, render_confirmation_html


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.append(dict(attrs).get('href'))


class ConfirmationEmailTests(unittest.TestCase):
    def setUp(self):
        self.doc = {'id': 'SI-2026-DEMO', 'customer_name': 'PT Contoh & Mitra', 'kind': 'Standing Instruction', 'nominal': 12500000, 'destination_account': '000123456789012', 'destination_name': 'PT Penerima <Contoh>'}
        self.link = 'https://bpip.example.test/#confirm/example_private_token'
        self.expires = datetime(2026, 10, 13, 18, 15, tzinfo=timezone.utc).timestamp()

    def test_exact_expiry_uses_wib_and_preserves_account_and_link(self):
        body = confirmation_body(self.doc, self.link, self.expires)
        self.assertEqual(expiry_label(self.expires), '14 Okt 2026 pukul 01.15 WIB')
        self.assertIn(self.link, body.splitlines())
        self.assertIn('Rekening tujuan: 000123456789012', body)
        html = render_confirmation_html(body, 'https://bpip.example.test', 'brand-logo')
        self.assertIn('14 Okt 2026 pukul 01.15 WIB', body)
        self.assertIn('Link verifikasi berlaku selama 24 jam sejak pengajuan dikirim.', body)
        self.assertIn('000123456789012', html)
        self.assertIn('PT Contoh &amp; Mitra', html)
        self.assertIn('PT Penerima &lt;Contoh&gt;', html)
        links = Links(); links.feed(html)
        self.assertEqual(links.hrefs, [self.link])

    def test_security_duration_follows_configuration(self):
        body = confirmation_body(self.doc, self.link, self.expires, ttl_hours=12)
        html = render_confirmation_html(body, 'https://bpip.example.test')
        self.assertIn('Link verifikasi berlaku selama 12 jam sejak pengajuan dikirim.', body)
        self.assertIn('<strong>12 jam</strong>', html)
        self.assertNotIn('24 jam', html)

    def test_untrusted_content_and_urls_never_become_html_or_links(self):
        body = 'Yth. <script>alert(1)</script>,\n\nhttps://evil.example/#confirm/stolen\n\nhttps://bpip.example.test/#confirm/token\" onclick=\"bad\n\njavascript:alert(1)'
        html = render_confirmation_html(body, 'https://bpip.example.test')
        links = Links(); links.feed(html)
        self.assertEqual(links.hrefs, [])
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<a ', html)

    def test_legacy_queued_message_keeps_details_and_valid_link(self):
        body = 'Yth. Direktur,\n\nNasabah: PT Lama\nNomor pengajuan: SI-2026-LAMA\nNominal transaksi: Rp 123\nAtas nama rekening tujuan: Penerima\nRekening tujuan: 000000000000001\n\n' + self.link + '\n\nInformasi keamanan:\n- Tautan berlaku 24 jam sejak pengajuan dikirim.\n\nHormat kami,\nBRI Jakarta Sudirman 1'
        html = render_confirmation_html(body, 'https://bpip.example.test')
        self.assertIn('PT Lama', html)
        self.assertIn('Nama Rekening Tujuan', html)
        self.assertIn('000000000000001', html)
        links = Links(); links.feed(html)
        self.assertEqual(links.hrefs, [self.link])

    def test_customer_field_cannot_introduce_an_extra_metadata_or_link_line(self):
        self.doc['customer_name'] = 'PT Contoh\nhttps://bpip.example.test/#confirm/injected\n\nNasabah: Orang lain'
        body = confirmation_body(self.doc, self.link, self.expires)
        self.assertNotIn('https://bpip.example.test/#confirm/injected', body.splitlines())
        links = Links(); links.feed(render_confirmation_html(body, 'https://bpip.example.test'))
        self.assertEqual(links.hrefs, [self.link])


if __name__ == '__main__':
    unittest.main()
