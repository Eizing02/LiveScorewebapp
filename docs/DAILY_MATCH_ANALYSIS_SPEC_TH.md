# วิเคราะห์ความต้องการ: โปรแกรมวันนี้/คืนนี้ รายลีก รายคู่ และสรุปแนวทางประจำวัน

วันที่จัดทำ: 25 ตุลาคม 2026

สถานะ: ข้อเสนอการพัฒนาจากโค้ดที่ตรวจจริง ไม่ใช่ฟังก์ชันที่พัฒนาเสร็จแล้ว เอกสารนี้ไม่เปลี่ยน policy/model ที่ล็อกไว้ ไม่อนุญาตเรียก API จริง ไม่เพิ่มข่าว ไม่ promote โมเดล และไม่ deploy

## 1. ผลิตภัณฑ์ที่ต้องการ

ผู้ใช้เปิดเว็บแล้วเห็นโปรแกรมแข่งขันในช่วงเวลาที่เลือก แบ่งตามรายการแข่งขันอย่างถูกต้อง เปิดรายละเอียดรายคู่เพื่อดูข้อมูลย้อนหลังและความน่าจะเป็น จากนั้นดูรายงานประจำวันซึ่งแยกประเภทการคัดเลือก พร้อมผลตรวจสอบหลังแข่ง

เส้นทางหลัก:

โปรแกรมวันนี้/คืนนี้ → เลือกลีก → เลือกคู่ → วิเคราะห์รายคู่ → สรุปประจำวัน → ผลย้อนหลังของคำทำนายที่ล็อกแล้ว

มีการตัดสินใจสองระดับที่ต้องแยกกัน:

- แสดงโปรแกรมแข่งขัน: ต้องมี fixture/competition/team identity และเวลาเตะที่ตรวจสอบได้
- เผยแพร่คำทำนายหรือจัดเป็นคู่คัดเลือก: ต้องผ่าน coverage, freshness, history, approved model และ prediction cutoff เพิ่มเติม

ลีกที่มีโปรแกรมแต่โมเดลยังไม่รองรับสามารถแสดงโปรแกรมพร้อมสถานะไม่พร้อมวิเคราะห์ ห้ามนำโมเดลสามลีกไปใช้กับทุกลีกโดยอัตโนมัติ

## 2. สิ่งที่มีอยู่จริงและช่องว่าง

| ความต้องการ | หลักฐานปัจจุบัน | งานที่ต้องเพิ่ม |
|---|---|---|
| รายการแข่ง | App.tsx แสดง fixture จำลอง; API มี league/date/page | ช่วงเวลาวันไทย/คืนนี้, โหลดครบทุกหน้า, สถานะเลื่อนแข่ง, completeness |
| แยกรายลีก | มี league selector | กลุ่มรายการบนหน้าเดียว, ประเทศ/ฤดูกาล/รอบ, mapping ที่ยืนยัน |
| รายละเอียดคู่ | Drawer แสดง 1X2, Poisson goal rates, top 5 scores | หน้ารายคู่ที่มี URL, form, H2H, ค่าเฉลี่ย, data provenance, API blocks |
| ผลวิเคราะห์จากโมเดล | ฝึก League/Elo/Poisson/Logistic/XGBoost แล้ว | เลือก approved model แยกตาม prediction target และบันทึก version |
| สูง–ต่ำ/BTTS/ประตูรวม | มี Poisson score computation เป็นฐาน | distribution contract, market aggregations, calibration และ backtest แยกตลาด |
| คู่เด่นประจำวัน | มี selective research ของ 1X2 | daily ranking, abstention, immutable daily snapshots |
| ชุด 3/5 คู่ | ยังไม่มี | eligibility/selection policy, dependencies, full-set evaluation, void rules |
| API จริง | client/quota/cache + mock fixture adapter | date-range support, coverage/season verification, endpoints และ mappings เพิ่ม |

ข้อจำกัดโค้ดที่ต้องจัดการเมื่อเริ่มพัฒนา:

