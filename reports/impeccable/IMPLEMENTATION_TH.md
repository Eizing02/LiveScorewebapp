# ผลติดตั้งและประยุกต์ Impeccable

วันที่ 27 ตุลาคม 2026 · โครงการ `D:\Football Prediction AI`

## งานที่ทำจริง

ติดตั้ง Impeccable 4.8.0 ในขอบเขตโครงการสำหรับ Codex อ่าน playbooks และนำมาใช้ปรับเส้นทางใช้งานทั้งหน้าประจำวันและหน้างานวิจัย ไม่แก้โครงการ `D:\Live score Project` ไม่ deploy และไม่เปิดบริการเสียเงิน

หน้าแรกเป็นโปรแกรมจากแคช API จริง เมนูหลักเป็น โปรแกรม / คู่เด่น / ผลการทำนาย ปุ่มงานวิจัยแยกไปอยู่ส่วนหัว โปรแกรมจำลองและผลวิจัยเก่ายังเข้าถึงได้โดยชัดเจนว่าเป็นงานทดลอง

รายการแบ่งลีก แสดงโลโก้ทีม/ลีกจริง เวลาไทย สกอร์ที่มี และสถานะ ณ เวลาบันทึก มีวันนี้/พรุ่งนี้ วันที่ ช่วงกลางคืน ลีก ค้นหาทีม และสถานะ ตัวกรองมือถือพับได้ ชื่อทีมไม่ลดลงเหลืออักษรจิ๋วและไม่ต้องเลื่อนตารางแนวนอนเพื่อหาปุ่มวิเคราะห์

รายคู่เป็นหน้าอ่านตามปกติ กด Back และเปิดลิงก์ตรงได้ เก็บตัวกรองใน URL และคืน focus หลังย้อนกลับ เปรียบเทียบฟอร์ม H2H 5/10/20 นัด สูง–ต่ำ สกอร์ที่เป็นไปได้ และข้อมูลเสริมที่มีจริง คำทำนาย provider แยกจากโมเดลเรา

เพิ่ม API อ่านผลทำนาย `/api/live/results` แบบจำกัด 50 รายการต่อหน้า แสดงคำทำนายแรกของแต่ละ fixture occurrence และผลตรวจ revision ล่าสุด ไม่รวมรายงานทั้งวันปะปนกับผลตรวจคำทำนายรายนัด ไม่คำนวณ accuracy ขึ้นใหม่บนหน้าเว็บ

เพิ่มโลโก้ local จากรหัส provider 47 ไฟล์ พร้อม manifest แหล่งที่มา/ขนาด/checksum และฟอนต์ IBM Plex Sans Thai พร้อม OFL ไม่มี API key ใน URL ภาพ การเตรียมภาพไม่ใช้โควตา API บัญชี

## หลักฐานก่อนแก้

- Assessment A: 18/40 บนหน้าที่ตรวจ พบโปรแกรมอยู่ลึก การอ่านตารางมือถือ และ Back ที่ไม่ตรงความคาดหวัง
- Assessment B: 10/20 บนมิติเทคนิคที่ตรวจ พบเส้นทางโหลดไม่สอดคล้อง ปุ่ม/ตัวอักษรเล็ก และไม่มีการโหลดฟอนต์จริง
- ตัวตรวจ static ก่อนแก้: 1 warning (`side-tab`) ซึ่งอยู่หน้างานวิจัย ไม่ใช่สาเหตุหลักที่ทำให้ดูโปรแกรมยาก
- ตัวเลขข้างต้นเป็น baseline ไม่ใช่คะแนนประเมินใหม่หลังแก้ และไม่ใช่การรับรองทั้งโครงการ

รายละเอียดอยู่ใน assessment-a.md และ assessment-b.md ส่วนผลหลังแก้อ้างอิงการทดสอบและภาพหน้าจอ ไม่ตั้งคะแนนเพิ่มเอง

## ข้อมูลจริงที่ตรวจระหว่างทำงาน

เรียก collector ที่อนุญาตไว้ผ่าน quota broker: status หนึ่งครั้งและ date สองวัน หลังจากตรวจว่า local broker กลับมาให้บริการได้ การลองครั้งแรกหยุดที่ local export จึงไม่ถึงขั้นเรียก provider

ผล refresh สำเร็จ: รวม fixture ล่าสุด 22 นัด ในห้าลีกเป้าหมาย มี 3 นัดล่วงหน้าของรอบ 27 ต.ค. ทีมที่ผ่านการจับคู่เดิม 18 นัด และข้อมูล 4 นัดถูกกักจาก identity ที่ยังไม่ทบทวน สามารถแสดงชื่อและโปรแกรมตาม provider ได้ แต่ไม่สร้างคำทำนายหรือเพิ่ม label เข้า training โดยแต่งการจับคู่ทีม

