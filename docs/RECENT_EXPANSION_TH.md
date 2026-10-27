# ชุดข้อมูลย้อนหลัง 5 ปีและ Match Centre

งานรอบ 25 ตุลาคม 2026 อยู่ใน D:/Football Prediction AI แยกจากโปรเจกต์เดิม ไม่เรียก API-Football ไม่ deploy ไม่ promote โมเดล และไม่เพิ่มข่าว

## ข้อมูลและเหตุผล

- กำหนดชุดใหม่เฉพาะวันที่ 2021-10-25 ถึงก่อน 2026-10-25 เพื่อให้ตรงคำขอ 4–5 ปี ไม่อาศัยประวัติก่อนช่วงนี้ warm-start ratings
- ใช้ OpenFootball SHA เดิม e6744429ee395bc86f247348c6184bb08d4eb361 และ snapshot OpenLigaDB ที่เก็บ URL/เวลา/SHA256/สิทธิ์ ODbL ครบ
- เพิ่ม Serie A, Championship, Ligue 1, Eredivisie, Primeira Liga และดิวิชันรองที่แหล่งข้อมูลมีผลจริง ข้อมูลไม่ได้ครบทุกลีกทุกฤดูกาล จึงแสดงจำนวนแยกและไม่เติมผล
- ไม่ขยายไปบอลถ้วย/ลีก split-format โดยนำโมเดล regular league ไปใช้ทันที เพราะ regime ของเสมอ/ต่อเวลา/รอบและการจับคู่ต่างกัน
- การเทียบหลายแหล่งรวม evidence ไม่เพิ่มน้ำหนักแมตช์ซ้ำ ความขัดแย้งทั้งวันและสกอร์กักทั้งสองแหล่ง ไม่มีการเลือกเสียงข้างมากหรือแก้วันเงียบ ๆ
- ใช้ Fjelstul แยกสำหรับตรวจสกอร์อังกฤษ เพราะไฟล์ matches ไม่มีวันที่รายนัด จึงไม่ใช้แก้ chronology และไม่รวม labels ต่างสิทธิ์เข้าชุดฝึก
- ไม่ดึง Football-Data.co.uk หรือ mirrors มาเลี่ยงข้อจำกัดฝึกข้อมูลด้วย bots/AI แหล่งที่ยังไม่ยืนยันสิทธิ์ไม่ถูกนำเข้าฝึก
- รายการที่สำรวจและเหตุผล: reports/historical-source-catalog.json; สิทธิ์และการดัดแปลง: data/ATTRIBUTION.md

## คำสั่งเพิ่มข้อมูลและฝึกซ้ำ

ใช้ Python ใน .venv และ Node ตาม README:

```powershell
python -m scripts.fetch_history
python -m scripts.source_snapshot
python -m scripts.fetch_additional_history
python -m ml.expanded
python -m scripts.crosscheck_history
python -m ml.recent_evaluate
python -m ml.market_benchmarks
python -m scripts.verify_recent_reproducibility
python -m scripts.prepare_centre
python -m scripts.package_recent_model
npm run db:migrate:local
npm run db:seed:local
npm run db:seed:selection:local
npm run db:seed:centre:local
```

source_snapshot restore ใช้ archive ที่ตรวจ hash แล้ว ไม่เรียก API ใหม่ หาก raw ในเครื่องต่างจาก snapshot จะหยุด ไม่เขียนทับ snapshot ต้นฉบับ การเปลี่ยนช่วง/แหล่ง/ข้อมูลภายหลังต้องใช้ protocol version ใหม่ ไม่เขียนทับ protocol ก่อนประเมินเดิม

## หน้าเว็บและเวลา

เปิด terminal สองหน้ารัน `npm run dev:api` และ `npm run dev` ตาม URL ที่แสดง

- “วันนี้”: D 06:00 ถึงก่อน D+1 06:00 เวลาไทย ขณะเวลา 00:00–05:59 ยังเป็นรอบวันก่อน
- “คืนนี้”: D 18:00 ถึงก่อน D+1 06:00 เป็นช่วงย่อยของรอบเดียวกัน
- เริ่มที่รอบสาธิต 26 ต.ค. เพื่อแสดงฟังก์ชัน มีปุ่มวันนี้/คืนนี้และเลือกวันที่ ไม่อ้างว่าคู่สมมติเป็นโปรแกรมจริง
- โหลดครบทุกหน้า แยกการแข่งขันด้วย league ID และเรียงเวลา/โอกาส/ประตูได้ ไม่จัดลีกตามชื่อสโมสร
- หน้ารายคู่มี deep link, 1X2, independent Poisson expected goals, สกอร์, สูง–ต่ำเส้น 1.5/2.5/3.5 และ BTTS
- ประวัติ 5/10/20 นัด แยกเหย้า–เยือนและ H2H โดยคงมุมมองทีมปัจจุบัน แม้เกมเก่าสลับเจ้าบ้าน แสดง sample และ cutoff
- ส่วน API รอ coverage/season/mapping จริง ไม่ใช้ missing injuries/lineups เป็นค่าศูนย์

## รายงานและกติกา