- หน้าเว็บเรียก /api/fixtures หน้าแรกครั้งเดียว ปัจจุบัน backend จำกัด 50 แถว/หน้า ต้องจัดการ pagination ก่อนอ้างว่าแสดงครบทุกคู่
- date filter ใช้ match_date ตรง ๆ ยังไม่ใช่ query ช่วง kickoff UTC ที่แปลงจากหน้าต่างวันไทย
- provider adapter ปัจจุบันรับ league/season/page และ schema fixture พื้นฐาน ยังไม่มี H2H/statistics/injuries/lineups/odds adapters
- /internal/predictions/import รับ 1X2 แต่ยังไม่รับ goal distribution/goal markets ดังนั้นเพิ่ม UI อย่างเดียวไม่พอ
- หน้า match อ่าน prediction ล่าสุดตาม generated_at ต้องเพิ่มการเลือก snapshot ตาม purpose, approved model, cutoff และ publication status
- feature cutoff ปัจจุบันเป็นระดับวันและ conservative ใช้เฉพาะวันก่อนหน้า หากต้องใช้ข้อมูลรายชั่วโมงก่อนเตะ ต้องเพิ่ม timestamp schema และทดสอบใหม่ ห้ามตีความวันที่เก่าเป็นเวลาเตะที่ยืนยันแล้ว

## 3. ความหมายของวันนี้และคืนนี้

ข้อกำหนดจากผู้ใช้: หนึ่งรอบวันเริ่ม 06:00 น. และสิ้นสุดก่อน 06:00 น. วันถัดไปตาม Asia/Bangkok ทุกหน้าระบุช่วงเวลาเต็มที่กำลังแสดง เก็บเวลาในฐานข้อมูลเป็น UTC

| ตัวเลือก | ช่วงเวลาไทย |
|---|---|
| วันนี้ | D 06:00 ถึงก่อน D+1 06:00 รวม 24 ชั่วโมง |
| คืนนี้ | D 18:00 ถึงก่อน D+1 06:00 |
| 24 ชั่วโมงข้างหน้า | เวลาปัจจุบันถึงก่อนอีก 24 ชั่วโมง |
| เลือกวันที่/ช่วงเอง | ถ้าเลือกวันที่ D ให้ใช้รอบ D 06:00 ถึงก่อน D+1 06:00; ช่วงกำหนดเองแสดงขอบเวลาเต็ม |

วันที่ D เป็นชื่อรอบตามวันเริ่ม: ถ้าเวลาปัจจุบันอยู่ระหว่าง 00:00 ถึงก่อน 06:00 ให้วันนี้อ้างรอบที่เริ่ม 06:00 ของวันก่อน เปลี่ยนรอบใหม่เวลา 06:00 เท่านั้น เกมหลังเที่ยงคืนยังอยู่ในรอบเดิมและแสดงวันที่/เวลาเตะจริงควบคู่กัน

คืนนี้เป็นตัวกรองย่อยในรอบเดียวกับวันนี้ เริ่ม D 18:00 ถึงก่อน D+1 06:00 เช่นเวลา 01:00 ให้แสดงคืนที่เริ่ม 18:00 ของวันก่อน พร้อมปุ่มเลือกคืนถัดไป

ใช้ขอบช่วง [start, end): เกมเตะ 05:59 อยู่รอบเดิม เกมเตะตรง 06:00 อยู่รอบใหม่ จัดรอบตามเวลาเริ่มแข่ง แม้เกมจบหลัง 06:00 ผลยังผูกกับรอบของเกมนั้น รวมรายการด้วย fixture identity เดิมเพื่อไม่ให้นับซ้ำ

สำหรับวันที่ตัวอย่าง D=2026-10-25 วันนี้คือ 25 ต.ค. 06:00 ถึงก่อน 26 ต.ค. 06:00 ไทย เทียบเท่า 24 ต.ค. 23:00 ถึงก่อน 25 ต.ค. 23:00 UTC ส่วนคืนนี้คือ 25 ต.ค. 18:00 ถึงก่อน 26 ต.ค. 06:00 ไทย เทียบเท่า 25 ต.ค. 11:00–23:00 UTC นี่เป็นตัวอย่างช่วงเวลา ไม่ใช่โปรแกรมแข่งขันจริง

รายงานคู่เด่น เต็ง ชุด 3/5 คู่ และผลประจำวันใช้รอบ 06:00 เดียวกัน เก็บ round date พร้อม timezone และ start/end ของรอบ ไม่เปลี่ยนเป็นรายงานวันใหม่เมื่อข้ามเที่ยงคืน ข้อกำหนดนี้ไม่เปลี่ยนเวลาตัดโควตาของ provider หรือผ่อนกติกา feature cutoff/training cutoff

