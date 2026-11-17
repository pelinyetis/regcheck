# RegCheck Uyum Raporu: KVKK Aydınlatma Metni

| | |
|---|---|
| **Belge** | {{ r.document_id }} |
| **Veri sorumlusu** | {{ r.controller }} |
| **Genel değerlendirme** | {{ {"compliant": "✅ Uyumlu", "non_compliant": "❌ Uyumsuz", "needs_human_review": "⚠️ Hukukçu incelemesi gerekli"}[r.overall_assessment] }} |
| **İnsan incelemesi (Action Center)** | {{ "Evet" if r.human_review_required else "Hayır" }} |
| **Kontrol ölçütü** | 6698 sayılı KVKK md. 10 |
{%- if meta %}
| **Çalışma** | {{ meta.run_at }} · {{ "%.0f"|format(meta.duration_s) }} sn · {{ meta.num_turns }} tur · model: {{ meta.model }} |
{%- endif %}

**Özet:** {{ r.summary }}

## 1. Unsur kontrolü (KVKK md. 10/1)

| Bent | Unsur | Durum | Belgedeki dayanak |
|---|---|---|---|
{%- for e in r.element_checks %}
| {{ e.element }} | {{ labels[e.element] }} | {{ {"present": "✅ Var", "deficient": "⚠️ Yetersiz", "missing": "❌ Yok"}[e.status] }} | {{ (e.evidence or "—")|truncate(140)|replace("|", "/")|replace("\n", " ") }} |
{%- endfor %}

## 2. Bulgular
{% if not r.findings %}
Bulgu yok.
{% endif %}
{%- for f in r.findings %}
### {{ f.id }} · {{ f.title }}

| | |
|---|---|
| **Unsur** | {{ f.element }} ({{ f.issue_type }}) |
| **Önem** | {{ {"high": "Yüksek", "medium": "Orta", "low": "Düşük"}[f.severity] }} |
| **Güven skoru** | {{ "%.2f"|format(f.confidence) }}{% if f.escalate %} → **⚠️ insan incelemesine yönlendirildi**{% endif %} |

{{ f.description }}
{% if f.document_excerpt %}
> **Belgeden:** {{ f.document_excerpt|replace("\n", " ") }}
{% endif %}
**Dayanaklar:**
{%- for c in f.citations %}
- **{{ c.reference }}** ([kaynak]({{ c.source_url }}), {{ c.retrieved_via }}): “{{ c.supporting_quote|replace("\n", " ") }}”
{%- endfor %}

**Öneri:** {{ f.recommendation }}
{% if f.escalate %}
**Hukukçunun karar vermesi gereken husus:** {{ f.escalation_reason }}
{% endif %}
{%- endfor %}

## 3. İdari para cezası riski
{% if r.penalty_exposure.applicable %}
**{{ r.penalty_exposure.reference }}**: {{ r.penalty_exposure.range }} ([kaynak]({{ r.penalty_exposure.source_url }}))
{% else %}
Kesinleşmiş bir md. 10 ihlali tespit edilmediğinden ceza riski öngörülmemiştir.
{% endif %}
_{{ r.penalty_exposure.note }}_

## 4. Bu çalışmada başvurulan kaynaklar

| Araç | Girdi | Bulguda kullanıldı |
|---|---|---|
{%- for s in r.sources_consulted %}
| `{{ s.tool }}` | {{ s.input|truncate(110)|replace("|", "/") }} | {{ "✓" if s.used_in_findings else "" }} |
{%- endfor %}

---
_Bu rapor RegCheck demo ajanı tarafından otomatik üretilmiştir ve hukuki görüş değildir. Güven skoru 0,70'in altındaki bulgular hukukçu onayı olmadan kesinleşmez._
