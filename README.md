# สนามข้อมูล — Football Prediction AI

หน้าแรกเป็นโปรแกรมบอลหน้าเดียว ธีมขาว–ฟ้า–แดง: เลือกรายการด้านซ้าย ดูคู่ตรงกลาง วิเคราะห์ด้านขวา; แท็บเล็ตใช้สองส่วนและมือถือสลับรายการ/วิเคราะห์พร้อมปุ่มกลับ ค้นหา กรองประเทศ/ลีก/สถานะ ติดตามและพับลีก แบ่งหน้า 25 คู่ พร้อมแท็บคู่เด่นและผลการทำนาย ดู [ผลพัฒนาหน้าใหม่และข้อจำกัด](docs/ONE_PAGE_IMPLEMENTATION_TH.md), [มาตรฐานหน้าจอ](DESIGN.md) และ [ผลตรวจจริง](reports/one-page/verification.json)

Repository นี้เผยแพร่โค้ด เอกสาร ผลวิจัยย้อนหลัง และ model artifacts ส่วนคีย์ ฐานข้อมูล local ข้อมูล API ส่วนตัวและภาพหน้าจอจากข้อมูล API ไม่ถูกส่งขึ้น GitHub เอกสารบางหน้าจึงอ้างถึงหลักฐานที่อยู่เฉพาะบนเครื่อง ดู [ขอบเขตการเผยแพร่และการเริ่มจาก clone ใหม่](docs/GITHUB_PUBLICATION_TH.md) การพุชโค้ดไม่ deploy หรือเปิดระบบดึงข้อมูลอัตโนมัติ

โปรแกรมเรียงลีกใหญ่ก่อนตามลำดับที่อนุมัติ โดย API เรียงก่อนแบ่งหน้า เมนู ตัวกรอง และกลุ่มคู่ใช้ลำดับเดียวกัน ภายในลีกเรียงเวลาเตะ ดู [กติกาและไฟล์ตั้งค่าลำดับลีก](docs/LEAGUE_ORDER_TH.md)

แคชรอบ 27 ต.ค. 2026 เวลาไทย 06:00 ถึงก่อน 28 ต.ค. 06:00 แสดง 332 คู่จาก 112 รายการแข่งขัน รวมบอลถ้วยและลีกอื่น ๆ ที่เคยถูกตัวกรอง 5 ลีกซ่อนไว้ ส่วนรอบ 28 ต.ค. มี 266 คู่จากแหล่งข้อมูลที่ยังไม่ครบวันที่ 29 ตัวเลขเป็นข้อมูลที่บันทึกไว้วันที่ 27 ต.ค. ไม่ใช่ผลสด การแสดงโปรแกรมได้ไม่แปลว่ามีโมเดลทำนายได้ทุกคู่

งานนี้ใช้ Impeccable 4.8.0 ตามแผนที่อนุมัติแล้ว อ่าน [คู่มือ 24 workflows](docs/IMPECCABLE_GUIDE_TH.md) และ [หลักฐานตรวจแก้ 4 ข้อ](reports/one-page/finish-verdict.md) การตรวจนี้ครอบคลุมรายการแก้ดังกล่าว ไม่ใช่คำรับรองว่าทั้งระบบพร้อม Production

สำหรับเครื่องนี้ที่เตรียมข้อมูลและ local D1 แล้ว เปิดสอง terminal ใน `D:\Football Prediction AI` รัน `npm run dev:api` และ `npm run dev` แล้วเปิด `http://127.0.0.1:5173` การกดอ่านแคชในเว็บไม่เรียก API ภายนอก ไม่ต้องฝึกโมเดลใหม่เพื่อเปิดหน้าจอ

หากต้องนำแคชเดิมเข้า catalogue อีกครั้ง ใช้ `.\.venv\Scripts\python.exe -m scripts.import_program --import-local` หลัง `npm run db:migrate:local` และเปิด local API แล้ว คำสั่งตรวจ checksum ของแคชและส่งเข้าเฉพาะ loopback; ไม่ดึงโปรแกรมใหม่จากผู้ให้บริการ โลโก้เพิ่มเติมโหลดจาก CDN ภาพแบบจำกัด ID และมี cache/ตัวอักษรสำรอง โดยไม่ส่ง API key

โปรเจกต์ใหม่แยกจาก D:/Live score Project: historical pipeline + โมเดลจริง 5 แบบ + temporal backtest + React ภาษาไทย + Worker/D1 mock integration