scheduled, live, finished, postponed, cancelled, abandoned, awarded แสดงแยกกัน คู่ที่เริ่มแล้วไม่นำเข้ารายการคัดเลือกก่อนแข่งใหม่ การเลื่อนเวลาต้องตรวจ snapshot และ eligibility ใหม่

## 4. การจัดกลุ่มลีกและ identity

จัดกลุ่มด้วย canonical competition ID + season; ใช้ provider fixture ID เป็น identity ภายนอกและเก็บ mapping ที่ตรวจสอบได้

- ประเทศ → รายการ → ฤดูกาล/รอบ → fixtures เรียง kickoff
- รายการถ้วยคงอยู่ในรายการถ้วย ห้ามจัดเข้าลีกของทีมตามชื่อประเทศ/สโมสร
- ห้ามสร้างแมตช์จากการจับชื่อสองทีมเอง เพราะอาจเจอกันทั้งลีกและบอลถ้วย หรือมีทีมชุดใหญ่/เยาวชนชื่อใกล้กัน
- ใช้ season/round/leg/venue/status เป็นบริบทตรวจสอบ ไม่ใช้แทน stable provider fixture ID
- fixture ที่แก้ kickoff ยังคง identity เดิมและมี revision log
- coverage ของลีก/ฤดูกาลและข้อมูลครบทั้งหน้าหรือไม่ต้องแสดงแยกจาก readiness ของโมเดล

เริ่มการทำนายจาก Premier League, La Liga และ Bundesliga ซึ่งมี pipeline ฝึกอยู่แล้ว การขยายลีกต้องผ่าน data audit, training และ validation ของลีกนั้น

## 5. หน้าโปรแกรมและความหมายของคำว่าน่าสนใจ

แต่ละการ์ด: ชื่อรายการ, เวลาไทย, ทีมเหย้า/เยือน, สถานะ, ความสดข้อมูล, readiness, summary probability และเหตุผลสั้นที่ตรวจสอบได้

โหมดจัดอันดับต้องเลือกได้และตั้งชื่อให้ตรงเหตุการณ์:

1. ทีมชนะมีโอกาสสูง: ความน่าจะเป็นชนะจาก 1X2 ที่ผ่าน eligibility ของตลาดนี้
2. ประตูรวมคาดหมายสูง: E[home goals]+E[away goals] ใช้เรียงแนวโน้มประตู ไม่ใช่โอกาสถูกของสกอร์ตรง
3. สูง 2.5 มีโอกาสสูง: P(total goals >= 3) โดยระบุเส้นเสมอ
4. ต่ำ 2.5 มีโอกาสสูง: P(total goals <= 2)
5. ทั้งสองทีมทำประตู: P(home goals >= 1 and away goals >= 1)
6. คู่สำคัญที่ผู้ใช้ติดตาม: ความสนใจส่วนบุคคล แยกจาก confidence ของโมเดล

อย่าผสม P(1X), P(home win), P(over 0.5) และ P(exact score) ลง leaderboard เดียวแล้วเรียกทุกอย่างว่าความแม่น ตลาดเหล่านี้มีความง่ายและผลตอบแทนต่างกัน

หากต้องมีคะแนน /100 ให้ระบุว่าเป็นคะแนนจัดอันดับซึ่งต้องตรวจสอบ policy ต่างหาก ไม่ใช้แทนความน่าจะเป็นชนะ และไม่กำหนดน้ำหนัก H2H/form/API consensus ขึ้นเองโดยไม่มีผล validation

## 6. หน้ารายละเอียดรายคู่

### 6.1 สรุปก่อนเกม

- 1X2 พร้อม probabilities รวม 100%, ชื่อโมเดล/version และเวลาข้อมูล
- ประตูคาดหมายแยกทีมและรวม ระบุเป็นค่าจากแบบจำลอง ไม่ใช้ชื่อ provider xG
- top 3–5 exact scorelines พร้อม probability ของแต่ละสกอร์และ tail mass
- ความพร้อมในการคัดเลือก เหตุผลที่ผ่าน/ไม่ผ่าน และข้อมูลสำคัญที่ยังขาด
- generated_at, information_cutoff, training cutoff, data source และ locked snapshot