ไม่มีคำทำนายล่วงหน้าใหม่ในรอบนี้ และไม่มีความแม่นยำล่วงหน้าให้รายงาน โมเดลเดิมยังเป็น research candidate และ auto promotion ยังปิด

## ไฟล์หลัก

- `.agents/skills/impeccable/`, `.codex/hooks.json`, `.impeccable/config*.json`, `.gitignore`: การติดตั้งและตั้งค่า
- `PRODUCT.md`, `DESIGN.md`, `.impeccable/surfaces/football-app.md`: บริบทและระบบภาพ
- `apps/web/src/App.tsx`, `ProviderPreview.tsx`, `LiveDetail.tsx`, `PredictionResults.tsx`, `ResearchHub.tsx`: เส้นทางหน้าจอ
- `apps/web/src/BrandLogo.tsx`, `navigation.ts`, `style.css`, `centre.css`: ชิ้นส่วนร่วม ไอคอน tokens และ responsive
- `apps/web/src/FilteringPanel.tsx`, `MatchCentre.tsx`, `MatchDetail.tsx`, `PrecisionPanel.tsx`, `ResearchEvidence.tsx`: ปรับให้ใช้ระบบภาพร่วมและตัดป้ายตกแต่งซ้ำ
- `apps/api/live.ts`, `packages/football/types.ts`: ส่ง branding IDs และสกอร์ nullable พร้อมผลทำนายแบบแบ่งหน้า
- `scripts/prepare_media.py`, `apps/web/public/media/`, `apps/web/public/fonts/`: ภาพและฟอนต์ local
- `tests/live.test.ts`, `tests/ui/*.spec.ts`: contract และเส้นทางใช้งาน
- `docs/IMPECCABLE_GUIDE_TH.md`: วิธีใช้ครบ 24 workflows และเงื่อนไขการเรียก

ไม่มี migration ใหม่ ไม่มีการแก้ training code/weights ของ candidate เดิม ตรวจ checksum เทียบ metadata แยกจากการรัน unit tests

## การตรวจสอบและข้อจำกัด

ผลเครื่องมือฉบับสุดท้ายเก็บใน `verification.json` พร้อม detector-after.json, layout-after.json และภาพ current/detail ตามขนาดหน้าจอ

การตรวจเป็น Chromium ในเครื่อง มีการทดสอบ reduced motion, focus และการเพิ่มขนาดตัวอักษร 200% ไม่อ้างว่าได้ทดสอบมือถือจริงทุกเครื่อง ทุก browser หรือได้รับการรับรอง WCAG เต็มรูปแบบ

การทดสอบบางรอบที่รันงานตรวจหลายชุดพร้อมกันพบ local runtime หยุด/รอนาน จึงหยุดรอบเหล่านั้นและตรวจซ้ำแยกชุด รัน UI แบบหนึ่ง worker และ unit tests แยกกันผ่านทั้งหมด โดยตั้งค่า browser specs ให้ใช้หนึ่ง worker เพราะแชร์ Worker/D1 ในเครื่อง รอบที่ล้มหรือหยุดไม่ได้ถูกนับเป็นผลผ่าน

ระหว่าง UI รอบที่ผ่านยังมีข้อความ `Network connection lost` จาก local Wrangler บางครั้ง แต่ไม่พบ uncaught page error ในเส้นทางที่ตรวจและ assertion ทั้ง 13 ชุดผ่าน ยังไม่ได้ยืนยันสาเหตุของข้อความฝั่ง dev runtime นี้ หรือทดสอบประสิทธิภาพบน Cloudflare production

ขอบเขตที่ยังต้องทำต่อ: ทบทวน provider identity ของทีมใหม่ เก็บคำทำนายก่อนแข่งจริงและผลประเมินเพิ่ม แล้วจึงพิจารณาโมเดล/ข้อมูลเสริมตามเกณฑ์เดิม ส่วน Cloudflare production และตารางงานอัตโนมัติยังรอการอนุมัติแยกต่างหาก

Hooks ตั้งค่าแล้ว แต่ยังไม่อ้างว่า Codex host ยอมรับ definition ใหม่โดยอัตโนมัติ หลังรีสตาร์ตให้ตรวจ Settings → Hooks รอบนี้ใช้ตัวตรวจด้วยตนเอง
