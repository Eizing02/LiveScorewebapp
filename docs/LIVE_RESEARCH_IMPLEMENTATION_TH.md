# ผลพัฒนา API-Football และระบบวิจัยก่อนแข่ง

อัปเดต 26 ตุลาคม 2026 ตาม Asia/Bangkok ใน `D:\Football Prediction AI` งานนี้เพิ่มโค้ดจริงและทดสอบกับ local Worker/D1 ไม่แก้โปรเจกต์ `D:\Live score Project` ไม่มี production deployment, remote D1 write, การซื้อบริการ หรือการเลื่อน active model

## ผลที่ใช้งานได้บนเครื่อง

- หน้า **โปรแกรม API จริง** เลือกวัน รอบวัน/คืนนี้ และลีกได้ นับวัน 06:00 ถึงก่อน 06:00 ของวันถัดไป แยกจากวันรีเซ็ตโควตา API เวลา 07:00 ไทย
- กดคู่เพื่อดูฟอร์ม 5/10/20 นัด, เหย้า–เยือน, ยิง/เสียเฉลี่ย และ H2H แยกลีกเดียวกันหรือทุกรายการที่มีข้อมูล ตัวอย่าง Barcelona–Real Madrid มี H2H ลีก 9 นัด หรือทุกรายการ 19 นัดในขอบเขตย้อนหลังที่ใช้
- แสดงนักเตะขาด, สถานะตัวจริง, xG จากเกมก่อน และคำทำนาย API ตามเวลาที่รับจริง ข้อมูลว่างแสดงว่าไม่ทราบ รายการนักเตะขาดตัวอย่าง 18 แถวถูก deduplicate เหลือ 9 คน
- แยกคำทำนายของเราออกจาก forecast ของ API ไม่เฉลี่ยเปอร์เซ็นต์เข้าด้วยกันโดยไม่มีผลทดสอบรองรับ สถิติของเกมเป้าหมายที่รับหลังเริ่มเกมอยู่ในส่วนหลังแข่ง
- มี pipeline สร้างคำทำนายก่อน kickoff เท่านั้น เก็บ feature values, แหล่งข้อมูล, เวลาที่ทราบ, รุ่นโมเดล/runtime และ checksum เป็น snapshot แก้ย้อนหลังไม่ได้
- สรุปรายวันและชุดทดลอง 3/5 คู่ใช้กติกาที่มีอยู่ หากคู่ผ่านไม่พอจะไม่ฝืนจัดชุด การมีเปอร์เซ็นต์สูง–ต่ำหรือสกอร์ที่เป็นไปได้ยังไม่ถือว่าตลาดนั้นผ่านการยืนยันความแม่นยำ

คำว่า `private_research` เป็นสถานะงานวิจัย ระยะนี้ให้บริการเฉพาะ localhost ส่วน flag สำหรับอ่านข้อมูลจริงปิดในค่าเริ่มต้นของ Wrangler ก่อนเปิดบนคลาวด์ต้องกำหนดสิทธิ์เข้าถึง เช่น Cloudflare Access และผ่านการอนุมัติแยกต่างหาก

## ข้อมูลจริงที่นำเข้า

| รายการ | จำนวน/สถานะ |
|---|---:|
| ชุดย้อนหลังเดิม 12 ลีก | 17,027 นัด |
| ผล FT 90 นาทีจาก API ที่เพิ่มและผ่านเกณฑ์วิจัยภายใน | 16 นัด |
| ชุดข้อมูลวิจัยรวมล่าสุด | 17,043 นัด |
| Fixture จริงจากสองวันปฏิทินที่เก็บไว้ | 18 คู่ |
| คู่ในรอบ 25 ต.ค. 06:00 → 26 ต.ค. 06:00 | 16 คู่ |
| Team mappings ผ่านการทบทวนชื่อ/ลีก/ประเทศ/หลักฐานต้นทาง | 36 ทีม |
| Fixture API ที่กักจากการตรวจโครงสร้างล่าสุด | 0 |
| ความขัดแย้งระหว่างผลใหม่กับชุดเดิม | 0 |
| คำทำนายของเราใหม่ก่อน kickoff ในการรันนี้ | **0** |