### 6.2 สถิติทีมก่อนเกม

ฟอร์ม 5/10/20 นัด, ชนะ/เสมอ/แพ้, ยิง/เสียรวมและเฉลี่ย, แยกเหย้า/เยือน, clean sheets, ไม่ยิงประตู, สูง/ต่ำตามเส้น, BTTS และแนวโน้มตามฤดูกาล

ทุกค่าเฉลี่ยแสดงจำนวนเกมและช่วงข้อมูลที่ใช้ ถ้ามีน้อยให้แสดงสถานะและ shrinkage ไม่ถือว่าข้อมูลขาดคือค่าศูนย์ ตารางอันดับ/ผู้เล่น/บาดเจ็บ/รายชื่อก่อนเกมเป็นข้อมูล API เสริมเมื่อ coverage และ season ใช้ได้

ระยะห่างจากเกมลีกล่าสุดไม่ใช่จำนวนวันพักจริง ถ้าไม่มีตารางถ้วย/ทีมชาติครบ ห้ามแสดงว่าเป็น fatigue/rest ที่ยืนยันแล้ว

### 6.3 Head-to-head

ค่าเริ่มต้นใช้การพบกันในรายการเดียวกับเกมเป้าหมาย มีตัวเลือกขยายเป็นทุกรายการและแสดงรายการของทุกแมตช์อย่างชัดเจน

- แสดง 5/10 นัดก่อน cutoff ตามข้อมูลที่มี ไม่แสดง 10 ถ้าจริงมี 4
- สรุปทีม A ชนะ/เสมอ/ทีม B ชนะ โดยคง orientation ของทีมปัจจุบันแม้เกมเก่าสลับเหย้าเยือน
- ประตูรวม/เฉลี่ย, ยิง/เสียของแต่ละทีม, ส่วนต่างเฉลี่ย และสกอร์ย้อนหลัง
- ระบุวันที่, รายการ, สนามเหย้า/เยือน และจำนวนตัวอย่าง
- เลื่อน/ยกเลิก/ข้อมูลไม่ยืนยันไม่นับเป็นผลเล่นจบ; administrative awards แยก; บอลถ้วยแยก 90 นาที/ต่อเวลา/จุดโทษ

H2H เป็นข้อมูลบริบทก่อน ในการฝึกต้องทดสอบว่าช่วยนอกเหนือ form/strength หรือไม่ ข้อมูลข้ามผู้จัดการ/ขุมกำลังหลายปีไม่ควรมีน้ำหนักสูงเพราะคำว่าเจอกันชนะบ่อยอย่างเดียว

### 6.4 ข้อมูล API และการเปรียบเทียบ

ข้อมูล provider ที่เข้ามาไม่ทำให้โมเดลใช้ฟีเจอร์ใหม่โดยอัตโนมัติ ต้องเพิ่ม feature schema, missingness policy, point-in-time provenance และฝึก/ทดสอบใหม่

หากเปิด /predictions ของ provider ให้แสดงในช่องผู้ให้บริการแยกจากโมเดลเรา มีเวลาที่ดึงและค่า missing ชัดเจน ยังไม่เฉลี่ยสองผลเข้าด้วยกันหรือถือว่าความเห็นตรงกันเป็นหลักฐานอิสระ

ผลทำนายย้อนหลังของ API ที่ไม่ได้เก็บก่อนเตะห้ามสมมติว่าสามารถย้อนเรียกมาเป็น historical feature ได้ หากใช้เป็นฟีเจอร์ต้องเก็บ prospective snapshots และประเมินช่วงอนาคต

ไม่เพิ่ม news integration ตามคำสั่งผู้ใช้

## 7. โมเดลประตูและตลาดที่ต้องแยกประเมิน

ปัจจุบัน Logistic เป็น candidate จากการเปรียบเทียบ 1X2 ส่วน Poisson เป็นฐานการคำนวณสกอร์/ประตู ไม่ถือว่าโมเดลที่ดีที่สุดสำหรับ 1X2 ต้องดีที่สุดสำหรับสูง–ต่ำ

