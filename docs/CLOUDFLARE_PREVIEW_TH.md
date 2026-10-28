# เว็บทดลองส่วนตัวบน Cloudflare

ชุดนี้เตรียมการเปิดเว็บทดลองด้วย Worker และ D1 ชื่อ `football-ai-preview` แยกจากทรัพยากรเดิม ยังไม่มีคำสั่ง Deploy หรือเขียน remote D1 ถูกดำเนินการ

## สิ่งที่เตรียมแล้ว

- `wrangler.preview.example.jsonc`: แม่แบบ Worker/D1 แยกชื่อ ใช้ Worker ตรวจทุก request รวม static assets ก่อนให้เปิดข้อมูล
- `apps/api/preview-access.ts`: HTTP Basic authentication ผ่าน HTTPS ใช้รหัสผ่านสุ่มอย่างน้อย 32 ตัวอักษร เก็บเป็น Worker secrets ไม่มีรหัสผ่านค่าเริ่มต้น และใช้ WebCrypto ตรวจ credentials
- Preview ปิด internal writes, cron, live provider execution และ auto-promotion หากค่าป้องกันหรือ credentials ไม่พร้อมจะไม่ให้เปิดข้อมูล
- `scripts/cloud_preview.py`: อ่านบัญชี/รายชื่อ resource เท่านั้น แล้วเตรียม config, credentials และ SQL ในเครื่อง ไม่มีโค้ดสร้าง resource, อัปเกรดแพ็กเกจ หรือ Deploy
- SQL เป็น snapshot จากตารางที่อนุญาต ตรวจด้วย migration จริงในฐานชั่วคราว นำเข้าซ้ำได้ และตรวจข้อจำกัด 100 KB ต่อ statement ของ D1 ไม่รวม nonce, quota, jobs หรือ active model registry

นี่เป็นเว็บอ่านข้อมูลที่บันทึกไว้ ไม่ใช่การเปิด live sync หรือรับรองผล AI ก่อนเริ่มใช้คลาวด์ต้องตรวจแพ็กเกจและ usage ของบัญชีจริง Free tier มีโควตาจำกัด ไม่ใช่ใช้ได้ไม่จำกัด

## ตรวจในเครื่อง

```powershell
npm run build
npm run worker:preview:check
.\.venv\Scripts\python.exe -m scripts.cloud_preview
.\.venv\Scripts\python.exe -m scripts.cloud_preview --prepare
```

`--prepare` เขียนเฉพาะ `wrangler.preview.local.jsonc` และ `.cloudflare/` ซึ่งถูก Git ignore เก็บ password ที่ `.cloudflare/preview.secrets.json` ไม่ใส่ใน config, source, GitHub หรือข้อความแชต OAuth อยู่ในที่เก็บ credentials ของ Wrangler

หากอ่านแพ็กเกจผ่าน OAuth ไม่ได้ (เช่น billing API ตอบ 403) รายงานเป็น `unverified` ต้องให้เจ้าของบัญชียืนยัน Free ก่อนเปิดบริการตามเงื่อนไขค่าใช้จ่ายเดิม การมีสิทธิ์ Workers write ไม่ได้แปลว่าได้ตรวจแพ็กเกจแล้ว

## ขั้นตอนหลังได้รับอนุมัติ

1. ยืนยัน Workers Free และอนุมัติสร้าง D1/import snapshot/Deploy เว็บทดลองส่วนตัว โดยไม่แตะ Worker เดิม
2. สร้าง D1 `football-ai-preview` แล้วใส่ UUID จริงใน config local; ใช้ migrations เฉพาะฐานใหม่นี้
3. นำเข้า SQL local ที่ตรวจ checksum แล้ว ตรวจจำนวน fixture heads และ foreign keys บนฐานใหม่
4. Deploy code ซึ่งปิดการเข้าถึงเมื่อยังไม่มี credentials จากนั้นใส่เฉพาะ `PREVIEW_USERNAME` และ `PREVIEW_PASSWORD` เป็น Worker secrets ไม่ต้องส่ง API-Football key สำหรับเว็บอ่าน snapshot
5. ตรวจจาก URL จริงว่าไม่มี credentials ได้ 401; มี credentials เปิดเว็บ/API ได้; internal routes ได้ 403; ค่า live/scheduler/auto-promotion ยังคงปิด
6. ทดสอบมือถือและบันทึก usage/CPU/D1 metrics จริงก่อนอนุมัติงานอัตโนมัติรอบถัดไป

ชื่อและ URL ที่เสนออยู่ใน `.cloudflare/preview-plan.json` ข้อมูลใน snapshot ยังมีเวลาบันทึกเดิม การย้ายขึ้นโฮสต์ไม่ได้ทำให้ข้อมูลสดหรือสร้างคำทำนายที่ยังไม่มีขึ้นมา

## CI และหลักฐานวิจัย

CI รอบแรกบน Linux หยุดที่ `v2_protocol_or_dataset_changed_use_new_version` เพราะ importer ที่ freeze ไว้สร้าง source-record ID จาก Windows path separators การแก้ CI ใช้ Windows สำหรับชุดวิจัย/Python เดิม และใช้ Linux ตรวจ frontend/API/Worker/Browser โดยอ่าน demo snapshots ที่บันทึกไว้ ไม่รันชุด API ที่ต้องสร้างฐานข้อมูลขนาดใหญ่ซ้ำบน Windows ซึ่งเคยติด hook timeout การเปลี่ยนนี้ไม่แก้ frozen training code, protocol, metrics หรือ model artifacts การทำ source IDs ให้ข้ามระบบได้ในอนาคตต้องเป็น dataset/model version ใหม่

HTTP Basic authentication ใช้สำหรับเว็บทดลองส่วนตัวผ่าน HTTPS ไม่ใช่ระบบสมาชิกหลายผู้ใช้ ระยะเปิดบริการต่อบุคคลอื่นต้องเลือกและทดสอบระบบสิทธิ์ที่เหมาะกับขอบเขตใหม่

อ้างอิงทางการ: [Workers assets routing](https://developers.cloudflare.com/workers/static-assets/), [Basic authentication](https://developers.cloudflare.com/workers/examples/basic-auth/), [D1 limits](https://developers.cloudflare.com/d1/platform/limits/), [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/), [Worker secrets](https://developers.cloudflare.com/workers/configuration/secrets/)
