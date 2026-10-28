# เว็บทดลองส่วนตัวบน Cloudflare

เปิดเว็บทดลองส่วนตัวแล้วเมื่อ 28 ตุลาคม 2026 ด้วย Worker และ D1 ใหม่ชื่อ `football-ai-preview` แยกจากทรัพยากรเดิม หลังเจ้าของบัญชียืนยัน Workers Free และอนุมัติสร้างฐาน นำเข้า snapshot และ Deploy แล้ว หลักฐานก่อน Deploy อยู่ใน `reports/cloudflare-preview/verification.json`; ผลบนคลาวด์จริงอยู่ใน `reports/cloudflare-preview/deployment.json`

## เข้าใช้งาน

เปิด [Football AI Preview](https://football-ai-preview.piyawatpiwsiri.workers.dev) ผ่าน HTTPS เบราว์เซอร์จะขอ username และ password อ่านข้อมูลเข้าสู่ระบบจาก `.cloudflare/preview.secrets.json` ในเครื่องเจ้าของโปรเจกต์ ไฟล์นี้ถูก Git ignore และไม่ใส่รหัสผ่านในเอกสารหรือ GitHub

เว็บนี้อ่าน snapshot ที่นำขึ้นไว้ การกดอ่านแคชหรือเปลี่ยนวันไม่ได้ดึง API-Football ใหม่ วันที่ซึ่งยังไม่ได้บันทึกจะแสดงข้อมูลไม่ครบหรือไม่มีรายการตามจริง รอบวันใช้เวลาไทย 06:00 ถึง 06:00 วันถัดไป

## ผลตรวจหลัง Deploy

- ใช้ application source commit `66100320783371c0a4434d98e7fbc1b9b883254b`; GitHub CI บน Linux/Windows ผ่านก่อน Deploy
- ฐานใหม่ผ่าน 11 migrations; มี fixture heads 2,191 คู่, observations 3,727 แถว, รายละเอียดคู่จริง 130 คู่ และ foreign key violations 0 เพิ่ม research report chunks 157 ส่วน พร้อมตรวจรายงานที่อ้างอิงทั้ง 3 ชุดว่าครบ ลำดับถูก และ checksum ตรงกัน
- รอบ 25 ต.ค. มี 1,203 คู่/327 รายการ; 27 ต.ค. มี 332 คู่/112 รายการ; 28 ต.ค. มี 266 คู่/75 รายการ โดยรอบ 28 ต.ค. ยังขาด source date 29 ต.ค.
- ตรวจ HTTP/API จริงผ่าน 40 ข้อ และ browser flow จริงผ่าน 24 ข้อ รวมหน้าโปรแกรม รายคู่ ผลวิจัย และหน้าจอ 1440, 390 และ 320 พิกเซล ไม่พบ page errors หรือ authenticated API errors
- ผู้ไม่เข้าสู่ระบบเปิด HTML, JavaScript และ API ไม่ได้ (401); credentials ผิดได้ 401; internal write routes ถูกปิด (403); response เป็น private/no-store
- ยืนยัน live API, scheduler, quota broker และ auto-promotion ปิดจริงบน Worker; ไม่มี cron; secrets บน Worker มีเฉพาะ credentials สำหรับ preview สองรายการ
- ตรวจไฟล์โมเดลและ training source ทั้ง 23 checksum entries ว่าคงเดิม; active model และคำทำนายล่วงหน้าบนคลาวด์ยังเป็น 0 ไม่สร้างผลทำนายแทนข้อมูลที่ขาด
- หลังแก้การส่งออก report chunks ชุดทดสอบในเครื่องผ่าน 87 Python + 65 TypeScript/API + 17 browser = 169 tests พร้อม lint/typecheck/build ผ่าน ใช้พอร์ตทดสอบ UI เฉพาะ 5193 และตรวจ API health ก่อนใช้ server เพื่อลดการเผลอทดสอบอีกโปรแกรมที่เปิดพอร์ต 5173 อยู่

ยังไม่ได้ยืนยัน CPU/usage จาก account analytics สำหรับการใช้งานสะสม ต้องเก็บหลักฐานส่วนนี้ก่อนพิจารณาเปิดงานอัตโนมัติ ผล smoke test ยืนยันการทำงานของ URL ในเวลาที่ตรวจเท่านั้น ภาพหน้าจอและรายละเอียดภายในเก็บใน `.cloudflare/smoke/` ซึ่งไม่ถูก commit

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

## ลำดับการ Deploy ที่ดำเนินการแล้ว

1. ยืนยัน Workers Free และอนุมัติสร้าง D1/import snapshot/Deploy เว็บทดลองส่วนตัว โดยไม่แตะ Worker เดิม
2. สร้าง D1 `football-ai-preview` แล้วใส่ UUID จริงใน config local; ใช้ migrations เฉพาะฐานใหม่นี้
3. นำเข้า SQL local ที่ตรวจ checksum แล้ว ตรวจจำนวน fixture heads และ foreign keys บนฐานใหม่
4. Deploy code ซึ่งปิดการเข้าถึงเมื่อยังไม่มี credentials จากนั้นใส่เฉพาะ `PREVIEW_USERNAME` และ `PREVIEW_PASSWORD` เป็น Worker secrets ไม่ต้องส่ง API-Football key สำหรับเว็บอ่าน snapshot
5. ตรวจจาก URL จริงว่าไม่มี credentials ได้ 401; มี credentials เปิดเว็บ/API ได้; internal routes ได้ 403; ค่า live/scheduler/auto-promotion ยังคงปิด
6. ทดสอบมือถือและบันทึก usage/CPU/D1 metrics จริงก่อนอนุมัติงานอัตโนมัติรอบถัดไป

แผนก่อน Deploy อยู่ใน `.cloudflare/preview-plan.json`; หลักฐานการดำเนินการจริงอยู่ใน `.cloudflare/deployment.json` ข้อมูลใน snapshot ยังมีเวลาบันทึกเดิม การย้ายขึ้นโฮสต์ไม่ได้ทำให้ข้อมูลสดหรือสร้างคำทำนายที่ยังไม่มีขึ้นมา

## CI และหลักฐานวิจัย

CI รอบแรกบน Linux หยุดที่ `v2_protocol_or_dataset_changed_use_new_version` เพราะ importer ที่ freeze ไว้สร้าง source-record ID จาก Windows path separators การแก้ CI ใช้ Windows สำหรับชุดวิจัย/Python เดิม และใช้ Linux ตรวจ frontend/API/Worker/Browser โดยอ่าน demo snapshots ที่บันทึกไว้ ไม่รันชุด API ที่ต้องสร้างฐานข้อมูลขนาดใหญ่ซ้ำบน Windows ซึ่งเคยติด hook timeout การเปลี่ยนนี้ไม่แก้ frozen training code, protocol, metrics หรือ model artifacts การทำ source IDs ให้ข้ามระบบได้ในอนาคตต้องเป็น dataset/model version ใหม่

HTTP Basic authentication ใช้สำหรับเว็บทดลองส่วนตัวผ่าน HTTPS ไม่ใช่ระบบสมาชิกหลายผู้ใช้ ระยะเปิดบริการต่อบุคคลอื่นต้องเลือกและทดสอบระบบสิทธิ์ที่เหมาะกับขอบเขตใหม่

อ้างอิงทางการ: [Workers assets routing](https://developers.cloudflare.com/workers/static-assets/), [Basic authentication](https://developers.cloudflare.com/workers/examples/basic-auth/), [D1 limits](https://developers.cloudflare.com/d1/platform/limits/), [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/), [Worker secrets](https://developers.cloudflare.com/workers/configuration/secrets/)
