# ผลพัฒนาโปรแกรมบอลหน้าเดียว

พัฒนาจริงใน `D:\Football Prediction AI` ตามแผน `docs/SINGLE_PAGE_RED_WHITE_BLUE_PLAN_TH.md` และคำอนุมัติ “ลงมือทำ/ทำต่อ” งานนี้เปลี่ยนส่วนแสดงโปรแกรมและเชื่อมข้อมูลที่มีอยู่เข้าหน้าใหม่ ไม่ได้ฝึกหรือปรับเกณฑ์โมเดลใหม่ ไม่แก้โปรเจกต์เดิม `D:\Live score Project`

## การใช้งานที่ทำเสร็จ

- หน้าหลักขาว–ฟ้า–แดง หน้าจอใหญ่แบ่งรายการแข่งขัน / โปรแกรม / วิเคราะห์ในหน้าต่างเดียว แท็บเล็ตสองส่วน มือถือใช้หนึ่งส่วนพร้อมปุ่มกลับที่คืนตำแหน่งและ focus
- เลือกวันนี้ พรุ่งนี้ หรือวันที่เอง รอบวันไทยเป็น `[06:00, 06:00 ของวันถัดไป)`; ตัวกรองคืนนี้เป็น 18:00–ก่อน 06:00
- ค้นหาทีม กรองประเทศ รายการแข่งขัน สถานะ ช่วงเวลา ติดตามลีก และเลือกเฉพาะคู่ที่มีคำทำนาย แบ่งหน้าฝั่งเซิร์ฟเวอร์ 25 คู่
- กลุ่มลีกมีชื่อ ประเทศ จำนวนคู่จริงในกลุ่ม ปุ่มพับ/แสดง และดาวติดตาม; หากหนึ่งลีกกินหลายหน้า จะแสดงจำนวนที่อยู่ในหน้านั้นเทียบกับทั้งหมด สถานะตัวกรองและคู่ที่เลือกเก็บใน URL ส่วนลีกที่ติดตามเก็บในเครื่อง
- วิเคราะห์แยกสี่แท็บ: สรุป, ฟอร์ม–H2H, ประตู, ข้อมูลทีม ประวัติและคำทำนายใช้ข้อมูลที่ยืนยันได้อยู่เดิม ไม่สร้าง H2H หรือคำทำนายให้รายการที่ยังไม่มีข้อมูล
- คู่เด่นแสดงเฉพาะคำทำนายที่ผ่านนโยบายเดิม ชุดทดลอง 3/5 คู่ยังพิจารณาทั้งรอบและมีป้ายอธิบาย ไม่เติมคู่เพื่อให้ครบชุด; ผลการทำนายกรองตามรอบที่เลือก โดยสถิติสะสมระบุว่าเป็นสะสม
- โลโก้เดิม 47 ภาพคงข้อมูลภาพเดิม เพิ่ม metadata ระบุต้นทางไว้ใน PNG และเก็บ checksum ก่อน/หลังใน manifest โดยตรวจว่าข้อมูลภาพไม่เปลี่ยน ID เพิ่มเติมใช้เส้นทางภาพ `/api/media` ไปยัง CDN ที่กำหนดตายตัว ตรวจชนิด/ขนาด PNG มี timeout และ cache 24 ชั่วโมง โหลดเมื่อเข้าใกล้ส่วนที่เห็น และแสดงตัวอักษรสำรองเมื่อภาพไม่พร้อม
- ข้อมูลเก่า ข้อมูลบางวันยังไม่ดึง สิทธิ์ไม่พอ หรือคำทำนายไม่พร้อม มีสถานะชัดเจน การกด “อ่านแคช” ไม่ส่งคำขอข้อมูล API-Football

## ข้อมูลที่แสดงจริง

เพิ่ม display catalogue จาก raw cache เดิมที่ตรวจ SHA256 แล้ว ไม่ใช้ตัวกรอง 5 ลีกของ training pipeline มาปิดกั้นโปรแกรมบอล:

| ขอบเขต | ผลตรวจ |
|---|---:|
| ทุก snapshot ที่มีอยู่ รวมหลายวัน | 2,191 fixture ID ไม่ซ้ำ |
| หลักฐานการสังเกตแบบไม่เขียนทับ | 3,727 รายการ |
| หลักฐานแหล่งข้อมูล | 6 รายการ |
| รายการแข่งขันรวมหลายวัน | 447 รายการ |
| กักจากการตรวจ schema ของ catalogue รอบนี้ | 0 |
| Training labels ที่เพิ่มจากงานนี้ | 0 |