18 fixture เป็นข้อมูลหลายเวลาและหลายสถานะ ไม่ใช่ 18 คู่อนาคต ณ เวลาประมวลผลทุกคู่เริ่มแข่งแล้ว จึงไม่มีการสร้างคำทำนายย้อนเวลา สองคู่ยังไม่มีผล FT ที่รับเข้าได้ตามข้อมูลที่บันทึก ไม่เติมผลจากการคาดเดา

| ลีก | เดิม | เพิ่ม FT จาก API | รวมเพื่อวิจัย |
|---|---:|---:|---:|
| Premier League | 1,860 | 5 | 1,865 |
| La Liga | 1,864 | 4 | 1,868 |
| Bundesliga | 1,510 | 2 | 1,512 |
| Serie A | 1,850 | 5 | 1,855 |
| Championship | 2,687 | 0 | 2,687 |
| Ligue 1 | 1,612 | 0 | 1,612 |
| Eredivisie | 1,504 | 0 | 1,504 |
| Primeira Liga | 1,513 | 0 | 1,513 |
| Bundesliga 2 | 1,489 | 0 | 1,489 |
| Segunda División | 453 | 0 | 453 |
| Serie B | 379 | 0 | 379 |
| Ligue 2 | 306 | 0 | 306 |

รายลีก/ฤดูกาลทั้ง 60 แถวอยู่ใน [data-by-league-season.csv](../reports/live-research/data-by-league-season.csv) และ dataset version/content checksum อยู่ใน [latest-dataset.json](../reports/live-research/latest-dataset.json) ไฟล์ accepted JSONL รวมถูกเก็บตามเวอร์ชันใต้ `data/processed/live-research/training-datasets/` ไม่เขียนทับชุดย้อนหลังที่ประเมินแล้ว

Team mapping รอบนี้เป็นการทบทวนภายในจาก provider ID, ชื่อ, ลีก/ประเทศ และชื่อใน historical snapshot ไม่ใช่การรับรองตัวตนจากแหล่งทางการอิสระ จึงยังไม่อนุมัติ production ชื่อหรือ ID ใหม่ที่ไม่ตรง mapping จะไม่จับคู่ด้วย fuzzy matching อัตโนมัติ

ข้อมูลที่ไม่นำเข้าเดิมอีก 902 แถวยังคงแยกไว้ ข้อมูลกักเดิม 4,363 แถวยังคงอยู่: สกอร์หาย 3,272, ฤดูกาลเก่าปิดแล้วแต่ข้อมูลไม่ครบ 556, ยังไม่ยืนยันการแข่ง 470, รอบนอก regular season 35, mapping ข้ามแหล่งไม่สำเร็จ 17, คะแนนขัดกัน 4, ผลทางปกครอง 3, วันขัดกัน 2, ยกเลิก 2 และเลื่อนแข่ง 2 เหตุผลเหล่านี้รวม 4,363 แถว ไม่ใช่ทั้งหมดเป็นข้อผิดพลาดสกอร์ ส่วน 66 นัด EPL 2019/20 ที่กักใน audit เดิมยังไม่ถูกแก้หรือรับกลับ และอยู่นอกช่วง recent-v2 ที่เริ่มปี 2021

## กระบวนการข้อมูลและนาฬิกา