daily-research-v2 ใช้ threshold ดิบ 70% + history/venue/date checks เพื่อทดสอบการทำงานเท่านั้น ไม่สืบทอดผล selective-v1 และไม่ถือว่าได้รับการยืนยันกับลีก/ตลาดใหม่

ชุด 3/5 ใช้ตลาด 1X2 แยก fixture และทีมที่ทับกัน ไม่เติมขาที่อ่อนเพื่อครบจำนวน แสดงผลคูณโดยตั้งสมมติฐานอิสระพร้อมข้อจำกัด ไม่เรียกว่า joint probability ที่ยืนยันแล้ว

รายงานจริงในระบบยังเป็น mock_research และมี live blockers เสมอ Public endpoints ไม่สามารถเปลี่ยนให้เป็น live เพียงเปลี่ยน flag

API ภายในที่มี HMAC/nonce เดิม:

- POST /internal/daily-reports/lock body {"date":"2026-10-26","period":"day"}: เก็บ snapshot ไม่เปลี่ยนแปลง พร้อม checksum และ exact model snapshot references ต้องทำก่อนเกมแรกของรอบเริ่ม
- POST /internal/daily-reports/evaluate body {"report_id":"..."}: เก็บผลตรวจแบบ append-only สกอร์ 90 นาที ตลาดครึ่งลูก; missing=pending, administrative/ยกเลิก=void; ชุดที่มี void ไม่ถูกนับเป็น full-size win
- GET /api/daily-report?date=...&period=... หรือ ?id=...: อ่านรายงานที่ล็อกและผลตรวจล่าสุด หากยังไม่มีจะแสดง preview ที่ยังไม่ล็อก
- GET /api/analysis/<fixture>?snapshot=<snapshot_id>: เปิดโมเดลรุ่นที่รายงานอ้างอิง แม้ pointer วิจัยถูกเปลี่ยนแล้ว

ไม่มีการเปิดปุ่ม public สำหรับแก้คำทำนาย/ผล หรือการเรียก provider ต่อการเปิดหน้าคู่ ข้อมูลย้อนหลังและ chunks ของรายงานเป็น immutable ใน D1 ผลการทำนายผูก dataset version เดิมเพื่อไม่ให้ H2H เปลี่ยนตามชุดข้อมูลใหม่

## การตีความโมเดล

ใช้ feature schema เดิม 11 ค่าและ state แยกลีก เปรียบเทียบ League/Elo/Poisson/Logistic/XGBoost ด้วย walk-forward ก่อนประเมิน 2025/26 ซึ่งเคยเห็นผลแล้ว จึงเรียก retrospective exploratory ไม่ใช่ final holdout ใหม่

ชุดโมเดล refit ใช้ผลถึงก่อน 2026-10-25 สำหรับสาธิตอนาคต ส่วน metrics ใช้ estimators ที่ฝึกก่อนแต่ละ fold/test ไม่ทดสอบ deployment refit กับ training labels

การประเมินสูง–ต่ำ/BTTS เพิ่มเป็น target แยก มี binary Log Loss/Brier/calibration และ CI แบบ resample วัน ไม่อ้าง accuracy จาก 1X2 ไปใช้กับสกอร์หรือชุด

มี diagnostic แยกเทียบกับโอกาสพื้นฐานลีกก่อนเกม (380 นัด/30 pseudo-games) เพื่อไม่ให้อัตราถูกสูงจากเหตุการณ์ที่เกิดบ่อยถูกตีความว่าโมเดลเก่ง ข้อมูลนี้ไม่ถูกใช้ปรับเกณฑ์หลังเห็น test

หลักฐานเดิม data/processed และ reports/selection-v1 ยังคงอยู่ ไม่มีการนำ 66 นัดผิดวันที่ EPL 2019/20 กลับเข้าฝึก

## โมเดล การทำซ้ำ และระบบอัตโนมัติ

Candidate อยู่ ml/models/recent-v2-<content hash>/; registry แยก active_version=null มี config, feature schema, dataset/source hashes, training cutoff, metrics, runtime และ checksums

ZIP และ SHA256 อยู่ reports/recent-v2/ พร้อม source manifest/attribution โดยไม่พึ่ง Actions Artifact อายุสั้นเป็นสำเนาถาวรเพียงแห่งเดียว การเผยแพร่ Release/การ promote ยังต้องได้รับอนุมัติและผ่านเกณฑ์ที่เกี่ยวข้อง

workflow recent-research.yml เป็น manual และไม่มี deploy/promotion; CI เตรียมข้อมูลและรัน tests/seed/UI ใหม่จาก snapshot เดียวกัน ยังไม่ได้รัน workflow บน GitHub จริงและยังไม่มี Cloudflare production deployment

ข้อจำกัดที่ยังต้องแก้ก่อน live: สิทธิ์ฤดูกาลปัจจุบันของบัญชี API, coverage และ paging จริง, mapping/เวลาเตะที่ยืนยัน, freshness ของผล, optional player/stat endpoints, calibration/validation ลีกและตลาดใหม่, prospective snapshots และการทดสอบถูกครบชุดจริง