รอบ **27 ต.ค. 2026** มี **332 คู่ / 112 รายการแข่งขัน** จาก source วันที่ 27 และ 28 ที่บันทึก 27 ต.ค. ประมาณ 15:09 เวลาไทย ตัวกรอง 5 ลีกเดิมเคยแสดงเพียง 3 คู่ ทำให้ 329 คู่ไม่ปรากฏ ตัวอย่างรายการเพิ่มเติมคือ Copa del Rey 18, Türkiye Kupası 12, KNVB Beker 9, AFC Champions League Elite 8, DFB Pokal 8, Serie B 7 และ League One 5 คู่

รอบ **28 ต.ค. 2026** มี **266 คู่ / 75 รายการแข่งขัน** ในแคชขณะตรวจ แต่ยังไม่ได้ดึง source วันที่ 29 จึงแสดง coverage ว่าบางส่วน การมี source ครบสองวันที่ใช้กรองไม่ได้ยืนยันว่าผู้ให้บริการมีทุกคู่ทั่วโลก และไม่ได้ยืนยันสถานะสด

Catalogue แยกสถานะที่บันทึกไว้ คะแนนที่หายยังเป็น null ไม่แทนด้วย 0–0 เก็บทุก observation ไว้และเลือกข้อมูลล่าสุดก่อนกรองวัน จึงไม่แสดงตำแหน่งเก่าของคู่ที่ถูกเปลี่ยนเวลาเป็นอีกคู่หนึ่ง การรับข้อมูลเข้ามี HMAC, checksum, ID/date/status validation และเส้นทางนำเข้าอนุญาตเฉพาะตารางโปรแกรม

ฐานที่ผ่านเกณฑ์เพื่อฝึกเดิมยัง **17,043 นัด** (17,027 เดิม + 16 ผล API ที่รับไว้ก่อนงานนี้) ไม่เพิ่มขึ้นตามจำนวนคู่ในหน้าจอ ข้อมูลผิดลำดับ EPL 2019/20 จำนวน 66 นัดยังถูกกักตามเดิม

## ไฟล์หลัก

| กลุ่ม | ไฟล์ที่สร้าง/แก้และหน้าที่ |
|---|---|
| Catalogue | สร้าง `ml/program_catalog.py`, `scripts/import_program.py`; แก้ `ml/provider_broker.py`, `scripts/live_sync.py` เพื่อส่ง catalogue ผ่าน broker เดิม |
| ฐานข้อมูล | สร้าง `db/migrations/0011_program_catalog.sql` เก็บ observations, current heads, sources และ immutable triggers; ใช้กับ local D1 แล้ว |
| API | สร้าง `packages/football/program.ts`, `apps/api/program.ts`, `apps/api/media.ts`; แก้ `apps/api/index.ts`, `apps/api/live.ts` สำหรับ routes และกรองผลตามรอบ |
| หน้าจอ | แก้ `apps/web/src/App.tsx`, `ProviderPreview.tsx`, `LiveDetail.tsx`, `PredictionResults.tsx`, `BrandLogo.tsx`, `style.css`; สร้าง `DailyPicks.tsx`, `presentation.ts`, `media-index.json` |
| เตรียมภาพ | แก้ `scripts/prepare_media.py` ให้สร้าง index ของไฟล์ที่มีอยู่; เพิ่ม origin metadata ใน PNG เดิม 47 ภาพและแก้ `apps/web/public/media/sources.json` ให้เก็บ checksum ปัจจุบันพร้อม checksum ต้นฉบับ |
| ทดสอบ | สร้าง `ml/tests/test_program_catalog.py`, `tests/program.test.ts`, `tests/media.test.ts`, `tests/ui/one-page.spec.ts`; ปรับ `tests/live.test.ts`, `tests/ui/usability.spec.ts` และ UI specs ที่เกี่ยวกับการเปิดโปรแกรม/วิเคราะห์/คำทำนาย |
| เอกสารและหลักฐาน | `README.md`, `PRODUCT.md`, `DESIGN.md`, `.impeccable/design.json`, surface/direction/quality-bar, แผนหน้าเดียว และ `reports/one-page/` |

รายชื่อพร้อม SHA256 ของไฟล์ส่งมอบอยู่ใน `reports/one-page/file-manifest.json` ข้อมูล raw cache, local D1, secrets และ generated import batches เป็นไฟล์ local ที่ไม่ควร commit

## ผลตรวจที่รันจริง

| การตรวจ | ผล |
|---|---|
| Python suite | 78 ผ่าน; รันก่อนการแก้ UI ชุดสุดท้ายซึ่งแตะเฉพาะ CSS/TypeScript |
| TypeScript/API suite รอบสุดท้าย | 56 ผ่าน |
| Browser suite รอบสุดท้าย | 16 ผ่าน |
| รวม | 150 ผ่าน |
| Ruff / ESLint | ผ่าน |
| TypeScript + Vite build | ผ่าน |
| Worker bundle | dry-run ผ่าน ไม่ deploy |
| Local D1 migrations | ไม่เหลือ migration ค้าง |
| Local API integration | catalogue, pagination, legacy read และ health ตอบสำเร็จ |
| Frozen candidate integrity | training code/config/artifacts checksum ตรงครบ 23 รายการ |
| Known secret value scan | ไม่พบใน source, docs และ bundle ที่ตรวจ; รายละเอียดขอบเขตใน verification.json |
| PNG provenance | ฝัง origin ครบ 47 ภาพ; scan ไม่เหลือ missing และข้อมูลภาพเหมือนเดิม |

