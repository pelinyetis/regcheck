// Builds the 3 fictional KVKK aydınlatma metni test documents.
// All company data is FICTIONAL (project rule: never real customer data).
// Usage: node scripts/build_docs.js   (run from project root)
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType,
  ShadingType, HeadingLevel, AlignmentType, LevelFormat, BorderStyle,
} = require("docx");

const CO = {
  unvan: "Kuzey Yıldızı Kitap ve Kırtasiye Ticaret A.Ş.",
  mersis: "0000-0000-0000-0001 (kurgusal)",
  adres: "Örnek Mahallesi, Kurgu Sokak No: 7, 34000 Kadıköy/İstanbul",
  eposta: "kvkk@kuzeyyildizi.example",
  kep: "kuzeyyildizi@kep.example",
  tel: "0 (212) 000 00 00",
  web: "www.kuzeyyildizi.example",
};

const W = 9026; // A4 content width in DXA (11906 - 2*1440)
const FONT = "Calibri";

const p = (text, opts = {}) => new Paragraph({
  spacing: { after: 120 }, ...opts,
  children: [new TextRun({ text, font: FONT, size: 22, ...(opts.run || {}) })],
});
const h = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text })] });
const bullet = (text) => new Paragraph({
  numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
  children: [new TextRun({ text, font: FONT, size: 22 })],
});

function table(headers, rows, widths) {
  const cell = (text, i, head) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA },
    shading: head ? { type: ShadingType.CLEAR, color: "auto", fill: "D9E2F3" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text, font: FONT, size: 20, bold: head })] })],
  });
  return new Table({
    width: { size: W, type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, children: headers.map((t, i) => cell(t, i, true)) }),
      ...rows.map((r) => new TableRow({ children: r.map((t, i) => cell(t, i, false)) })),
    ],
  });
}
const spacer = () => new Paragraph({ spacing: { after: 120 }, children: [] });

// ---------- shared sections ----------
function header(version) {
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { after: 120 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "C00000", space: 4 } },
      children: [new TextRun({ text: "KURGUSAL ÖRNEK BELGE – yalnızca demo amaçlıdır; gerçek bir şirkete ait değildir.", font: FONT, size: 18, italics: true, color: "C00000" })],
    }),
    new Paragraph({ heading: HeadingLevel.TITLE, alignment: AlignmentType.CENTER, children: [new TextRun({ text: CO.unvan.toLocaleUpperCase("tr-TR") })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [new TextRun({ text: "Müşteri ve Üyelik Süreçlerine İlişkin Kişisel Verilerin İşlenmesi Aydınlatma Metni", font: FONT, size: 26, bold: true })] }),
    p(`Sürüm ${version} – Yürürlük tarihi: 01.10.2026`, { alignment: AlignmentType.CENTER, run: { size: 18, color: "595959" } }),
  ];
}

function vsSection(n) {
  return [
    h(`${n}. Veri Sorumlusu`),
    p(`6698 sayılı Kişisel Verilerin Korunması Kanunu (“Kanun”) uyarınca, kişisel verileriniz veri sorumlusu sıfatıyla ${CO.unvan} (“Şirket”) tarafından aşağıda açıklanan kapsamda işlenecektir.`),
    table(["Bilgi", "Değer"], [
      ["Unvan", CO.unvan], ["MERSİS No", CO.mersis], ["Adres", CO.adres],
      ["E-posta", CO.eposta], ["KEP adresi", CO.kep], ["Telefon", CO.tel],
    ], [2600, 6426]),
    spacer(),
    p("Şirket Türkiye’de yerleşik olduğundan veri sorumlusu temsilcisi atanmamıştır."),
  ];
}

function kategoriSection(n) {
  return [
    h(`${n}. İşlenen Kişisel Veri Kategorileri`),
    bullet("Kimlik: ad, soyad."),
    bullet("İletişim: e-posta adresi, cep telefonu numarası, teslimat ve fatura adresi."),
    bullet("Müşteri işlem: sipariş geçmişi, sepet içeriği, iade ve değişim talepleri, müşteri hizmetleri yazışmaları."),
    bullet("Finans: fatura bilgileri. Kart bilgileriniz Şirket tarafından saklanmaz; ödeme kuruluşu tarafından işlenir."),
    bullet("İşlem güvenliği: IP adresi, oturum açma ve kapama kayıtları."),
    bullet("Pazarlama: ilgi alanları ve iletişim tercihleri (yalnızca açık rıza vermeniz hâlinde)."),
  ];
}

