"""Build the second fictional test set (D, E, F) as PDF files with a normal text layer.

  Document IDs and the files they are written to (docs/):
  D_klinik_uyumlu      -> D_klinik_uyumlu_aydinlatma_metni.pdf
  E_spor_eksik         -> E_spor.pdf
  F_fintech_sinirda    -> F_fintech.pdf

  D_klinik_uyumlu      private clinic, health data (KVKK md. 6), fully compliant
  E_spor_eksik         gym chain, md. 10/1-b (purposes) and 10/1-c (recipients/transfer) missing
  F_fintech_sinirda    payment app, borderline: legal bases listed but not mapped to purposes (10/1-ç)

All companies, addresses, numbers and domains are invented (".example" domains, "(kurgusal)" MERSİS).
Usage: uv run --no-project --python 3.12 --with reportlab python -I scripts/build_docs_def.py
"""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
pdfmetrics.registerFont(TTFont("Arial", r"C:\Windows\Fonts\arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\Windows\Fonts\arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic", r"C:\Windows\Fonts\ariali.ttf"))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic", boldItalic="Arial-Bold")

BODY = ParagraphStyle("body", fontName="Arial", fontSize=9.5, leading=12.5, spaceAfter=4)
NOTE = ParagraphStyle("note", parent=BODY, fontName="Arial-Italic", fontSize=8.5, textColor=colors.HexColor("#7a1f1f"), alignment=TA_CENTER, spaceAfter=8)
TITLE = ParagraphStyle("title", parent=BODY, fontName="Arial-Bold", fontSize=13, leading=16, alignment=TA_CENTER, spaceAfter=2)
SUB = ParagraphStyle("sub", parent=BODY, fontName="Arial-Bold", fontSize=10.5, alignment=TA_CENTER, spaceAfter=2)
VER = ParagraphStyle("ver", parent=BODY, fontSize=8.5, alignment=TA_CENTER, textColor=colors.HexColor("#555555"), spaceAfter=10)
H = ParagraphStyle("h", parent=BODY, fontName="Arial-Bold", fontSize=10.5, leading=13, spaceBefore=8, spaceAfter=4)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.5, leading=10.5, spaceAfter=0)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="Arial-Bold")
BULLET = ParagraphStyle("bullet", parent=BODY, leftIndent=12, bulletIndent=2, spaceAfter=2, bulletFontName="Arial")

FICTION = "KURGUSAL ÖRNEK BELGE – yalnızca demo amaçlıdır; gerçek bir şirkete veya kişiye ait değildir."


def P(text, style=BODY):
    return Paragraph(text, style)


def bullets(items):
    return [Paragraph(escape(t), BULLET, bulletText="–") for t in items]


