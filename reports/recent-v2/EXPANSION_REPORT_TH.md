# ผลพัฒนา Football Prediction AI: ข้อมูล 5 ปีและ Match Centre

รายงานรอบ 25–26 ตุลาคม 2026 · โปรเจกต์ D:/Football Prediction AI

## ผลงานที่ใช้งานได้ในเครื่อง

- โปรแกรมตามรอบไทย 06:00–06:00 และคืนนี้ 18:00–06:00 แยกรายลีก โหลดหลายหน้าและเลือกวันที่
- รายคู่มี deep links, 1X2, ประตูคาดหมาย, สกอร์, สูง–ต่ำ 1.5/2.5/3.5, BTTS, ฟอร์ม 5/10/20, เหย้า–เยือน และ H2H ก่อน cutoff
- สรุปคู่เดี่ยว เกมประตูสูง และชุด 3/5 คู่แบบวิจัย ไม่เติมคู่ที่ไม่ผ่านเกณฑ์ และไม่ใช้ fixture/ทีมซ้ำในชุด
- Immutable model/dataset/report snapshots, checksum, signed locking/evaluation และเปิดดู exact snapshot เก่าตามลิงก์ได้
- ตารางคะแนนโมเดล/ตลาด/ค่าพื้นฐานลีก และคุณภาพข้อมูลพร้อมจำนวนแยกฤดูกาล

ทุกโปรแกรมปัจจุบันยังเป็นข้อมูลสาธิต ผลย้อนหลัง/metrics คำนวณจริง ไม่มี API-Football จริง ไม่มี deploy ไม่มีโมเดล active

## ข้อมูลที่รับ

ช่วง 2021-10-25 ถึงก่อน 2026-10-25 · 17,027 นัด · 12 ลีก

| ลีก | นัดรับฝึก |
|---|---:|
| Bundesliga | 1,510 |
| 2. Bundesliga | 1,489 |
| Premier League | 1,860 |
| Championship | 2,687 |
| La Liga | 1,864 |
| Segunda División | 453 |
| Ligue 1 | 1,612 |
| Ligue 2 | 306 |
| Serie A | 1,850 |
| Serie B | 379 |
| Eredivisie | 1,504 |
| Primeira Liga | 1,513 |

ตารางทุกลีก/ฤดูกาลอยู่ quality-by-season.csv และข้อมูลด้านล่าง จำนวนรับของ 2021/22 ถูกตัดตามขอบหน้าต่างห้าปี ส่วน 2026/27 เป็นผลที่บันทึกแล้วในฤดูกาลที่ยังไม่ครบ