const AMACLAR = [
  ["Üyelik hesabının oluşturulması ve yönetilmesi", "Kimlik, İletişim", "Kanun md. 5/2-c: bir sözleşmenin kurulması veya ifasıyla doğrudan ilgili olması"],
  ["Siparişlerin alınması, teslimi, iade ve değişim işlemleri", "Kimlik, İletişim, Müşteri işlem", "Kanun md. 5/2-c"],
  ["Fatura düzenlenmesi ve ticari defter/belgelerin saklanması (213 sayılı VUK, 6102 sayılı TTK)", "Kimlik, Finans, Müşteri işlem", "Kanun md. 5/2-ç: veri sorumlusunun hukuki yükümlülüğü"],
  ["Mesafeli satış kapsamında ön bilgilendirme ve cayma hakkı kayıtlarının tutulması (6502 sayılı Kanun)", "Kimlik, İletişim, Müşteri işlem", "Kanun md. 5/2-ç"],
  ["Hesap güvenliğinin sağlanması ve dolandırıcılığın önlenmesi", "İşlem güvenliği", "Kanun md. 5/2-f: veri sorumlusunun meşru menfaati"],
  ["Talep ve şikâyetlerin yanıtlanması", "Kimlik, İletişim, Müşteri işlem", "Kanun md. 5/2-c ve 5/2-e: bir hakkın tesisi, kullanılması veya korunması"],
  ["Kampanya duyuruları ve kişiselleştirilmiş kitap önerileri gönderilmesi", "İletişim, Pazarlama", "Kanun md. 5/1: açık rıza (ayrı Açık Rıza Metni ile alınır; rıza vermemeniz alışverişinizi etkilemez)"],
];

function amacSection(n, withLegalBasis) {
  if (withLegalBasis) {
    return [
      h(`${n}. Kişisel Verilerin İşlenme Amaçları ve Hukuki Sebepleri`),
      p("Kişisel verileriniz aşağıdaki amaçlarla ve her bir amacın karşısında belirtilen hukuki sebebe dayanılarak işlenmektedir:"),
      table(["İşleme amacı", "Veri kategorisi", "Hukuki sebep"], AMACLAR, [3600, 2026, 3400]),
      spacer(),
    ];
  }
  // Variant B: purposes only — legal basis column dropped, consent wording softened
  return [
    h(`${n}. Kişisel Verilerin İşlenme Amaçları`),
    p("Kişisel verileriniz aşağıdaki amaçlarla işlenmektedir:"),
    table(["İşleme amacı", "Veri kategorisi"],
      AMACLAR.map(([a, k], i) => [i === AMACLAR.length - 1 ? "Kampanya duyuruları ve kişiselleştirilmiş kitap önerileri gönderilmesi" : a, k]),
      [5826, 3200]),
    spacer(),
  ];
}

function yontemSection(n) {
  return [
    h(`${n}. Kişisel Veri Toplamanın Yöntemi`),
    p(`Kişisel verileriniz; ${CO.web} internet sitesi, Kuzey Yıldızı mobil uygulaması, müşteri hizmetleri çağrı merkezi ve e-posta kanalları aracılığıyla elektronik ortamda toplanmaktadır. Üyelik ve sipariş formları ile sistem kayıtları aracılığıyla toplanan veriler kısmen otomatik yollarla; çağrı merkezi görüşmelerinde sözlü olarak iletilen veriler ise müşteri temsilcisi tarafından sisteme girilerek otomatik olmayan yollarla elde edilmektedir.`),
    p("Çerezler aracılığıyla yapılan işlemeler hakkında ayrıca Çerez Aydınlatma Metni sunulmaktadır."),
  ];
}

function aktarimTable(n) {
  return [
    h(`${n}. Kişisel Verilerin Aktarılması`),
    p("Kişisel verileriniz, Kanun’un 8’inci maddesinde belirtilen şartlara uygun olarak aşağıdaki alıcı gruplarına, karşılarında belirtilen amaçlarla aktarılabilecektir:"),
    table(["Alıcı grubu", "Aktarım amacı"], [
      ["Kargo ve lojistik firmaları", "Siparişlerin teslim edilmesi ve iade ürünlerin teslim alınması"],
      ["Ödeme kuruluşları ve bankalar", "Ödemenin alınması ve iade tutarlarının ödenmesi"],
      ["Barındırma ve bulut hizmet sağlayıcısı (sunucuları Türkiye’de)", "Verilerin güvenli biçimde saklanması ve sistemlerin işletilmesi"],
      ["Mali müşavir ve bağımsız denetim şirketi", "Yasal muhasebe ve denetim yükümlülüklerinin yerine getirilmesi"],
      ["Yetkili kamu kurum ve kuruluşları (Gelir İdaresi Başkanlığı, Ticaret Bakanlığı) ve yargı mercileri", "Hukuki yükümlülüklerin yerine getirilmesi; yalnızca kanuni talep hâlinde"],
    ], [4200, 4826]),
    spacer(),
    p("Kişisel verileriniz yurt dışına aktarılmamaktadır."),
  ];
}

// Variant C: the borderline issue — generic recipient groups + catch-all purpose
function aktarimBorderline(n) {
  return [
    h(`${n}. Kişisel Verilerin Aktarılması`),
    p("Kişisel verileriniz, yukarıda sayılan amaçların gerçekleştirilmesi ve Şirket’in ticari faaliyetlerinin yürütülmesi kapsamında, Kanun’un 8’inci maddesinde belirtilen şartlara uygun olarak iş ortaklarımıza, tedarikçilerimize, hizmet aldığımız üçüncü kişilere ve yetkili kamu kurum ve kuruluşlarına aktarılabilecektir."),
    p("Kişisel verileriniz yurt dışına aktarılmamaktadır."),
  ];
}