เพิ่ม Match Centre: รอบวันไทย 06:00–06:00, แยกลีก, H2H/ฟอร์ม/เหย้า–เยือน, สูง–ต่ำ/BTTS/สกอร์คาดหมาย, สรุปคู่เดี่ยวและชุดทดลอง 3/5 คู่ พร้อม immutable snapshots และระบบตรวจผล ชุดย้อนหลังใหม่ใช้เฉพาะ 2021-10-25 ถึงก่อน 2026-10-25 จำนวน 17,027 นัดจาก 12 ลีก รายละเอียดอยู่ใน `docs/RECENT_EXPANSION_TH.md` และ `reports/recent-v2/EXPANSION_REPORT_TH.md` สิทธิ์ข้อมูลเพิ่มดู `data/ATTRIBUTION.md`

เชื่อม API-Football บัญชีฟรีแบบจำกัดโควตาและเพิ่ม local research pipeline แล้ว มีข้อมูลวิจัยรวม 17,043 นัดจากฐานเดิมและผล API ใหม่ 16 นัด ยังไม่มี production deployment หรือ active model ที่ promote แล้ว รายละเอียดและข้อจำกัดอยู่ใน [ผลพัฒนา API และระบบวิจัยก่อนแข่ง](docs/LIVE_RESEARCH_IMPLEMENTATION_TH.md)

## รันบนเครื่อง

ต้องมี Node 24, Git และ Python 3.12 จาก environment ที่อนุญาตให้ใช้ NumPy/SciPy/XGBoost บน Windows รอบนี้ใช้ Python runtime ที่ Codex จัดมา และสร้าง `.venv` ไว้แล้ว

```powershell
cd "D:\Football Prediction AI"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
npm ci
python -m scripts.fetch_history
python -m ml.pipeline
python -m pytest -q
python -m ml.evaluate
python -m scripts.prepare_demo
python -m scripts.source_snapshot
python -m scripts.fetch_additional_history
python -m ml.expanded
python -m scripts.crosscheck_history
python -m ml.recent_evaluate
python -m ml.market_benchmarks
python -m scripts.prepare_centre
python -m scripts.package_recent_model
python -m ml.precision.experiment
python -m scripts.verify_precision
python -m scripts.precision_diagnostics
python -m scripts.prepare_precision
python -m scripts.package_precision
npm run db:migrate:local
npm run db:seed:local
npm run db:seed:selection:local
npm run db:seed:centre:local
npm run db:seed:precision:local
npm run dev:api
```

เปิด terminal อีกช่องในโฟลเดอร์นี้แล้ว `npm run dev` เปิด URL ที่ Vite แสดง โดยปกติ http://127.0.0.1:5173 หน้าเว็บอ่านเฉพาะ local Worker ไม่อ่าน provider จาก browser โปรเจกต์นี้ไม่ต้องติดตั้ง/เชื่อม MongoDB

Match Centre มีโปรแกรมสมมติ 15 รายการสำหรับรอบสาธิต 26 ตุลาคม 2026 และตัวอย่างขอบเวลา 06:00 ของรอบถัดไป สถิติและผลโมเดลคำนวณจากชุดย้อนหลังใหม่ มีป้ายบอกชัดว่าไม่ใช่โปรแกรมจริง หน้า “ผลวิจัย 5 ปี” แสดงการประเมินย้อนหลังที่เคยเห็นช่วงทดสอบแล้ว; หน้า “ผล Backtest เดิม” เก็บหลักฐานเดิมแยกกัน Fixture จำลองเดิมสามคู่ยังอยู่สำหรับ integration tests เดิม

## ทดสอบ

การทดสอบ API-Sports จริงครั้งแรกผ่านแบบ date endpoint และมีแท็บ “โปรแกรม API จริง” แสดงแคชแยกจากคู่จำลอง ยังไม่เปิด automatic sync หรือคำทำนายจริง ดู [ผลเชื่อมต่อและวิธี refresh](docs/API_CONNECTION_TH.md) ห้ามใช้ season catalog เป็นหลักฐานว่าบัญชีเข้าถึงฤดูกาลนั้นได้

```powershell
python -m pytest -q
python -m ruff check ml scripts
npm run lint
npm run typecheck
npm test
npm run build
npm run worker:check
npx playwright install chromium
npm run test:ui
```

`worker:check` เป็น dry-run ของการ bundle ไม่เผยแพร่ Worker ทุกคำสั่ง D1 ข้างต้นมี --local ไม่มี remote DB credentials

## ข้อมูลและโมเดล