ให้ score distribution กำหนด p(h,a) โดยเก็บ mass/tail และตรวจความถูกต้อง:

- P(home win)=sum p(h,a) เมื่อ h>a; draw เมื่อ h=a; away เมื่อ h<a
- P(over 2.5)=sum p(h,a) เมื่อ h+a>=3
- P(BTTS)=sum p(h,a) เมื่อ h>=1 และ a>=1
- E[total]=E[h]+E[a]
- Exact score ใช้ p(h,a) โดยตรง

เริ่มเส้น 1.5/2.5/3.5 ก่อน เส้นเต็มและ .25/.75 ต้องมี push/half-win/half-loss settlement และการทดสอบเพิ่มก่อนเผยแพร่ ไม่ใช้ binary win/loss อย่างเดียว

ระบุ model head ของแต่ละผลให้ชัดเจน หาก 1X2 ใช้ Logistic และตลาดประตูใช้ Poisson ตัวเลขอาจไม่ตรงกับ 1X2 ที่รวมจาก Poisson ห้ามแสดงเหมือนมาจาก joint distribution เดียวกัน การผสานให้ coherent ต้องผ่าน validation เพิ่ม ไม่แก้ตัวเลขให้ตรงเอง

ตัวอย่างคำนวณสมมติ ไม่ใช่โปรแกรมจริงหรือผล backtest: independent Poisson rates เหย้า 1.8 เยือน 0.9 ให้

- ประตูรวมคาดหมาย 2.70
- 1X2 ประมาณ 58.61% / 22.90% / 18.50% (รวมที่แสดงอาจต่างจาก 100 เล็กน้อยเพราะปัดเศษ)
- สูง 2.5 ประมาณ 50.64%; BTTS ประมาณ 49.53%
- สกอร์ที่มีโอกาสสูงสุด 1–0 ประมาณ 12.10%

ตัวอย่างนี้แสดงว่า expected goals, ชนะ, สูง–ต่ำ และสกอร์ตรงเป็นคนละเหตุการณ์ การเป็นสกอร์อันดับหนึ่งไม่ได้ทำให้สกอร์นั้นมีโอกาส 70–80%

## 8. กติกาคัดเลือกและ abstention

ชั้นแรกเป็น hard gates: fixture/league/team mapping ยืนยัน, kickoff ยืนยันและยังไม่เริ่ม, coverage/current-season ใช้ได้, feed สด, features อยู่ก่อนเวลาทำนาย, approved model, probabilities valid, ไม่มี quarantine/contradiction

จากนั้นใช้ selection policy แยกตามตลาดที่เลือกบน validation เท่านั้น เช่น confidence, history adequacy, calibration, stability และ minimum sample per league การเพิ่มเงื่อนไขต้องพิสูจน์ incremental benefit ไม่ถือว่ามีเงื่อนไขมากย่อมแม่นขึ้น

ให้ผลลัพธ์เป็น selected/watch/insufficient_data/rejected พร้อม reason codes ไม่บังคับว่าทุกวันต้องมีเต็งหรือครบ 3/5 คู่

threshold 0.70 ของงาน 1X2 เดิมเป็น research policy เดิมเท่านั้น ไม่ย้ายไปใช้กับสูง–ต่ำ/BTTS หรือสร้างนโยบาย live ที่อนุมัติแล้ว

หลักฐานที่มี: test 2025/26 เลือก 67 จาก 1,066 คู่ ถูก 57 (85.07%), coverage 6.29%, confirmation=false เพราะจำนวนรวมและ EPL ไม่พอ ตัวเลขนี้ไม่ใช่ผลสูง–ต่ำ ไม่ใช่ผลสกอร์ตรง ไม่ใช่อัตราถูกครบชุด และไม่รับรองว่าจะคัดได้ 3–5 คู่ทุกคืน

## 9. รายงานประจำวัน

รายงานของแต่ละช่วงเวลามี:

- จำนวน fixture ที่พบ, จำนวนลีก, coverage และจำนวนผ่าน eligibility
- คู่เด่นแบบเดี่ยว แยก market/line/outcome
- เกมประตูรวมคาดหมายสูง และอันดับสูง/ต่ำ/BTTS แยกกัน
- ชุด 3 คู่ และ 5 คู่เฉพาะเมื่อมีคู่ผ่าน policy เพียงพอ
- คู่ที่เฝ้าดู/รอข้อมูล พร้อมเหตุผล
- เวลาสร้าง report, data cutoff, policy version, model version และ snapshot ID
- หลังแข่งแสดงผลทุก pick รวมทั้งไม่ถูก เลื่อน หรือ void ตามกติกาที่ประกาศไว้

เก็บรายการทั้งหมดที่มีสิทธิ์ในตอนจัดอันดับ รวมที่ไม่ถูกเลือก เพื่อให้ตรวจ coverage และป้องกันเลือกแสดงย้อนหลังเฉพาะคู่ถูก

## 10. เต็งและชุด 3/5 คู่

เต็งในสเปกหมายถึง single selection ระบุ market/line/outcome ตายตัว ไม่ใช่รับประกันชนะ ชุดหมายถึงต้องถูกครบตามนิยาม settlement ที่ล็อกไว้

คำนวณประกอบเพื่ออธิบายภายใต้สมมติฐานแต่ละขาเป็นอิสระและ probability ถูกต้อง:

| โอกาสถูกแต่ละขา | ถูกครบ 3 | ถูกครบ 5 |
|---:|---:|---:|
| 70% | 34.30% | 16.81% |
| 80% | 51.20% | 32.77% |
| 85% | 61.41% | 44.37% |

สูตร product เป็นเพียง independent estimate ไม่ใช่ probability ที่ยืนยันแล้ว การจำลองแมตช์แบบอิสระซ้ำจำนวนมากก็ไม่ได้แก้ dependency ข้ามเกม

ข้อเสนอเริ่มต้น:

- ใช้คนละ fixture ในชุดเดียว ไม่เลือก home win + over จากแมตช์เดียวกันแล้วคูณ probability เหมือนอิสระ
- ไม่บังคับเลือกคนละลีกเสมอ แต่แสดง concentration และปัจจัยร่วม; คนละลีกไม่ได้แปลว่าเป็นอิสระ
- ถ้าเป็น same-game combination ในอนาคต ต้องคำนวณ joint event จาก joint score model โดยตรงและทดสอบแยก
- ไม่เพิ่มคู่คุณภาพต่ำเพื่อให้ครบจำนวน วันไม่มีชุดผ่านเกณฑ์แสดงเหตุผลตรง ๆ
- แสดงขาทั้งหมดและผลชุดครบ; รายงาน leg accuracy แยกจาก full-set hit rate
- ถ้าสร้างหลายชุดในวันเดียว ต้องนับทุกชุดและ exposure ที่ทับกัน ไม่เอาชุดที่ถูกชุดเดียวมาเป็นผลวันนั้น
- เลื่อน/ยกเลิก/เปลี่ยน venue หรือ lineup สำคัญต้องทำ report revision/withdrawal ก่อนเตะ พร้อมรักษาประวัติ ไม่ลบคำแนะนำเดิม

โอกาสเกิดสูงยังไม่ใช่ความคุ้มค่าราคา หากไม่มี odds ที่ตรวจสอบ market/line/time/bookmaker ได้ ไม่จัดอันดับเป็น value และไม่รายงานกำไรจำลอง การประเมิน EV/ROI ต้องมีราคา ณ เวลาคัดเลือกและ payout/void rules ที่ถูกต้องเพิ่มต่างหาก

## 11. Backtest และการวัดผล

แยกโมเดล/นโยบายของ 1X2, totals, BTTS, exact score และชุด ไม่สืบทอดความแม่นข้าม target

- 1X2: multiclass Log Loss, Brier, accuracy, calibration, per league, sample/CI
- Totals/BTTS: binary Log Loss, Brier, calibration, selected hit rate, coverage แยกแต่ละเส้น/ลีก
- Goal distribution: likelihood/log score, mean-goal error และ tail diagnostics
- Exact score: joint log score, top-1/top-k coverage โดยระบุ k ไม่เทียบ accuracy กับ 1X2 แบบตรง ๆ
- ชุด: จำนวนวัน/ชุดที่ผ่าน, full-set hit rate, leg hit rate, skip rate, void/revision count; uncertainty แบบกลุ่มวันและรายงานการพึ่งกัน