function haklarSection(n) {
  return [
    h(`${n}. Kanun’un 11’inci Maddesi Kapsamındaki Haklarınız`),
    p("Kanun’un 11’inci maddesi uyarınca Şirket’e başvurarak;"),
    bullet("kişisel verilerinizin işlenip işlenmediğini öğrenme,"),
    bullet("kişisel verileriniz işlenmişse buna ilişkin bilgi talep etme,"),
    bullet("kişisel verilerinizin işlenme amacını ve bunların amacına uygun kullanılıp kullanılmadığını öğrenme,"),
    bullet("yurt içinde veya yurt dışında kişisel verilerinizin aktarıldığı üçüncü kişileri bilme,"),
    bullet("kişisel verilerinizin eksik veya yanlış işlenmiş olması hâlinde bunların düzeltilmesini isteme,"),
    bullet("Kanun’un 7’nci maddesinde öngörülen şartlar çerçevesinde kişisel verilerinizin silinmesini veya yok edilmesini isteme,"),
    bullet("düzeltme, silme veya yok etme işlemlerinin kişisel verilerinizin aktarıldığı üçüncü kişilere bildirilmesini isteme,"),
    bullet("işlenen verilerinizin münhasıran otomatik sistemler vasıtasıyla analiz edilmesi suretiyle aleyhinize bir sonucun ortaya çıkmasına itiraz etme,"),
    bullet("kişisel verilerinizin kanuna aykırı olarak işlenmesi sebebiyle zarara uğramanız hâlinde zararın giderilmesini talep etme"),
    p("haklarına sahipsiniz."),
    p(`Taleplerinizi, Veri Sorumlusuna Başvuru Usul ve Esasları Hakkında Tebliğ’e uygun olarak yazılı şekilde ${CO.adres} adresine, ${CO.kep} KEP adresine veya Şirket sistemlerinde kayıtlı e-posta adresinizden ${CO.eposta} adresine iletebilirsiniz. Başvurunuz, talebin niteliğine göre en geç otuz gün içinde ücretsiz olarak sonuçlandırılır; işlemin ayrıca bir maliyet gerektirmesi hâlinde Kurulca belirlenen tarifedeki ücret alınabilir.`),
  ];
}

function iletisimOnly(n) {
  return [
    h(`${n}. İletişim`),
    p(`Kişisel verilerinize ilişkin her türlü soru ve talebiniz için ${CO.eposta} adresinden bizimle iletişime geçebilirsiniz.`),
  ];
}

function footer() {
  return [
    spacer(),
    p("Bu metin, Kanun’un 10’uncu maddesi uyarınca hazırlanmıştır. Açık rıza gerektiren işlemeler için ayrı bir Açık Rıza Metni sunulmaktadır.", { run: { size: 18, italics: true, color: "595959" } }),
  ];
}

// ---------- variants ----------
const VARIANTS = {
  "A_uyumlu": () => [
    ...header("1.0"), ...vsSection(1), ...kategoriSection(2), ...amacSection(3, true),
    ...yontemSection(4), ...aktarimTable(5), ...haklarSection(6), ...footer()],
  // Missing: md.10/1-ç (method + legal basis) and md.10/1-d (art. 11 rights)
  "B_eksik": () => [
    ...header("1.0"), ...vsSection(1), ...kategoriSection(2), ...amacSection(3, false),
    ...aktarimTable(4), ...iletisimOnly(5), ...footer()],
  // Borderline: generic recipient groups / catch-all transfer purpose (md.10/1-c, Tebliğ 5/1-g, 5/1-ı)
  "C_sinirda": () => [
    ...header("1.0"), ...vsSection(1), ...kategoriSection(2), ...amacSection(3, true),
    ...yontemSection(4), ...aktarimBorderline(5), ...haklarSection(6), ...footer()],
};

const styles = {
  default: { document: { run: { font: FONT, size: 22 } } },
  paragraphStyles: [
    { id: "Title", name: "Title", basedOn: "Normal", run: { font: FONT, size: 32, bold: true, color: "1F3864" }, paragraph: { spacing: { before: 120, after: 60 }, keepNext: true } },
    { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 24, bold: true, color: "1F3864" }, paragraph: { spacing: { before: 240, after: 120 }, keepNext: true, outlineLevel: 0 } },
  ],
};
const numbering = { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }] };

(async () => {
  const outDir = path.join(process.cwd(), "docs");
  fs.mkdirSync(outDir, { recursive: true });
  for (const [name, build] of Object.entries(VARIANTS)) {
    const doc = new Document({
      creator: "Pelin Yetiş", lastModifiedBy: "Pelin Yetiş", title: `KVKK Aydınlatma Metni – ${name} (kurgusal)`,
      styles, numbering, sections: [{ properties: {}, children: build() }],
    });
    const file = path.join(outDir, `${name}_aydinlatma_metni.docx`);
    fs.writeFileSync(file, await Packer.toBuffer(doc));
    console.log("wrote", file);
  }
})();