| ลีก | ฤดูกาล | รับ | กัก | นอกช่วง | ผลตรงกันข้ามแหล่ง |
|---|---|---:|---:|---:|---:|
| Bundesliga | 2021-22 | 225 | 0 | 81 | 225 |
| Bundesliga | 2022-23 | 306 | 0 | 0 | 306 |
| Bundesliga | 2023-24 | 306 | 0 | 0 | 306 |
| Bundesliga | 2024-25 | 306 | 1 | 0 | 305 |
| Bundesliga | 2025-26 | 306 | 0 | 0 | 306 |
| Bundesliga | 2026-27 | 61 | 515 | 0 | 36 |
| 2. Bundesliga | 2021-22 | 207 | 0 | 99 | 207 |
| 2. Bundesliga | 2022-23 | 306 | 0 | 0 | 306 |
| 2. Bundesliga | 2023-24 | 306 | 0 | 0 | 306 |
| 2. Bundesliga | 2024-25 | 303 | 6 | 0 | 303 |
| 2. Bundesliga | 2025-26 | 306 | 207 | 0 | 99 |
| 2. Bundesliga | 2026-27 | 61 | 242 | 3 | 0 |
| Premier League | 2021-22 | 290 | 0 | 90 | 0 |
| Premier League | 2022-23 | 380 | 0 | 0 | 0 |
| Premier League | 2023-24 | 380 | 0 | 0 | 0 |
| Premier League | 2024-25 | 380 | 0 | 0 | 0 |
| Premier League | 2025-26 | 380 | 0 | 0 | 0 |
| Premier League | 2026-27 | 50 | 330 | 0 | 0 |
| Championship | 2021-22 | 384 | 5 | 168 | 0 |
| Championship | 2022-23 | 552 | 5 | 0 | 0 |
| Championship | 2023-24 | 552 | 5 | 0 | 0 |
| Championship | 2024-25 | 552 | 5 | 0 | 0 |
| Championship | 2025-26 | 552 | 5 | 0 | 0 |
| Championship | 2026-27 | 95 | 457 | 0 | 0 |
| La Liga | 2021-22 | 285 | 0 | 95 | 0 |
| La Liga | 2022-23 | 380 | 0 | 0 | 0 |
| La Liga | 2023-24 | 380 | 0 | 0 | 0 |
| La Liga | 2024-25 | 370 | 10 | 0 | 0 |
| La Liga | 2025-26 | 380 | 0 | 0 | 0 |
| La Liga | 2026-27 | 69 | 311 | 0 | 0 |
| Segunda División | 2024-25 | 453 | 9 | 0 | 0 |
| Segunda División | 2025-26 | 0 | 462 | 0 | 0 |
| Ligue 1 | 2021-22 | 271 | 0 | 109 | 0 |
| Ligue 1 | 2022-23 | 380 | 0 | 0 | 0 |
| Ligue 1 | 2023-24 | 306 | 0 | 0 | 0 |
| Ligue 1 | 2024-25 | 305 | 1 | 0 | 0 |
| Ligue 1 | 2025-26 | 305 | 1 | 0 | 0 |
| Ligue 1 | 2026-27 | 45 | 261 | 0 | 0 |
| Ligue 2 | 2024-25 | 306 | 0 | 0 | 0 |
| Ligue 2 | 2025-26 | 0 | 306 | 0 | 0 |
| Serie A | 2021-22 | 290 | 0 | 90 | 0 |
| Serie A | 2022-23 | 380 | 0 | 0 | 0 |
| Serie A | 2023-24 | 380 | 0 | 0 | 0 |
| Serie A | 2024-25 | 370 | 10 | 0 | 0 |
| Serie A | 2025-26 | 380 | 0 | 0 | 0 |
| Serie A | 2026-27 | 50 | 330 | 0 | 0 |
| Serie B | 2024-25 | 379 | 11 | 0 | 0 |
| Serie B | 2025-26 | 0 | 380 | 0 | 0 |
| Eredivisie | 2021-22 | 218 | 0 | 88 | 0 |
| Eredivisie | 2022-23 | 306 | 0 | 0 | 0 |
| Eredivisie | 2023-24 | 306 | 0 | 0 | 0 |
| Eredivisie | 2024-25 | 306 | 0 | 0 | 0 |
| Eredivisie | 2025-26 | 305 | 1 | 0 | 0 |
| Eredivisie | 2026-27 | 63 | 243 | 0 | 0 |
| Primeira Liga | 2021-22 | 227 | 0 | 79 | 0 |
| Primeira Liga | 2022-23 | 306 | 0 | 0 | 0 |
| Primeira Liga | 2023-24 | 306 | 0 | 0 | 0 |
| Primeira Liga | 2024-25 | 306 | 0 | 0 | 0 |
| Primeira Liga | 2025-26 | 306 | 0 | 0 | 0 |
| Primeira Liga | 2026-27 | 62 | 244 | 0 | 0 |

## แหล่งข้อมูลและการกัก

- OpenFootball SHA e6744429ee395bc86f247348c6184bb08d4eb361 (CC0)
- OpenLigaDB snapshot แช่แข็ง URL/เวลา/เนื้อหา SHA256 ภายใต้ ODbL พร้อม attribution; เพิ่มผลที่มีเฉพาะแหล่งนี้ใน accepted 294 นัด
- ผลตรงกันสองแหล่ง 2,705 นัด; รวมหลักฐานซ้ำ 2,885 รายการ ไม่นับซ้ำเป็นเกมฝึก
- Fjelstul อังกฤษแยก CC-BY-SA: สกอร์ตรง 2,538 นัด ไม่มีวันที่รายนัดจึงใช้ยืนยัน chronology ไม่ได้ และไม่รวม reference labels เข้าชุดฝึก
- สำรวจ 11 กลุ่มแหล่งข้อมูล รายละเอียด reports/historical-source-catalog.json ไม่อ้างว่าค้นหมดทุกแหล่งบนอินเทอร์เน็ต
- Football-Data.co.uk ระบุข้อห้าม data-training products ผ่าน bots/scrapers/AI จึงไม่ดึงข้อมูลหรือใช้ mirrors เลี่ยงเงื่อนไข; แหล่งอื่นที่สิทธิ์/coverage ยังไม่ยืนยันถูกพักไว้
- กัก 4,363 รายการ รวม unplayed/missing/format ที่ไม่รองรับ ไม่ได้หมายความว่าทั้งหมดเป็นสกอร์ผิด