Replay รายงานประจำวันจากข้อมูลที่ทราบ ณ เวลาจัดจริง รวมสิ่งที่ไม่ถูกเลือก ห้ามใช้ standings จบฤดูกาล รายชื่อหลังแข่ง หรือสถิติที่อัปเดตหลัง cutoff ย้อนเข้ามา

ล็อก protocol ก่อนประเมิน การออกแบบตลาดใหม่บนข้อมูลเดิมทำได้ในฐานะ exploratory research แต่ช่วงทดสอบเดิมเห็นผลแล้ว จึงใช้ยืนยันซ้ำหลังปรับกติกาไม่ได้ ต้องมีช่วงอนาคตที่ยังไม่เปิดดูหรือ prospective shadow collection

ทดสอบเพิ่ม: รอบ 06:00–06:00 ไทย (05:59, 06:00, ข้ามเที่ยงคืน, เวลาปัจจุบันก่อน 06:00, แปลง UTC และเกมจบข้ามรอบ), ทั้งหมดหลายหน้า, ลีก/บอลถ้วย, identity สลับเหย้าเยือน, same teams multiple fixtures, postponed revisions, missing values, same-day leakage, probability sums/complements/monotonicity, score tail, bundle duplicates, snapshot immutability และ deterministic ranking/tie-break

## 12. API และข้อจำกัดฟรี

แผน API-Football ฟรีระบุ 100 requests/day และจำกัดฤดูกาลที่เข้าถึงได้ ต้องตรวจบัญชีจริงก่อนว่าได้ฤดูกาลปัจจุบันของทั้งสามลีกหรือไม่ เอกสารที่มี endpoint ไม่ใช่หลักฐานว่าบัญชีฟรีมี current-season payload ที่ต้องการ

ลำดับข้อมูลที่เสนอ: /leagues coverage/season → /fixtures → team mappings → ผลย้อนหลัง/standings → /teams/statistics และ /fixtures/headtohead → /injuries หรือ /fixtures/lineups ตาม coverage และ quota → /predictions หรือ odds เป็น optional

ตรวจ support และจำนวนหน้าของแต่ละ endpoint ก่อนออกแบบ query จริง ไม่นำ page semantics ของ endpoint หนึ่งไปสมมติกับทุก endpoint

ใช้ OpenFootball/D1 คำนวณ form/H2H/ค่าเฉลี่ยเท่าที่มีและยืนยัน mapping ได้ เก็บขอบเขตข้อมูลชัดเจน ข้อมูลเพิ่มจาก API ดึงเป็น batch/cache ฝั่ง Worker ผู้ใช้เปิดหน้าคู่ไม่ควรยิง provider ทุกครั้ง

ตัวอย่างงบประมาณออกแบบเท่านั้น ไม่ใช่จำนวนที่เรียกแล้ว และสมมติแต่ละ query ได้ครบในหนึ่ง request:

| งาน | เพดานตัวอย่าง requests/day |
|---|---:|
| coverage สามลีก | 3 |
| fixtures สามลีก สองวัน สองรอบ | 12 |
| H2H รายละเอียดสูงสุดหกคู่ cache miss | 6 |
| team statistics สูงสุดสิบสองทีม cache miss | 12 |
| injuries รายลีกสองรอบ หากรองรับ | 6 |
| provider predictions สูงสุดหกคู่ หากเปิดใช้ | 6 |
| ผลแข่ง/reconciliation ตามที่ตรวจแล้ว | 20 |
| รวมตัวอย่าง | 65 |

ยังต้องหัก retries, pagination, bootstrap และงานอื่นจากงบจริง ปิด optional blocks เมื่อ quota ไม่พอ ห้ามแสดงข้อมูลเก่าเหมือนสด การอัปเดต lineups ใกล้เตะทุกคู่/ทุกลีกและ livescore ต่อเนื่องไม่ใช่สิ่งที่รับรองภายในตัวอย่างงบนี้

สอดคล้องกับ quota manager เดิม: normal requests หยุดที่ยอดใช้ 65, result-priority ใช้ได้ถึง 95 และกัน 5 ไม่ใช้ โดยต้องยืนยัน provider reset/rate headers ก่อน live

## 13. สถาปัตยกรรมและ data contracts ที่เสนอ

