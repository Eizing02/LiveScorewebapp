# เว็บโปรแกรมบอลและการซิงก์

หน้าเว็บเปิดอ่านได้โดยไม่ต้องใส่รหัสผ่าน ข้อมูลอยู่ใน Cloudflare D1 เดิมของโปรเจกต์ใหม่ และใช้ Worker `football-ai-preview` ตัวเดิม ไม่แก้ทรัพยากรของโปรเจกต์เก่า

GitHub Actions workflow `Programme data sync` เก็บโปรแกรมสามวันตามปฏิทิน เพื่อให้รอบวันนี้และพรุ่งนี้ครบ 06:00–06:00 เวลาไทย เป้าหมายรอบละสองชั่วโมง รวมสูงสุด 36 fixture requests ต่อวัน ไม่รวมการตรวจสถานะบัญชี ไม่มี retry อัตโนมัติ และไม่รับประกันนาทีที่ scheduler จะเริ่มจริง หน้าเว็บแสดงเวลาบันทึกและเวลาซิงก์สำเร็จจริง พร้อมแจ้งเมื่อข้อมูลไม่ครบหรือรอบล่าสุดล้มเหลว

ตัว collector ใช้ Python standard library ไม่ฝึกโมเดลและไม่ใช้ frozen research pipeline ดึง `/status` ก่อนสาม date queries ตรวจว่าเป็นบัญชี Free ที่ active และเหลือโควตาพอ ใช้ D1 quota broker เดียวกันสำหรับทุกคำขอ จำกัด normal calls 65/day และเก็บสำรองอย่างน้อย 15 requests ตาม policy เดิม ข้อผิดพลาดจะเก็บ snapshot ล่าสุดไว้ ไม่มีการแทนด้วย fixtures จำลองหรือแปลง missing score เป็น 0–0

ตั้งค่า Worker `APP_ENV=public`, `PROGRAM_SYNC_ENABLED=true`, `PREVIEW_AUTH_ENABLED=false` ส่วน `PREVIEW_READ_ONLY=true`, `LIVE_API_ENABLED=false`, `SCHEDULER_ENABLED=false` และ `MODEL_AUTO_PROMOTE=false` คงไว้ เพราะการเก็บโปรแกรมทำผ่าน collector ไม่ใช่ legacy sync หรือ Worker cron ตัวเก่า ต้องเปิด `PROVIDER_BROKER_ENABLED` และยืนยัน `PROVIDER_WINDOW_VERIFIED` หลังตรวจบัญชีจริง

Public mode อนุญาตเฉพาะ signed service routes สำหรับ programme import, sync status และ quota reserve/settle เส้นทางเปลี่ยนโมเดลและ legacy writes ถูกปิดทั้งหมด เก็บ `INTERNAL_SYNC_SECRET` เป็น Worker secret; API key อยู่ใน GitHub Actions secret และไฟล์ local ที่ถูก ignore ไม่มี key บน frontend หรือใน URL

GitHub secrets ที่ใช้: `API_FOOTBALL_KEY`, `PROGRAM_SYNC_SECRET`, `PROGRAM_WORKER_URL` และ repository variable `PROGRAM_SYNC_ENABLED=true` ต้องมี workflow บน default branch จึงทำงานตามเวลา แยก concurrency group เพื่อไม่ให้ sync ซ้อนกัน เปลี่ยน variable เป็น false เพื่อหยุด schedule โดยไม่ลบข้อมูล

ตรวจในเครื่องแบบไม่ยิง API: `python -m scripts.program_sync` การใช้ `--execute --approved-remote` เป็นการเรียก API และ signed import จริง จึงใช้เฉพาะเมื่อตรวจ config และได้รับอนุมัติแล้ว

หลักฐานอ้างอิง: [API-Football direct account quota/reset](https://www.api-football.com/terms), [API quota guidance](https://www.api-football.com/news/post/how-to-optimize-api-sports-calls-and-quota-usage), [GitHub scheduled workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