หน้า “เป้าความแม่นยำ” ใช้ Precision v3 ที่ฝึกจริงด้วย 58 features และ ensemble Logistic/Dixon–Coles ผลย้อนหลังคัด 121/3,220 คู่ ถูก 103 (85.12%, coverage 3.76%, Wilson 95% CI 77.71–90.38%) ทุกคู่ยังถูก 50.56% และยังไม่ผ่านเกณฑ์ยืนยันรายลีก/อนาคต โมเดลยังเป็น research candidate ดู [รายงานละเอียด](reports/precision-v3/PRECISION_REPORT_TH.md) และ [คู่มือรัน/เชื่อม API](docs/PRECISION_V3_OPERATIONS_TH.md)

- `ml/config/policy.json`: frozen protocol/acceptance ก่อนเห็นผล holdout
- `ml/pipeline.py`: normalize สกอร์สองแบบ, identity/league mapping, dedup, status/date validation, quarantine และ dataset hash
- `data/processed/`: accepted/quarantine/excluded JSONL, manifest, quality report และ correction log (ignored, สร้างซ้ำได้)
- `reports/quality-by-season.csv`: จำนวนรับ/กัก/ไม่นำเข้าแยกทุกลีกและฤดูกาล
- `ml/models.py`: point-in-time features, league prior, Elo และ Poisson
- `ml/evaluate.py`: walk-forward Logistic/XGBoost, final holdout, uncertainty และ calibration
- `reports/backtest.json`, `metrics.csv`, `calibration.png`: หลักฐานผลจริง
- `ml/models/`: JSON artifacts + metadata/checksums + registry; active=null และ MODEL_AUTO_PROMOTE=false
- `ml/batch.py`: offline batch prediction; default baseline เมื่อยังไม่มี active model
- `apps/api/`: public reads, mock adapter, quota/cache, signed internal calls, sync/locking/evaluation
- `db/migrations/`: D1 schema, unique constraints, immutable prediction triggers
- `.github/workflows/`: CI, training, offline batch และ release ที่ต้องอนุมัติ

รัน importer ซ้ำได้ผล dataset version เดิม การฝึกซ้ำใช้ seed/versions เดิม Registry version รวม dataset, policy และ hash ของ training code ไม่เขียนทับ artifact เวอร์ชันเดิมถ้าเนื้อหาเปลี่ยน ห้ามถือว่า all-source rows ที่ไม่มีคะแนนคือ 0–0

## เอกสาร

- [Architecture Decision Record](docs/ADR-0001.md)
- [วิธีประเมินและข้อจำกัด](docs/ML_METHODOLOGY.md)
- [การเชื่อมจริง ความปลอดภัย โควตา และ rollback](docs/OPERATIONS.md)
- [หลักฐานงานและผลทดสอบ](docs/ACCEPTANCE.md)
- [แนวคิดและผลทดลองการคัดกรองแบบละเอียด](docs/DETAILED_FILTERING_TH.md)

## การคัดกรองแบบละเอียด

หน้า “การคัดกรอง” ใช้ผลทดลองที่ล็อกกติกาบน validation แล้วทดสอบช่วงใหม่ 2025/26 โมเดลสำหรับช่วงใหม่นี้ฝึกจากข้อมูลก่อน 2025/26 เท่านั้น กติกาที่เลือกคัด 67 จาก 1,066 คู่ ถูก 57 คู่ (85.07%) แต่ยังไม่ผ่านเกณฑ์ยืนยันเพราะ sample รวมและ EPL ไม่พอ จึงแสดงเป็น research_only

ตรวจดูได้ทั้งคู่ที่ผ่าน/ไม่ผ่าน เหตุผลรายคู่ probability ก่อน/หลัง calibration ประวัติก่อนวันแข่ง ความเห็นของโมเดล และเหตุผลที่ยังเผยแพร่ live ไม่ได้ เปลี่ยนตัวกรองในหน้าจอเพื่อดูข้อมูล ไม่ได้เปลี่ยนกติกาทำนายหรือเลือก threshold ใหม่ตามผล test

ผลทดลองอยู่ใน `reports/selection-v1/` และเก็บหลักฐานลง local D1 แบบ immutable ผ่าน migration 0003 หากต้องสร้าง SQL จากหลักฐานเดิมใหม่ให้ใช้ `python -m scripts.prepare_selection` แล้วรัน `npm run db:seed:selection:local` การประเมินใหม่ด้วย `python -m ml.selective` จะปฏิเสธการเขียนทับผล test ที่เคยประเมินแล้ว

Historical source มี CC0-1.0: https://github.com/openfootball/football.json/blob/e6744429ee395bc86f247348c6184bb08d4eb361/LICENSE.md การใช้ข้อมูล provider/โลโก้มีเงื่อนไขแยกจาก source code นี้