def table(rows, widths, header=True):
    data = [[Paragraph(escape(c), CELLB if (header and i == 0) else CELL) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
             ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6e6e6")))
    t.setStyle(TableStyle(style))
    return [t, Spacer(1, 6)]


def identity(rows):
    return table([["Bilgi", "Değer"]] + rows, [4.2, 12.3])


RIGHTS = [
    "a) Kişisel verilerinizin işlenip işlenmediğini öğrenme,",
    "b) Kişisel verileriniz işlenmişse buna ilişkin bilgi talep etme,",
    "c) Kişisel verilerinizin işlenme amacını ve bunların amacına uygun kullanılıp kullanılmadığını öğrenme,",
    "ç) Yurt içinde veya yurt dışında kişisel verilerinizin aktarıldığı üçüncü kişileri bilme,",
    "d) Kişisel verilerinizin eksik veya yanlış işlenmiş olması hâlinde bunların düzeltilmesini isteme,",
    "e) Kanun’un 7’nci maddesinde öngörülen şartlar çerçevesinde kişisel verilerinizin silinmesini veya yok edilmesini isteme,",
    "f) (d) ve (e) bentleri uyarınca yapılan işlemlerin, kişisel verilerinizin aktarıldığı üçüncü kişilere bildirilmesini isteme,",
    "g) İşlenen verilerin münhasıran otomatik sistemler vasıtasıyla analiz edilmesi suretiyle aleyhinize bir sonucun ortaya çıkmasına itiraz etme,",
    "ğ) Kişisel verilerinizin kanuna aykırı olarak işlenmesi sebebiyle zarara uğramanız hâlinde zararın giderilmesini talep etme.",
]


def rights_section(num, company_dative, email, kep, address):
    return [
        P(f"{num}. İlgili Kişi Olarak Haklarınız", H),
        P(f"Kanun’un 11’inci maddesi uyarınca {escape(company_dative)} başvurarak aşağıdaki haklarınızı kullanabilirsiniz:"),
        *bullets(RIGHTS),
        P("Başvurularınızı, Veri Sorumlusuna Başvuru Usul ve Esasları Hakkında Tebliğ’e uygun olarak; "
          f"{escape(address)} adresine yazılı olarak, {escape(kep)} KEP adresine veya sistemimizde kayıtlı e-posta adresinizden "
          f"{escape(email)} adresine iletebilirsiniz. Başvurunuz, talebin niteliğine göre en geç otuz gün içinde ücretsiz olarak "
          "sonuçlandırılır; işlemin ayrıca bir maliyet gerektirmesi hâlinde Kurulca belirlenen tarifedeki ücret alınabilir."),
    ]


def build(path, story):
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title=path.stem, author="Pelin Yetiş", creator="Cognera Teknoloji", subject="Kurgusal KVKK aydınlatma metni")
    doc.build(story)


# ------------------------------------------------------------------ D: clinic, compliant
def doc_d():
    co, short = "Ilgaz Tıp Merkezi Sağlık Hizmetleri A.Ş.", "Merkez"
    addr = "Kurgu Mahallesi, Şifa Caddesi No: 12, 06000 Çankaya/Ankara"
    s = [P(FICTION, NOTE), P("ILGAZ TIP MERKEZİ SAĞLIK HİZMETLERİ A.Ş.", TITLE),
         P("Hasta ve Hasta Yakınlarına Yönelik Kişisel Verilerin İşlenmesi Aydınlatma Metni", SUB),
         P("Sürüm 1.0 – Yürürlük tarihi: 01.11.2026", VER),
         P("1. Veri Sorumlusu", H),
         P(f"6698 sayılı Kişisel Verilerin Korunması Kanunu (“Kanun”) uyarınca, kişisel verileriniz veri sorumlusu sıfatıyla {co} (“Merkez”) tarafından aşağıda açıklanan kapsamda işlenecektir."),
         *identity([["Unvan", co], ["MERSİS No", "0000-0000-0000-0042 (kurgusal)"], ["Adres", addr],
                    ["E-posta", "kvkk@ilgaztip.example"], ["KEP adresi", "ilgaztip@kep.example"], ["Telefon", "0 (312) 000 00 00"]]),
         P("Merkez Türkiye’de yerleşik olduğundan veri sorumlusu temsilcisi atanmamıştır."),
         P("2. İşlenen Kişisel Veri Kategorileri", H),
         *bullets(["Kimlik: ad, soyad, T.C. kimlik numarası, doğum tarihi, cinsiyet.",
                   "İletişim: telefon numarası, e-posta adresi, adres; hasta yakınının adı ve telefon numarası.",
                   "Hasta işlem: randevu bilgileri, hasta kabul kayıtları, fatura ve provizyon bilgileri.",
                   "Finans: ödeme bilgileri, özel sağlık sigortası poliçe numarası.",
                   "Sağlık verileri (özel nitelikli kişisel veri): şikâyet ve öykü, muayene bulguları, tanı, tetkik ve görüntüleme sonuçları, reçete ve epikriz bilgileri.",
                   "Görsel kayıt: bekleme alanları ve girişlerdeki güvenlik kamerası kayıtları."]),
         P("3. İşleme Amaçları ve Hukuki Sebepler", H),
         P("Kişisel verileriniz aşağıdaki amaçlarla ve her bir amacın karşısında belirtilen hukuki sebebe dayanılarak işlenmektedir:"),
         *table([["İşleme amacı", "Veri kategorileri", "Hukuki sebep"],
                 ["Randevu oluşturulması ve hasta kabulünün yapılması", "Kimlik, iletişim, hasta işlem", "Bir sözleşmenin kurulması veya ifasıyla doğrudan ilgili olması (Kanun md. 5/2-c)"],
                 ["Tıbbi teşhis, tedavi ve bakım hizmetlerinin yürütülmesi", "Kimlik, sağlık verileri", "Sır saklama yükümlülüğü altındaki hekim ve sağlık personelince tıbbi teşhis, tedavi ve bakım hizmetlerinin yürütülmesi amacıyla gerekli olması (Kanun md. 6/3-e)"],
                 ["Sağlık mevzuatı uyarınca hasta kayıtlarının tutulması ve Sağlık Bakanlığı sistemlerine bildirim yapılması", "Kimlik, sağlık verileri, hasta işlem", "Kanunlarda açıkça öngörülmesi (Kanun md. 5/2-a ve md. 6/3-b)"],
                 ["Sağlık hizmeti bedellerinin faturalandırılması, SGK ve özel sigorta provizyon işlemleri", "Kimlik, finans, hasta işlem, sağlık verileri (provizyonla sınırlı)", "Hukuki yükümlülüğün yerine getirilmesi (Kanun md. 5/2-ç); sağlık verileri bakımından sağlık hizmetlerinin finansmanı amacıyla gerekli olması (Kanun md. 6/3-e)"],
                 ["Hasta ve tesis güvenliğinin sağlanması", "Görsel kayıt", "Temel hak ve özgürlüklerinize zarar vermemek kaydıyla Merkez’in meşru menfaati (Kanun md. 5/2-f)"],
                 ["Hasta memnuniyeti anketlerinin gönderilmesi", "İletişim", "Açık rızanız (Kanun md. 5/1); ayrı Açık Rıza Metni ile alınır"]],
                [5.2, 4.4, 6.9]),
         P("4. Kişisel Verilerin Toplanma Yöntemi", H),
         P("Kişisel verileriniz; çağrı merkezi, internet sitesi ve mobil uygulama üzerinden randevu alınması sırasında elektronik ortamda; hasta kabul bankosunda doldurulan formlar ile muayene, tetkik ve tedavi süreçlerinde hekim ve sağlık personeli aracılığıyla fiziki ve elektronik ortamda; bekleme alanlarındaki kamera sistemi aracılığıyla elektronik ortamda toplanmaktadır. Verileriniz kısmen otomatik yollarla (randevu ve kamera sistemleri) ve otomatik olmayan yollarla (basılı formlar) elde edilmektedir."),
         P("5. Kişisel Verilerin Aktarılması", H),
         P("Kişisel verileriniz, Kanun’un 8’inci maddesinde belirtilen şartlara uygun olarak aşağıdaki alıcı gruplarına, karşılarında belirtilen amaçlarla aktarılabilecektir:"),
         *table([["Alıcı grubu", "Aktarım amacı"],
                 ["Sağlık Bakanlığı ve bağlı sistemler (e-Nabız, Ulusal Sağlık Sistemi)", "Sağlık mevzuatı uyarınca zorunlu kayıt ve bildirimlerin yapılması"],
                 ["Sosyal Güvenlik Kurumu", "Sağlık hizmeti bedellerinin faturalandırılması ve provizyon alınması"],
                 ["Hastanın sigortalı olduğu özel sağlık sigortası şirketi", "Provizyon ve tazminat süreçlerinin yürütülmesi"],
                 ["Anlaşmalı dış laboratuvar ve görüntüleme merkezleri", "Merkez’de yapılamayan tetkiklerin gerçekleştirilmesi"],
                 ["Yetkili kamu kurum ve kuruluşları ile yargı mercileri", "Hukuki yükümlülüklerin yerine getirilmesi ve resmî taleplerin karşılanması"]],
                [7.0, 9.5]),
         P("Kişisel verileriniz yurt dışına aktarılmamaktadır."),
         *rights_section(6, "Merkez’e", "kvkk@ilgaztip.example", "ilgaztip@kep.example", addr),
         P("Açık rıza gerektiren işlemler için ayrıca Açık Rıza Metni sunulmaktadır. Bu aydınlatma metni, açık rıza alınmasından bağımsız olarak hazırlanmıştır."),
         ]
    build(ROOT / "docs" / "D_klinik_uyumlu_aydinlatma_metni.pdf", s)


# ------------------------------------------------------------------ E: gym chain, 10/1-b and 10/1-c missing
def doc_e():
    co = "Çınaraltı Spor ve Sağlıklı Yaşam Hizmetleri Ltd. Şti."
    addr = "Örnek Mahallesi, Kondisyon Sokak No: 3, 35000 Konak/İzmir"
    s = [P(FICTION, NOTE), P("ÇINARALTI SPOR VE SAĞLIKLI YAŞAM HİZMETLERİ LTD. ŞTİ. (“ÇınarFit”)", TITLE),
         P("Üyelerimize Yönelik Kişisel Verilerin İşlenmesi Aydınlatma Metni", SUB),
         P("Sürüm 2.1 – Yürürlük tarihi: 15.10.2026", VER),
         P("1. Veri Sorumlusu", H),
         P(f"6698 sayılı Kişisel Verilerin Korunması Kanunu (“Kanun”) uyarınca, kişisel verileriniz veri sorumlusu sıfatıyla {co} (“ÇınarFit”) tarafından işlenmektedir."),
         *identity([["Unvan", co], ["MERSİS No", "0000-0000-0000-0077 (kurgusal)"], ["Adres", addr],
                    ["E-posta", "kvkk@cinarfit.example"], ["KEP adresi", "cinarfit@kep.example"], ["Telefon", "0 (232) 000 00 00"]]),
         P("ÇınarFit Türkiye’de yerleşik olduğundan veri sorumlusu temsilcisi atanmamıştır."),
         P("2. İşlenen Kişisel Veri Kategorileri ve Hukuki Sebepler", H),
         P("ÇınarFit tarafından işlenen kişisel veri kategorileri ve her bir kategorinin dayandığı hukuki sebep aşağıda gösterilmiştir:"),
         *table([["Veri kategorisi", "İçerik", "Hukuki sebep"],
                 ["Kimlik", "Ad, soyad, doğum tarihi", "Bir sözleşmenin kurulması veya ifasıyla doğrudan ilgili olması (Kanun md. 5/2-c)"],
                 ["İletişim", "Cep telefonu numarası, e-posta adresi, adres", "Bir sözleşmenin kurulması veya ifasıyla doğrudan ilgili olması (Kanun md. 5/2-c)"],
                 ["Üyelik bilgileri", "Üyelik paketi, başlangıç ve bitiş tarihleri, üyelik kartı numarası, kulüp giriş-çıkış saatleri", "Bir sözleşmenin kurulması veya ifasıyla doğrudan ilgili olması (Kanun md. 5/2-c)"],
                 ["Finans", "Ödeme bilgileri, fatura bilgileri", "Hukuki yükümlülüğün yerine getirilmesi (Kanun md. 5/2-ç)"],
                 ["Görsel kayıt", "Kulüp giriş ve ortak alanlarındaki kamera kayıtları", "Temel hak ve özgürlüklerinize zarar vermemek kaydıyla ÇınarFit’in meşru menfaati (Kanun md. 5/2-f)"],
                 ["İletişim izinleri", "SMS ve e-posta izin durumu", "Açık rızanız (Kanun md. 5/1)"]],
                [3.0, 6.2, 7.3]),
         P("Soyunma odaları ve duş alanlarında kamera bulunmamaktadır. Kart bilgileriniz ÇınarFit tarafından saklanmaz."),
         P("3. Kişisel Verilerin Toplanma Yöntemi", H),
         P("Kişisel verileriniz; kulüp resepsiyonlarında doldurulan üyelik sözleşmesi ve formlar aracılığıyla fiziki ortamda; ÇınarFit mobil uygulaması ve internet sitesi üzerinden yapılan üyelik ve paket yenileme işlemleri sırasında elektronik ortamda; kulüp girişlerindeki kart okuyucular ve kamera sistemleri aracılığıyla elektronik ortamda toplanmaktadır. Verileriniz kısmen otomatik yollarla (kart okuyucu, kamera ve mobil uygulama) ve otomatik olmayan yollarla (basılı formlar) elde edilmektedir."),
         *rights_section(4, "ÇınarFit’e", "kvkk@cinarfit.example", "cinarfit@kep.example", addr),
         P("Açık rızanıza dayanan işlemler için rızanız ayrı bir form ile alınmaktadır; açık rızanızı dilediğiniz zaman geri alabilirsiniz."),
         ]
    build(ROOT / "docs" / "E_spor.pdf", s)


# ------------------------------------------------------------------ F: payment app, legal bases not mapped (borderline)
def doc_f():
    co = "Defne Ödeme ve Elektronik Para Hizmetleri A.Ş."
    addr = "Deneme Mahallesi, Finans Bulvarı No: 21 Kat: 4, 34000 Ataşehir/İstanbul"
    s = [P(FICTION, NOTE), P("DEFNE ÖDEME VE ELEKTRONİK PARA HİZMETLERİ A.Ş. (“DefnePay”)", TITLE),
         P("DefnePay Mobil Uygulaması Kullanıcılarına Yönelik Kişisel Verilerin İşlenmesi Aydınlatma Metni", SUB),
         P("Sürüm 3.0 – Yürürlük tarihi: 01.09.2026", VER),
         P("1. Veri Sorumlusu", H),
         P(f"6698 sayılı Kişisel Verilerin Korunması Kanunu (“Kanun”) uyarınca, kişisel verileriniz veri sorumlusu sıfatıyla {co} (“DefnePay”) tarafından aşağıda açıklanan kapsamda işlenecektir."),
         *identity([["Unvan", co], ["MERSİS No", "0000-0000-0000-0099 (kurgusal)"], ["Adres", addr],
                    ["E-posta", "kvkk@defnepay.example"], ["KEP adresi", "defnepay@kep.example"], ["Telefon", "0 (216) 000 00 00"]]),
         P("DefnePay Türkiye’de yerleşik olduğundan veri sorumlusu temsilcisi atanmamıştır."),
         P("2. İşlenen Kişisel Veri Kategorileri", H),
         *bullets(["Kimlik: ad, soyad, T.C. kimlik numarası, doğum tarihi, kimlik belgesi görüntüsü.",
                   "İletişim: cep telefonu numarası, e-posta adresi, adres.",
                   "Müşteri işlem: elektronik para cüzdanı hareketleri, para transferi ve ödeme işlem kayıtları, işlem açıklamaları.",
                   "Finans: IBAN, bağlı banka kartının ilk altı ve son dört hanesi.",
                   "İşlem güvenliği: IP adresi, cihaz kimliği, oturum kayıtları, şifre ve doğrulama kodu kayıtları.",
                   "Risk yönetimi: müşterinin tanınmasına ilişkin kontrol sonuçları, şüpheli işlem değerlendirme kayıtları.",
                   "Pazarlama: kampanya tercihleri ve iletişim izinleri."]),
         P("3. Kişisel Verilerin İşlenme Amaçları ve Hukuki Sebepleri", H),
         P("Kişisel verileriniz aşağıdaki amaçlarla işlenmektedir:"),
         *bullets(["DefnePay hesabının açılması, kimliğinizin doğrulanması ve hesabın yönetilmesi,",
                   "Elektronik para ihracı, ödeme ve para transferi işlemlerinin gerçekleştirilmesi,",
                   "5549 sayılı Suç Gelirlerinin Aklanmasının Önlenmesi Hakkında Kanun ve ilgili mevzuat kapsamında müşterinin tanınması, şüpheli işlem bildirimi ve kayıtların saklanması,",
                   "Dolandırıcılık ve yetkisiz işlemlerin önlenmesi, hesap ve işlem güvenliğinin sağlanması,",
                   "Müşteri talep ve şikâyetlerinin yanıtlanması,",
                   "Açık rızanızın bulunması hâlinde kampanya ve tanıtım iletilerinin gönderilmesi."]),
         P("Kişisel verileriniz, yukarıda belirtilen amaçlarla, Kanun’un 5’inci maddesinin ikinci fıkrasında sayılan kanunlarda açıkça öngörülmesi, bir sözleşmenin kurulması veya ifasıyla doğrudan doğruya ilgili olması, veri sorumlusunun hukuki yükümlülüğünü yerine getirebilmesi için zorunlu olması ve ilgili kişinin temel hak ve özgürlüklerine zarar vermemek kaydıyla veri sorumlusunun meşru menfaatleri için veri işlenmesinin zorunlu olması hukuki sebeplerinden bir veya birkaçına dayanılarak; kampanya ve tanıtım iletileri bakımından ise Kanun’un 5’inci maddesinin birinci fıkrası uyarınca açık rızanıza dayanılarak işlenmektedir."),
         P("4. Kişisel Verilerin Toplanma Yöntemi", H),
         P("Kişisel verileriniz; DefnePay mobil uygulaması üzerinden hesap açılışı, kimlik doğrulama (kimlik kartı çipinin okunması ve görüntülü görüşme) ve işlem talimatları sırasında elektronik ortamda; müşteri hizmetleri çağrı merkezi ve e-posta kanalları aracılığıyla elektronik ortamda toplanmaktadır. Verileriniz, işlem ve güvenlik kayıtları bakımından otomatik yollarla, müşteri hizmetleri görüşmeleri bakımından kısmen otomatik yollarla elde edilmektedir."),
         P("5. Kişisel Verilerin Aktarılması", H),
         P("Kişisel verileriniz, Kanun’un 8’inci maddesinde belirtilen şartlara uygun olarak aşağıdaki alıcı gruplarına, karşılarında belirtilen amaçlarla aktarılabilecektir:"),
         *table([["Alıcı grubu", "Aktarım amacı"],
                 ["Türkiye Cumhuriyet Merkez Bankası", "Ödeme ve elektronik para mevzuatı kapsamındaki raporlama ve denetim yükümlülüklerinin yerine getirilmesi"],
                 ["Mali Suçları Araştırma Kurulu (MASAK)", "Şüpheli işlem bildirimi ve bilgi taleplerinin karşılanması"],
                 ["Para transferi yaptığınız hesabın bulunduğu banka veya ödeme kuruluşu", "Transfer talimatınızın gerçekleştirilmesi"],
                 ["Uzaktan kimlik doğrulama hizmeti aldığımız yurt içindeki hizmet sağlayıcı", "Hesap açılışında kimlik doğrulamanın yapılması"],
                 ["Yetkili kamu kurum ve kuruluşları ile yargı mercileri", "Hukuki yükümlülüklerin yerine getirilmesi ve resmî taleplerin karşılanması"]],
                [7.0, 9.5]),
         P("Kişisel verileriniz yurt dışına aktarılmamaktadır."),
         *rights_section(6, "DefnePay’e", "kvkk@defnepay.example", "defnepay@kep.example", addr),
         P("Kampanya ve tanıtım iletileri için açık rızanız uygulama içinde ayrı bir onay ekranı ile alınmaktadır."),
         ]
    build(ROOT / "docs" / "F_fintech.pdf", s)


if __name__ == "__main__":
    doc_d()
    doc_e()
    doc_f()
    print("built D, E, F")