ทดสอบ schema/null scores, รอบ 06:00, duplicate/correction/immutability, checksum/auth, การค้นหาและกรองจากเซิร์ฟเวอร์, ไม่สร้างคำทำนายให้คู่ไม่มีข้อมูล, แสดง error/retry, กลับหน้ารายการ, URL/reload, keyboard tabs, ภาพโหลดล้มเหลว และความต่างระหว่าง accuracy ที่ยังไม่มีผลกับ 0%

ภาพจริงตรวจที่ 1440×900, 1366×768, 1024×900, 768×900, 390×844 และ 320×900 ขนาดปกติไม่มี document overflow แต่ละส่วนยาวเลื่อนใน pane ได้ ที่ตัวอักษร 200% อนุญาตให้เลื่อนเอกสารเพิ่มเพื่ออ่านได้ ทดสอบเข้าถึงคู่สุดท้ายและแท็บวิเคราะห์ มีภาพและค่าที่วัดใน `layout-verification.json` และ `zoom-reading.json`

Impeccable finish review พบสี่ข้อ และ verdict ตรวจแก้ซ้ำให้ **resolved ครบ 4 ข้อ / disposition: ship** ขอบเขตคือรายการแก้ทั้งสี่ ไม่ใช่การรับรองทุกส่วนของระบบ มี detector แบบ manual หนึ่งครั้งก่อนการแก้ (`[]`); ไม่มีหลักฐานว่า host รัน hook อัตโนมัติ

Build สุดท้าย: main JavaScript 269.37 KB / gzip 81.52 KB, research chunk 68.13 KB / gzip 14.84 KB และ CSS 37.26 KB / gzip 7.45 KB

## ข้อจำกัดและงานต่อไป

1. โปรแกรมแสดงได้หลายร้อยรายการ แต่โมเดลยังรองรับเฉพาะรายการ/ทีมที่มี identity, history และการตรวจสอบตามเกณฑ์เดิม บางคู่จึงไม่มี prediction, injuries, lineups หรือ xG ให้แสดง
2. Candidate ยังเป็น `precision-v3-9f46ca6392a2`, active model เป็น null และ `MODEL_AUTO_PROMOTE=false` ไม่มีผลทดสอบ accuracy ใหม่จากการเปลี่ยนหน้าจอ และไม่มีการรับประกัน 70–80% ล่วงหน้า
3. การอ่านแคชไม่ทำให้ข้อมูลสดขึ้น ต้องใช้ sync ที่มีการตรวจโควตา/สิทธิ์เดิมเมื่อต้องการ snapshot ใหม่ รอบนี้เรียก API-Football v3 เพิ่ม **0 requests**; มีเฉพาะการทดสอบ CDN รูปโดยไม่ส่ง key
4. ยังไม่เปิด production, remote D1, scheduler หรือ paid service ก่อนใช้งานสาธารณะต้องตรวจ provider coverage/โควตา ตั้งค่า Cloudflare secrets และ resource จริง แล้วทดสอบระบบ sync/locking/evaluation ในสภาพแวดล้อมที่อนุมัติ
5. ก่อนขยายโมเดลไปบอลถ้วย/ลีกอื่น ต้องจัด identity และข้อมูลย้อนหลังที่เชื่อถือได้ ทดสอบตามเวลาและ freeze policy ใหม่ก่อนประเมิน ห้ามเปิดสิทธิ์ทำนายเพียงเพราะแสดงโปรแกรมได้

## เปิดใช้บนเครื่องนี้

เปิด terminal สองช่องใน `D:\Football Prediction AI`: ช่องแรก `npm run dev:api` ช่องสอง `npm run dev` แล้วเปิด `http://127.0.0.1:5173` หากต้องการดูรอบที่ใช้ตรวจ ให้เลือกวันที่ 27 ต.ค. 2026 หรือใช้ `/?live_date=2026-10-27` ส่วน “วันนี้” จะเปลี่ยนตามรอบเวลาไทยจริง

นำ catalogue จากแคชเดิมเข้า local ซ้ำได้ด้วย `.\.venv\Scripts\python.exe -m scripts.import_program --import-local` หลังเปิด local API และ apply migrations แล้ว คำสั่งนี้ไม่เรียก API-Football และไม่เพิ่ม training labels
