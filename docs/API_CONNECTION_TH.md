# ผลทดสอบ API-Football จริง 26 ตุลาคม 2026

ใช้ API-Sports โดยตรงผ่าน `https://v3.football.api-sports.io` เก็บคีย์ไว้เฉพาะ `.dev.vars` ที่ถูก ignore ไม่ใส่ใน React, report, SQL หรือคำสั่งเรียกผ่าน URL ไม่มีการสมัครแพ็กเกจเสียเงินหรือ Deploy

## ผลจริง

- บัญชี Free active, 100 requests/day จาก `/status`
- ตรวจ catalog/coverage Premier League, La Liga, Bundesliga, Serie A และ Championship สำเร็จ
- `fixtures?league=39&season=2026` ถูกปฏิเสธ: บัญชีนี้ระบุว่า free season filter ใช้ 2022–2024
- ทดลองวันที่ย้อนหลังปี 2024 ถูกปฏิเสธเช่นกัน: บัญชีนี้ระบุช่วงวันที่ที่รับได้เป็น 2026-10-24 ถึง 2026-10-26
- `fixtures?date=2026-10-25&timezone=Asia/Bangkok` และวันที่ 26 โดยไม่ระบุ season **สำเร็จ** นี่คือรูปแบบ endpoint ตามเอกสารที่ทดสอบผ่านจริง ไม่สรุปว่าวิธี query อื่นหรือ endpoint อื่นจะมีสิทธิ์เหมือนกัน

รอบวันปัจจุบันขณะทดสอบยังเป็น **25 ตุลาคม 06:00 ถึง 26 ตุลาคม 06:00 กรุงเทพ** เพราะเวลาท้องถิ่นยังไม่ถึง 06:00 กรอง kickoff แบบ `[start,end)` หลังดึงสองวัน จึงไม่ปนเกมหลัง 06:00 ของรอบถัดไป

| ลีก | คู่ในรอบจาก response ที่บันทึก |
|---|---:|
| Premier League | 5 |
| La Liga | 4 |
| Bundesliga | 2 |
| Serie A | 5 |
| Championship | 0 |
| รวม | 16 |

เป็นโปรแกรม/สกอร์ ณ เวลาดึง ไม่ใช่ live stream และไม่ใช่คำทำนาย มี API fixture/team IDs แต่ historical identity mapping ยัง unverified จึงไม่เอาผลโมเดลของทีมอื่นมาใส่แทน และไม่แปลงสกอร์ null เป็น 0–0

## Requests และข้อจำกัด

รอบทดสอบทั้งหมด 10 HTTP requests: status 1, league coverage 5, fixture queries ที่ถูกปฏิเสธ 2, date queries ที่สำเร็จ 2 เอกสาร API-Sports ระบุ status ไม่หัก daily quota; header ล่าสุดรายงานเหลือ **93/100**, minute limit **10** และ minute remaining **8** ณ เวลานั้น ตัวนับ local กันงบแบบเผื่อรวมคำขอที่ล้มเหลวไว้ด้วย จึงเหลือ conservative 91 ไม่ถือว่าความล้มเหลวทุกแบบฟรี

Probe เว้นระยะอย่างน้อย 13 วินาที เคารพ minute headers, กัน daily reserve 10, ไม่ retry อัตโนมัติ และจำกัด rolling 24 ชั่วโมงของการทดสอบ local ไว้ 20 billable attempts สคริปต์ local ใช้ครั้งละหนึ่ง process; ยังไม่ใช้แทน atomic D1 quota manager สำหรับงาน cloud ที่รันพร้อมกัน เวลา reset ของบัญชียังไม่ยืนยัน จึงไม่เปิด Worker live/scheduler

coverage ทั้งห้าลีกมี flags ของ lineups, fixture/player statistics และ injuries แต่ยังไม่ได้เรียก endpoints เหล่านี้ ไม่รับรองว่าข้อมูลครบทุกแมตช์ และยังไม่ยืนยัน xG จริง รายการฤดูกาลใน catalog เป็นคนละเรื่องกับสิทธิ์ของบัญชีตาม query ที่ใช้

## ดูแคชในระบบและอัปเดตเอง

หน้าเว็บมีแท็บ **โปรแกรม API จริง** อ่านเฉพาะแคชจาก local D1 ผ่าน `/api/provider-preview` ไม่ส่ง API key ไป browser และไม่เรียก provider เมื่อเปิดหน้า แสดงเวลาที่ดึงและไม่มีการ refresh อัตโนมัติ คู่จำลองและสรุปทดลองเดิมอยู่แท็บแยก

```powershell
# วางแผนอย่างเดียว ไม่ใช้ requests
python -m scripts.api_football_schedule

# เรียกจริง: status 1 + date 2, budgeted billable ไม่เกิน 2
python -m scripts.api_football_schedule --execute

# ทำหลัง collect สำเร็จเท่านั้น ไม่ใช้ provider requests เพิ่ม
python -m scripts.prepare_provider_preview
npm run db:seed:provider:local

# เปิด local preview ด้วยสอง terminal
npm run dev:api
npm run dev
```

เมื่อ collect ล้มเหลวจะเก็บ last-good snapshot ไว้และเขียน `schedule-last-failure.json` แยก ห้ามใช้เวลาจากไฟล์ใหม่มาบอกว่าแคชเก่าสดขึ้น ถ้าจะเปลี่ยนคีย์ ให้แก้ `.dev.vars` ในเครื่อง ไม่ส่งคีย์ใหม่ในแชต

## งานถัดไป

1. ทำ canonical mapping ระหว่าง provider team IDs กับ historical team IDs โดยมีหลักฐานและฤดูกาล ไม่จับชื่อคล้ายกันแล้วถือว่ายืนยัน
2. อัปเดตผลก่อนเกมล่าสุดและฟีเจอร์จริงให้ตรงกับ prediction cutoff ก่อนนำ Precision v3 มาทำนาย fixtures จริง
3. ทดสอบ injuries/lineups/statistics แบบตัวอย่างและแจ้งงบ requests ก่อนเพิ่ม endpoint ให้ข้อมูลขาดเป็น unknown
4. เก็บคำทำนายก่อนเตะ/ผลจริงและวัด prospective แยกจาก retrospective 85.12% เดิม การต่อ API ครั้งนี้ยังไม่ได้เพิ่ม accuracy หรือฝึกโมเดลใหม่
5. ตรวจ reset, terms/retention และงบ cloud แล้วจึงเตรียม Cloudflare deployment หลังอนุมัติ ทุก scheduler และ MODEL_AUTO_PROMOTE ยัง false

หลักฐาน: `reports/api-football/preflight.json`, `historical-smoke-test.json`, `date-smoke-test.json`, `verification.json`; raw payload/content hashes และ request ledger อยู่ใน ignored `data/processed/api-football` โดยไม่เก็บ raw `/status` ที่มีชื่อ/อีเมล

แหล่งอ้างอิงทางการ: [ราคาและข้อจำกัด season ของแพ็กเกจฟรี](https://www.api-football.com/pricing), [รูปแบบการเรียก API และ coverage](https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide), [เอกสาร status/header](https://www.api-football.com/documentation_v3), [Rate limits](https://www.api-football.com/news/post/how-ratelimit-works) ผลบัญชีจริงข้างต้นมีขอบเขตเฉพาะเวลาและ query ที่ทดสอบ