1. เก็บ response ที่อนุญาตตาม hash และเวลารับจริง ไม่เก็บ raw `/status` ที่มีข้อมูลส่วนบุคคล
2. ตรวจ fixture ID, ทีม, ลีก/ประเทศ, UTC timestamp, competition date และ business date ไทย แยกผล 90 นาที/ต่อเวลา/จุดโทษ ไม่แปลง null เป็น 0–0
3. เก็บ observations แบบเพิ่มเวอร์ชัน การเปลี่ยน kickoff ทำให้เกิด occurrence ใหม่ ผลทางปกครอง/ยกเลิก/เลื่อนแข่งไม่ถูกนับเป็นชัยชนะปกติ
4. ผล FT ใหม่ที่ผ่านเกณฑ์สร้าง dataset version ใหม่ ถ้าวัน/สกอร์ขัดกับข้อมูลเดิมให้กัก ไม่แก้ข้อมูลเดิมเงียบ ๆ เวลาที่รู้ผลใช้หลักฐานแรกของผลเดียวกัน
5. คำนวณ 58 features จากวันที่ก่อน cutoff ของลีกเท่านั้น และรับเฉพาะข้อมูลที่ทราบก่อนเวลาทำนาย แยก cutoff ของ features ออกจาก cutoff ที่ใช้ฝึกน้ำหนัก
6. ใช้น้ำหนัก Precision v3 เดิมกับสถานะข้อมูลใหม่ โมเดลประตู Dixon–Coles รองรับการ refit ทุกสองเดือนตามพารามิเตอร์เดิม และเก็บ component/checksum แยกเมื่อเกิดการ refit
7. ล็อก stages `initial`, `pre_lineup`, `final` ก่อนแข่งเท่านั้น ประเมินหลักจาก initial แรกต่อ fixture/occurrence เพื่อลดการนับซ้ำ การแก้ผลแข่งสร้าง evaluation revision โดยรักษาคำทำนายเดิม

D1 มี trigger ตรวจความเป็น immutable, เวลา, source observation/feature และผลรวม probability Python มี accepted dataset ที่ตรวจ hash และ signed import/export สำหรับกู้ normalized state จาก D1 กลับมาใน runner ใหม่ได้

## โควตาและข้อจำกัดบัญชีที่พิสูจน์แล้ว

บัญชี Free เรียกแบบ date-only ได้ แต่ season filter, fixtures `ids`, injuries `ids` และวันที่ 27 ต.ค. ที่ลองขณะตรวจถูกปฏิเสธ เส้นทางที่ทราบว่าใช้ไม่ได้ถูกปิดก่อนเรียก provider ไม่ทำ retry หรืออ้างว่าจะประหยัดด้วย batching ที่ยังใช้ไม่ได้ ดู [optional-batch-proof.json](../reports/live-research/optional-batch-proof.json)

รวมตั้งแต่เริ่มเชื่อมมี 22 HTTP attempts เป็น status 2 และ billable attempts ที่กันงบไว้ 20 ครั้ง ตัวเลขนี้เป็นการบันทึกคำขอ ไม่ใช่ใบยืนยันการคิดโควตาจากผู้ให้บริการทุกครั้ง Header ที่ยืนยันได้ล่าสุดรายงาน remaining 86 ก่อนคำขอทดสอบที่ถูกปฏิเสธสามครั้ง หลังรวมหลักฐานและการกันงบ local D1 ใช้นโยบายเผื่อเหลือ 80 ณ การตรวจครั้งนี้ การทดสอบระบบรอบสุดท้ายอ่านแคชและ local Worker ไม่มีการเรียก API เพิ่ม

- ใช้ broker กลาง D1 สำหรับ reserve/settle ร่วมกันระหว่าง Worker/Python แทนตัวนับ cloud แยกไฟล์
- กันงบงานปกติ 65/day, ช่องผลแข่งเร่งด่วนถึง 85/day, สำรองอย่างน้อย 15; `/status` ไม่คิด daily cost แต่ยังต้องเว้นระยะ
- เว้นอย่างน้อย 12.1 วินาที และเคารพ minute limit ที่ต่ำกว่า ค่าตั้งต้นแบบเผื่อ 5/min รองรับ header ที่ตรวจได้ 10/min โดยไม่เร่งเกินค่าเผื่อ
- reconcile daily remaining โดยไม่เพิ่มกลับจาก response เก่า, settle ticket เดียวซ้ำไม่ได้, 429/rate error ทำให้พักการเรียก
- Collector context ใช้ไม่เกิน 3 billable/run เรียก lineups ใกล้ kickoff ไม่เกินสองครั้ง เว้น 15 นาที และหยุดก่อนแข่ง ข้อมูลหลังจบเกมใช้สร้างฐานสำหรับเกมถัดไป
- แผนหนึ่งรอบสูงสุด 7 HTTP / 5 billable เมื่อ refresh สองวันพร้อมเก็บ context ตารางที่เตรียม 8 รอบ/วันจึงมีเพดานตามแผน 40 billable ก่อนขอเพิ่ม ยังไม่ได้เปิด schedule จริง และบางรอบอาจได้ข้อมูลวันถัดไปเพียงบางส่วน