| เหตุผล | รายการ |
|---|---:|
| non_regular_round | 35 |
| status_awarded | 3 |
| missing_score | 3,272 |
| status_cancelled | 2 |
| status_postponed | 2 |
| unplayed_or_unconfirmed | 470 |
| unresolved_cross_source_team | 17 |
| cross_source_date_conflict | 2 |
| cross_source_score_conflict | 4 |
| incomplete_closed_season | 556 |

ความขัดแย้งข้ามแหล่งกักทั้งสองฝั่ง ไม่เลือกแก้ผลเงียบ ๆ ไม่แปลง missing เป็น 0–0 และหลักฐานเดิม 66 นัด EPL 2019/20 ไม่ถูกนำกลับเข้าฝึก

## ผลโมเดล 1X2 ที่รันจริง

ประเมิน 3,220 นัดใน 2025/26; แต่ช่วงเวลาเคยถูกตรวจแล้ว จึงเป็น exploratory retrospective ไม่ใช่ final holdout ที่ยังไม่เคยเห็น

| โมเดล | Log Loss | Brier | Accuracy |
|---|---:|---:|---:|
| league | 1.0768 | 0.6515 | 43.60% |
| elo | 1.0179 | 0.6088 | 50.03% |
| poisson | 1.0215 | 0.6121 | 48.82% |
| logistic | 1.0087 | 0.6035 | 49.38% |
| xgboost | 1.0090 | 0.6036 | 49.91% |

เลือก logistic จาก validation ตาม Log Loss โมเดลที่ Accuracy สูงสุดอาจเป็นคนละตัว ความต่างจาก XGBoost มีขนาดเล็กและไม่ใช่หลักฐานยืนยันความเหนือกว่าในอนาคต

## ตลาดประตูและค่าพื้นฐาน

Accuracy binary ด้านล่างตัดสินทั้งการเกิด/ไม่เกิดที่เกณฑ์ 0.5 ไม่ใช่อัตราถูกของการเลือกฝั่งสูงอย่างเดียว ไม่ใช่ผลชุด และไม่ใช่ผลเฉพาะคู่ที่ผ่าน threshold 70%

| ตลาด | Poisson LL | พื้นฐานลีก LL | Poisson Accuracy | พื้นฐาน Accuracy |
|---|---:|---:|---:|---:|
| over_1.5 | 0.5327 | 0.5281 | 77.61% | 77.70% |
| over_2.5 | 0.6928 | 0.6868 | 54.44% | 54.32% |
| under_3.5 | 0.6078 | 0.6042 | 69.41% | 70.09% |
| btts_yes | 0.6946 | 0.6847 | 52.86% | 56.12% |

เหตุผลที่ยังไม่อนุมัติ: Poisson ตลาดประตูรอบนี้ไม่ชนะค่าพื้นฐานใน Log Loss/Brier จึงต้องปรับโมเดล/ตรวจ calibration และยืนยันช่วงอนาคต ไม่ยกตัวเลขเหตุการณ์ที่เกิดบ่อยมาอ้างว่า AI แม่น 80%

ผลรายลีก calibration bins และ 95% CI แบบ date-cluster อยู่ backtest.json; ไม่พบ test sample ของ Segunda/Serie B/Ligue 2 ในช่วง 2025/26 ที่ผ่านข้อมูล จึงไม่อ้างผลสำหรับสามลีกนี้

## Registry และการทำซ้ำ

Candidate: recent-v2-88aa9869efd8

ZIP: reports\recent-v2\recent-v2-88aa9869efd8.zip

SHA256: 24679983fbddb7d9f2a8c8f1c002012df2ab3431ac8ea70c5b2fde6404dcf5e1

โมเดลมี feature schema, config, training cutoff, dataset version, source manifest, metrics, runtime และ checksums; active_version=null และ MODEL_AUTO_PROMOTE=false การรัน importer และฝึกซ้ำทั้งชุดให้ dataset/version/ไฟล์โมเดลตรงกันบน runtime นี้ (reproducibility.json)

