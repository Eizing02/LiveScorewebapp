# ขอบเขตการพุชโปรเจกต์ขึ้น GitHub

ปลายทางที่เจ้าของโปรเจกต์ระบุคือ `https://github.com/Eizing02/LiveScorewebapp` ตรวจพบว่า repository เป็น Public และยังไม่มี commit ก่อนนำเข้า โปรเจกต์ต้นทางคือ `D:\Football Prediction AI` ไม่ใช่ `D:\Live score Project`

## สิ่งที่อยู่ใน repository

- React/TypeScript frontend, Workers API และ shared football logic
- Python data/model pipelines, frozen policies และ unit/integration/browser tests
- D1 migrations และข้อมูลสาธิตที่ไม่ใช่ข้อมูล API ส่วนตัว
- Model artifacts พร้อม metadata/checksums/registry และรายงานย้อนหลังที่เกี่ยวข้อง
- ไฟล์ตั้งค่า workflow, package/requirements locks, เอกสารสถาปัตยกรรมและวิธีใช้งาน
- Branding assets พร้อม origin metadata และ source manifest เดิม

## สิ่งที่เก็บบนเครื่อง

- `.dev.vars`, `.env` และ secrets/key material
- `.wrangler/` และไฟล์ฐานข้อมูล local
- `data/source/`, `data/processed/` และ authenticated provider responses/normalized research records
- `reports/api-football/`, `reports/live-research/`, prospective collection reports และภาพหน้าจอที่แสดงข้อมูล API ส่วนตัว
- Provider/live/quota SQL exports, generated archives, dependencies, build output และ local agent-tool installations

การเพิ่มรายการใน `.gitignore` ไม่ลบไฟล์บนเครื่อง หลักฐานที่เอกสารเดิมอ้างถึงยังอยู่ในโปรเจกต์ local ส่วน archive โมเดลสร้างซ้ำได้จาก artifacts ที่บันทึกไว้ การพุชนี้ไม่เผยแพร่ GitHub Release หรืออนุมัติโมเดลเป็น active

## เริ่มจาก clone ใหม่

ใช้ขั้นตอนติดตั้งและสร้างข้อมูลย้อนหลัง/ข้อมูลสาธิตใน `README.md` โดยไม่ต้องมี API key สำหรับการทดสอบแบบ mock หลังติดตั้ง dependencies ให้รัน tests/build และใช้ migrations กับ D1 local ตามคำสั่งใน README

ฐานข้อมูล live และรายการ API ที่เครื่องเดิมมีอยู่ไม่ได้เดินทางมาพร้อม Git clone จึงอาจเห็นสถานะยังไม่มีข้อมูลจริงหรือยังไม่เปิดอ่าน private catalogue ซึ่งต่างจากฐานสาธิตที่สร้างได้จากแหล่งย้อนหลัง การสร้างข้อมูล API ใหม่ต้องตั้งค่า credentials ในไฟล์ local ที่ ignored และใช้ตัวตรวจสิทธิ์/โควตาที่เตรียมไว้

โครงสร้าง Cloudflare ยังคงปิด live/scheduler/auto-promotion เป็นค่าเริ่มต้น และ D1 ID เป็น placeholder การพุชไม่สร้าง resource, ไม่เขียน remote D1 และไม่ deploy เว็บไซต์ Workflow CI ตรวจซอฟต์แวร์ได้ ส่วน live collection, automation และ model publication ยังมีเงื่อนไขอนุมัติเดิม

ก่อน commit ตรวจรายชื่อ staged files, Git ignore rules, known secret values และรูปแบบ credentials โดยรายงานเฉพาะ path/จำนวน ไม่แสดงค่าคีย์
