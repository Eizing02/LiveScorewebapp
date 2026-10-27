# งานวิจัยความแม่นยำรุ่น 3

โค้ดและฐานข้อมูลอยู่ที่ `D:\Football Prediction AI` แยกจากโปรเจกต์เดิม โมเดลรุ่นนี้เป็น research candidate; active registry ยังว่าง, `MODEL_AUTO_PROMOTE=false`, `LIVE_API_ENABLED=false` หน้า “เป้าความแม่นยำ” แสดงผลจริงพร้อมจำนวนคู่และช่วงความไม่แน่นอน

## รันหลังสร้าง recent-v2 แล้ว

```powershell
python -m ml.precision.experiment
python -m scripts.verify_precision
python -m scripts.precision_diagnostics
python -m scripts.prepare_precision
python -m scripts.package_precision
npm run db:seed:precision:local
```

`experiment` สร้าง features, ฝึกโมเดลตามช่วงเวลา, เลือกจาก validation และประเมินย้อนหลัง แยก artifact ที่ refit สำหรับอนาคตออกจากตัวที่ใช้คำนวณ test; `verify_precision` ฝึกซ้ำทั้งงานและเทียบ checksum/metrics/selection เวอร์ชันรวม runtime ด้วย จึงไม่คาดหวัง hash ข้ามระบบปฏิบัติการตรงกัน

`prepare_precision` วิเคราะห์เฉพาะโปรแกรมสมมติเดิม เก็บเวลาสร้างจริง และไม่สร้างคำทำนายย้อนหลังเมื่อเวลาเตะผ่านแล้ว หากต้องทดสอบ UI ในอนาคต ใช้ `--mock-clock 2026-10-25T18:00:00Z` เฉพาะ fixture สมมติเท่านั้น จะติด `timestamp_basis=simulated_mock_clock` และเก็บ `record_created_at` จริง ห้ามนับเป็นหลักฐาน prospective

`db:seed:precision:local` นำเข้า snapshot และรายงานลง D1 เครื่องนี้ พร้อมเปลี่ยน pointer ของหน้าวิจัยเท่านั้น ไม่มีการเปลี่ยน active production model รายงานย้อนหลังยังอ่านได้เมื่อปิด mock เพื่อใช้ตรวจหลักฐาน แต่ไม่มีการอนุมัติโมเดลจากการอ่าน

## หลักฐานล่วงหน้าแบบส่วนตัว

```powershell
python -m ml.precision_shadow --days 7
```

คำสั่งนี้เรียก public OpenLigaDB สองครั้งสำหรับ Bundesliga และ 2. Bundesliga ไม่มี API-Football ไม่ใช้ key และไม่เผยแพร่คู่แนะนำ เก็บ response/hash/first_seen/คำทำนายก่อนเตะเป็นไฟล์ immutable ใน `data/processed/precision-v3-shadow` หากชื่อทีมไม่ยืนยันจะข้าม รายงานสรุปอยู่ที่ `reports/precision-v3/prospective-collection.json`

รายการเหล่านี้ยังไม่เป็นการรับรอง: source จากชุมชนต้องตรวจ mapping/วันเวลา, feature feed อาจไม่ปัจจุบัน, เวลาท้องถิ่นยังไม่มีพยานภายนอก และยังไม่มีผลแข่ง ตัว payload จาก engine ใช้ marker `mock_research` เดิมแต่ record ชั้นนอกระบุ `private_prospective_research_unverified` ชัดเจน ไม่มีการนำเข้า UI สาธิตซึ่งใช้โปรแกรมสมมติ การเก็บซ้ำต้องนับ fixture/policy เดิมเพียงครั้งเดียวเมื่อประเมินในอนาคต ยังไม่ได้ทำระบบ settlement สำหรับ collector นี้

## ก่อนต่อ API-Football จริง

ตรวจบัญชีจริงแยกแต่ละลีก/ฤดูกาลและ endpoint: coverage, season availability, daily/minute rate limit/reset และการเข้าถึง fixtures, injuries, lineups, fixture/player statistics ไม่ถือว่า xG มีจนกว่าจะตรวจ payload ของบัญชีได้ ข้อมูลขาดต้องเป็น unknown ไม่ใช่ไม่มีคนเจ็บ/ไม่มีการยิง

งบ requests ต้องคำนวณจาก `league/season coverage checks + fixture date pages + unique team/fixture detail calls + retries` โดย cache ตาม endpoint/params, เก็บ seen_at/available_at และสงวนโควตาไว้ ไม่เรียกทุก endpoint ทุกคู่ด้วยจำนวนเดา ขณะนี้ไม่มี live test และจำนวน API-Football requests เป็น 0

`ml/enrichment.py` เตรียมสัญญาข้อมูลไว้: license/coverage ต้อง verified, available_at และ first_seen_at ต้องไม่เกิน prediction time, สถิติ xG/shots ของ target match ห้ามเข้าฟีเจอร์ก่อนเกม ใช้ได้เฉพาะแมตช์ก่อนหน้าที่จบแล้ว ผลของฟีเจอร์เสริมต้องทดสอบ ablation บนช่วงใหม่ก่อนเลื่อนรุ่น

## เก็บรุ่นและย้อนกลับ

ZIP มี JSON weights, feature schema, cutoff, protocol, metrics, checksum, training code, runtime/dependency lock และ source manifest เก็บ local versioned files ไว้ถาวร หลังอนุมัติการเผยแพร่จึงนำ ZIP ที่ตรวจแล้วขึ้น immutable GitHub Release; Actions artifact 14 วันเป็นสำเนาตรวจงาน ไม่ใช่ที่เก็บถาวรเพียงแห่งเดียว

ไม่มี production model ถูกเลื่อนรุ่นในรอบนี้ หากทดสอบเปลี่ยนรุ่นบนหน้าวิจัย ให้ตั้งค่า `RECENT_RESEARCH_CANDIDATE` กลับเป็น candidate ก่อนหน้าและใช้ snapshot ID ที่ล็อกไว้ ห้ามแก้ payload เดิม เกณฑ์ production promotion ยังต้องผ่านผล prospective ที่ตรวจแล้วและการอนุมัติ