ZIP อยู่ถาวรใน workspace พร้อม SHA256 เตรียมเก็บใน Git/immutable GitHub Release เมื่ออนุมัติ ยังไม่อัปโหลดและไม่พึ่ง Actions Artifact ที่หมดอายุเป็นแหล่งเก็บเพียงแห่งเดียว

## ทดสอบ

Python 38 ผ่าน · TypeScript/D1 33 ผ่าน · Browser desktop/mobile 3 ผ่าน

Lint/Ruff/TypeScript/Vite build/Worker dry-run ผ่าน · npm production audit 0 vulnerabilities · local migrations/seed สำเร็จ · provider requests จริง API-Football 0 · deployment 0

ทดสอบข้อมูลซ้ำ/ขัดแย้ง/missing, chronological leakage, local/UTC consistency, round 05:59/06:00/ข้ามเที่ยงคืน, probabilities/complements, หลายหน้า/จำนวน query, H2H orientation, immutable snapshots, exact model references, grading pending/void และ reproducibility

มีคำเตือน Wrangler dev เมื่อ browser ยกเลิก request ระหว่างนำทาง แต่ scenario ผ่านและ browser pageerror เป็นศูนย์ ไม่มีการปิด security controls

## ไฟล์สำคัญที่สร้าง/แก้

- ml/config/expanded_policy_v2.json, source_snapshot_v2.json — เวลาข้อมูล/ลีก/เกณฑ์และ snapshot pin
- ml/expanded.py, recent_evaluate.py, goal_markets.py, market_benchmarks.py — importer/merge/quality/ฝึก/ประเมิน
- scripts/fetch_additional_history.py, source_snapshot.py, crosscheck_history.py — แหล่งเพิ่มและตรวจย้อนกลับ
- scripts/prepare_centre.py, seed_recent.mjs, package_recent_model.py, verify_recent_reproducibility.py — เตรียมข้อมูลเว็บ/โมเดล/ตรวจทำซ้ำ
- packages/football/window.ts, markets.ts, selection.ts, settlement.ts, types.ts — กติกาเวลา/ตลาด/คัด/ตรวจผล
- apps/api/analysis.ts, index.ts — endpoints และ signed operations
- db/migrations/0004_match_centre.sql, 0005_centre_query_indexes.sql, db/seed-centre.sql — D1 และ indexes
- apps/web/src/App.tsx, MatchCentre.tsx, MatchDetail.tsx, ResearchEvidence.tsx, centre.css, main.tsx — UI
- ml/tests/test_expanded.py, tests/football.test.ts, analysis.test.ts, tests/ui/centre.spec.ts และ tests เดิมที่ปรับ selectors — tests
- .github/workflows/recent-research.yml, ci.yml — manual research และ CI; ไม่ได้ execute บน GitHub จริง
- data/snapshots/, data/ATTRIBUTION.md, README.md, docs/RECENT_EXPANSION_TH.md — ชุดต้นฉบับ/สิทธิ์/วิธีใช้

## ข้อจำกัดและขั้นต่อไป

1. ต่อ API จริงหลังตรวจสิทธิ์ฤดูกาลปัจจุบัน Coverage, identity/timezone, paging, quota/reset และงบ requests โดยไม่เปิดเผย key
2. เชื่อม current results/feature updates และ optional player data ตามสิทธิ์ ไม่แทนข้อมูลขาดด้วยศูนย์
3. ปรับ/สอบเทียบตลาดประตูที่ยังแพ้ baseline โดยใช้ validation แล้วล็อกกติกาก่อนเก็บ prospective test
4. เก็บคำทำนายและรายงานก่อนเตะจริงเพื่อวัดถูกครบชุด/coverage/uncertainty ไม่มีการสมมติ ROI หรืออัตราถูกชุด
5. จึงค่อยอนุมัติ promotion และ Cloudflare/GitHub production automation ปัจจุบันยังต้องเปิด local preview เอง

## เปิดดู

ใน D:/Football Prediction AI เปิดสอง terminal: npm run dev:api และ npm run dev แล้วใช้ URL ที่ Vite แสดง รายละเอียด setup/rebuild อยู่ README และ docs/RECENT_EXPANSION_TH.md