Worker Cron → provider adapter + quota/cache → normalized D1 fixtures/results → versioned feature snapshots → Python batch models → prediction/market snapshots → daily selection → React reads จาก D1

Python training/inference หนักใช้ GitHub Actions ตาม workflow ที่เตรียมไว้ งาน realtime ที่ย้ายเข้า Worker ต้องมี artifact/schema parity และ golden-output verification Cloud jobs จะทำงานโดยไม่เปิดเครื่องส่วนตัวได้หลังเชื่อม/deploy ตามการอนุมัติเท่านั้น

ตาราง/สัญญาข้อมูลเพิ่มเติมที่ควรออกแบบเป็น migration ใหม่เมื่อเริ่ม implementation:

- competition coverage / provider mappings / fixture revisions
- point-in-time team stats และ provider prediction snapshots
- goal-distribution หรือ model goal-rate snapshots พร้อม market probabilities/line/outcome
- selection_policy_versions, daily_reports, daily_report_items
- combination_groups, combination_legs, settlements และ report revisions

API ของแอปที่เสนอ: fixtures ตาม start/end/timezone + league + pagination; match analysis ตาม fixture ID; daily report ตาม window/policy; report history/results พร้อม snapshot ID ไม่ผูกการเรียกของ browser กับ provider request โดยตรง

initial/refresh/final เป็น prediction versions ที่ตรวจสอบได้ ทุก report อ้าง exact prediction snapshot และ freeze ก่อนเกมของขานั้นเริ่ม หาก report มีหลายเวลาเตะ ห้ามเปลี่ยนขาที่ย้อนกลับมาแข่งจบแล้วให้ดูเป็นคำแนะนำใหม่

แยก cutoff ของ daily report ที่ใช้จัดอันดับกับ final pre-match snapshot อย่าใช้ final ของบางคู่ที่ยังไม่มี ณ เวลาจัดรายงานมา replay รายงานก่อนหน้านั้น

## 14. ลำดับทำงานที่เหมาะสม

1. โปรแกรมวันนี้/คืนนี้ + timezone/range + pagination + grouped leagues + mock data หลายสถานะ
2. หน้ารายคู่ + descriptive statistics/H2H จากข้อมูลที่มี + provenance/sample/cutoff
3. Goal-market computations + invariants + frozen protocol + exploratory walk-forward ก่อน prospective confirmation
4. รายงานประจำวัน/คู่เดี่ยว/abstention + immutable snapshots + evaluation
5. ชุด 3/5 คู่พร้อมกติกาเฉพาะและผลทั้งชุด หลังระบบรายคู่มีหลักฐานพอ
6. หลังผู้ใช้อนุมัติ live integration: ตรวจบัญชี/ฤดูกาล/coverage/request budget แล้วเชื่อม API จริง จากนั้น shadow predictions ก่อนอนุมัติ model promotion และ production deployment

ไม่ต้องรอ API เพื่อเริ่มข้อ 1–5 ด้วย mocks/ข้อมูลย้อนหลัง แต่ห้ามอ้างเป็นโปรแกรมหรือคำทำนายปัจจุบันจริง และห้ามถือว่าผลตลาดใหม่ผ่านการยืนยันแล้วเพียงเพราะโค้ดคำนวณได้

## 15. แหล่งอ้างอิงที่ตรวจ

- API-Football pricing: https://www.api-football.com/pricing — 100/day, free-season restrictions
- API-Football official endpoint/coverage guide: https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide — fixtures, H2H, team statistics, injuries, predictions, coverage และ caching
- โค้ดที่ตรวจ: apps/web/src/App.tsx, apps/api/index.ts, apps/api/provider.ts, packages/prediction/index.ts
- หลักฐานวิธีประเมิน: docs/ML_METHODOLOGY.md, ml/config/policy.json, ml/config/selection_policy_v1.json, reports/selection-v1/new-test.json

การทำงานรอบนี้: ตรวจโค้ดและเอกสารสาธารณะ คำนวณตัวอย่าง Poisson/ชุดด้วย Python และเพิ่มเอกสารนี้เท่านั้น ไม่แก้ runtime code/ฐานข้อมูล/โมเดล ไม่เรียก authenticated API-Football ไม่เพิ่ม secrets ไม่ deploy