นโยบายรีเซ็ต direct API ตรวจจาก [เงื่อนไข API-Football](https://www.api-football.com/terms) ความสามารถแต่ละ query ยังต้องตรวจจาก payload จริงร่วมกับ [เอกสาร v3](https://www.api-football.com/documentation_v3) ไม่อนุมานสิทธิ์จาก league catalog เพียงอย่างเดียว

## สถานะโมเดลและความแม่นยำ

โมเดลสกอร์ Precision v3 เคยฝึกจริงแล้ว รุ่น `precision-v3-9f46ca6392a2` น้ำหนักและไฟล์หลักฐานเดิมไม่ถูกเปลี่ยน ผลย้อนหลังคัด 121/3,220 คู่ ถูก 103 = 85.12%, coverage 3.76%, Wilson 95% 77.71–90.38%; ทุกคู่ถูก 50.56% ผลนี้เป็น retrospective research ที่ช่วงทดสอบเคยถูกตรวจแล้ว ยังไม่ใช่การรับรองว่าจะทำได้ 70–80% ในอนาคต ดู [รายงานรุ่นเดิม](../reports/precision-v3/PRECISION_REPORT_TH.md)

รอบนี้เพิ่มทางฝึก Challenger จริง: Logistic และ XGBoost พร้อม ablation `score58`, `+xG`, `+availability`, `+provider` ใช้ median จาก train เท่านั้นและ missing indicators, แบ่งกลุ่มวันที่ 60/20/20, เลือกจาก validation log loss ก่อนอ่าน test และไม่เลื่อนโมเดลอัตโนมัติ มีการทดสอบเส้นทาง fit/save ด้วยข้อมูลจำลองที่แยกออกไปใน temporary test directory ผลจำลองนั้นไม่ถูกใช้เป็นความแม่นยำของโปรเจกต์

**ยังไม่ได้ฝึก Challenger ด้วยข้อมูลเสริม API จริง** เพราะมีคำทำนายก่อนแข่งที่ทราบผลแล้ว 0 ตัวอย่าง ขณะที่ protocol กำหนดอย่างน้อย 1,000 fixture, 60 วันที่ต่างกัน และ 300 แถวที่มีข้อมูลเสริมจริง เกณฑ์ถูกล็อกก่อนสะสมข้อมูลใหม่ ไม่ลดเกณฑ์เพื่อให้เกิดผลดูดี [ผลตรวจ training readiness](../reports/live-research/challenger-training.json)

การประเมินจริงใหม่รายงาน accuracy/log loss/Brier/calibration เป็น null เมื่อ n=0 มีจำนวนตัวอย่าง, selected coverage, Wilson interval, แยกรายลีก และ benchmark forecast API ต่างหาก ปัจจุบันมี API forecast ก่อนแข่ง 1 ชุดที่ยังไม่มีผลจบในแคชสำหรับตรวจ [ผล prospective](../reports/live-research/prospective-evaluation.json)

## ไฟล์หลักที่เพิ่ม/แก้

| ส่วน | ไฟล์ |
|---|---|
| Mapping/query policy | `ml/config/provider_identity_v1.json`, `provider_access_policy.json`, `ml/provider_policy.py` |
| ข้อมูล/ฟีเจอร์/ทำนาย | `ml/live/normalize.py`, `ledger.py`, `context.py`, `predict.py`, `pipeline.py` |
| ประเมิน/ฝึกรุ่นใหม่ | `ml/live/evaluate.py`, `challengers.py`, `ml/config/live_challenger_v1.json` |
| Collector/ตัวนับกลาง | `scripts/live_sync.py`, `collect_live_context.py`, `api_football_probe.py`, `api_football_schedule.py`, `verify_provider_batch.py`, `ml/provider_broker.py` |
| Worker API | `apps/api/live.ts`, `live-import.ts`, `live-export.ts`, `provider-broker.ts`, `provider.ts`, `index.ts`, `jobs.ts`, `types.ts` |
| D1 | migrations `0006`–`0010`: observations, feature/prediction snapshots, quota broker, guards, current heads และ goal components |
| กติกา/หน้าจอ | `packages/football/types.ts`, `selection.ts`, `provider-leagues.ts`, `apps/web/src/ProviderPreview.tsx`, `LiveDetail.tsx`, `App.tsx` |
| Automation/config | `.github/workflows/live-research.yml`, `wrangler.jsonc`, `.gitignore`, `.gitattributes`, package scripts |
| Tests | `ml/tests/test_live_research.py`, `test_live_evaluation.py`, `test_live_collector.py`, `test_api_football_probe.py`, `tests/live.test.ts`, `provider-broker.test.ts`, `provider.test.ts`, UI live-detail/provider-preview |
| หลักฐาน/แพ็กเกจ | `reports/live-research/`, `scripts/package_live.py`, README และเอกสารนี้ |

โมเดล/โค้ดฝึกรุ่น v3 ที่มี source hash ใน metadata ยังตรงกับหลักฐานเดิมทั้งหมด มี archive โมเดลถาวรบนเครื่อง และแพ็กเกจ integration พร้อม checksum แยก ห้ามใช้ Actions artifact ที่หมดอายุเป็นที่เก็บโมเดลเพียงแห่งเดียว GitHub Releases และการเผยแพร่ยังไม่ได้ดำเนินการ

## วิธีใช้รอบถัดไป

จาก `D:\Football Prediction AI` ใช้ `.venv` เดิมและ `.dev.vars` ที่ ignored ไว้ ห้ามคัดลอก key ลง source หรือ browser

```powershell
npm run db:migrate:local
npm run dev:api
# อีก terminal: ประมวลผลแคชและนำเข้า local D1 โดยไม่เรียก provider
.venv\Scripts\python.exe -m scripts.live_sync --execute --hydrate --import-local
npm run dev
```

เปิด `http://127.0.0.1:5173/?view=provider&live_date=2026-10-25` เพื่อดูข้อมูลที่มีจริง วันที่อื่นอาจยังไม่มีข้อมูล ไม่ตีความว่าไม่มีการแข่งขัน

```powershell
# แสดงงบอย่างเดียว ไม่เรียก API
.venv\Scripts\python.exe -m scripts.live_sync --refresh --enrich --import-local
# ใช้เมื่อจะอัปเดตจริง: สูงสุด 7 HTTP / 5 billable ผ่าน broker
.venv\Scripts\python.exe -m scripts.live_sync --execute --hydrate --refresh --enrich --import-local
.venv\Scripts\python.exe -m ml.live.challengers --check-only
```

ขั้นถัดไปคือสะสม fixture อนาคตและ context ที่รับก่อนแข่ง ตรวจผลเมื่อมี FT แล้วจึงประเมินแบบ prospective เพิ่ม identity ที่ยังไม่อยู่ใน mapping ผ่านการทบทวนก่อนขยายลีก สำหรับคลาวด์มี workflow พร้อม signed hydration/import และ protected environment แต่ยังต้องอนุมัติ remote infrastructure, กำหนด access control, durable model store และวัด CPU/D1/GitHub minutes จริงภายใต้โควตาฟรีก่อนเปิดใช้งาน `MODEL_AUTO_PROMOTE=false` คงเดิม

ผลทดสอบและขอบเขตการตรวจล่าสุดอยู่ใน [verification.json](../reports/live-research/verification.json) ข้อจำกัดที่ยังเหลือคือข้อมูลเสริมย้อนหลังยังไม่พอ, ตัวจริงตัวอย่างยังว่าง, mapping ยังเป็นการทบทวนภายใน, ลีกใหม่/ตลาดสูงต่ำยังไม่ผ่านการยืนยัน และยังไม่เปิดบริการให้ทำงานต่อเมื่อปิดเครื่อง
