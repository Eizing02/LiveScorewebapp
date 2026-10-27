# หลักฐานการพัฒนา — 25 ตุลาคม 2026

สร้างโปรเจกต์ใหม่ที่ D:/Football Prediction AI โดยไม่แก้โค้ดหรือเชื่อมฐานข้อมูลของ D:/Live score Project

## งานที่ทำสำเร็จจริง

- Historical importer pin source commit, ตรวจ working tree, score normalizer สองรูปแบบ, explicit aliases, league mapping, dedup/conflict handling, status/date/time validation, quarantine และ accepted dataset
- League prior, Elo/home advantage/cold start, Poisson/shrinkage/scoreline probabilities และ feature replay แบบวันเดียวกันไม่ใช้ผลข้ามกัน
- Logistic Regression จริงผ่าน NumPy/SciPy และ XGBoost native CPU, expanding walk-forward validation สอง fold, final holdout ที่ไม่ใช้เลือกโมเดล
- JSON Model Registry พร้อม code/runtime/dataset/config provenance, checksums, immutable versions, local packaging และ manual promotion/rollback
- React ภาษาไทยพร้อม league filter, match details, probability/scorelines, quality และ performance จริง
- Worker/D1 local migrations, mock API client, quota/cache, signed internal endpoints, idempotent jobs, immutable prediction/feature snapshots และ result evaluation
- CI/training/offline-batch/manual-release workflows เตรียมแล้ว; ยังไม่ได้ push หรือรันบน GitHub

## ข้อมูลที่รับและกัก

อ่าน 97,082 แถว: รับ 15,905, กัก 7,082, ไม่นำเข้าใน scope 74,095

Accepted หมายถึงรับสำหรับทดลองแบบใช้ประวัติก่อนวันแข่ง ยังติด unverified สำหรับ source dates/timezones และ cross-provider identity ไม่ใช่ยืนยันว่าข้อมูลทุกนัดถูกต้องจากผู้จัดการแข่งขัน

| ลีก | รับสำหรับฝึก |
|---|---:|
| en.1 | 5,700 |
| es.1 | 5,310 |
| de.1 | 4,895 |

| ฤดูกาล | EPL | La Liga | Bundesliga |
|---|---:|---:|---:|
| 2010-11 | 380 | ไม่มีไฟล์ | 306 |
| 2011-12 | 380 | ไม่มีไฟล์ | 306 |
| 2012-13 | 380 | 380 | 306 |
| 2013-14 | 380 | 380 | 306 |
| 2014-15 | 380 | 380 | 306 |
| 2015-16 | 380 | 380 | 306 |
| 2016-17 | 380 | 380 | 306 |
| 2017-18 | 380 | 380 | 306 |
| 2018-19 | 380 | 380 | 306 |
| 2019-20 | 0 | 380 | 306 |
| 2020-21 | 380 | 380 | 306 |
| 2021-22 | 380 | 380 | 306 |
| 2022-23 | 380 | 380 | 306 |
| 2023-24 | 380 | 380 | 306 |
| 2024-25 | 380 | 370 | 305 |
| 2025-26 | 380 | 380 | 306 |
| 2026-27 | 0 | 0 | 0 |

| เหตุผลที่กัก (ทั้ง repository) | จำนวน |
|---|---:|
| epl_2019_20_misdated_66 | 66 |
| unresolved_team | 1 |
| duplicate_merged | 12 |
| status_awarded | 52 |
| status_cancelled | 585 |
| season_chronology_hold | 314 |
| missing_score | 5,875 |
| status_postponed | 21 |
| status_abandoned | 1 |
| incomplete_season | 155 |

66 นัดที่ผิดลำดับยังไม่ถูกแก้วันที่ อีก 314 นัดของฤดูกาลเดียวกันพักไว้ด้วย รวม EPL 2019/20 ทั้ง 380 นัด ไม่มีการเติม missing score เป็น 0–0 ข้อมูลนอก 3 ลีกที่มีผลใช้ได้ 73,214 แถวและ full enrichment 881 แถวถูกแยกเป็น excluded; ไม่ควรนับ excluded ทั้งหมดเป็นข้อมูลเสีย

## ผลโมเดลที่รันจริง

Validation: 2022/23 และ 2023/24, final holdout: 2024-07-01 ถึงก่อน 2025-07-01 รวม 1,055 นัด เกณฑ์ถูกกำหนดไว้ใน policy.json ก่อนรันประเมิน

| โมเดล | Log Loss ↓ | Brier ↓ | Accuracy | ECE ↓ |
|---|---:|---:|---:|---:|
| league | 1.0810 | 0.6549 | 41.52% | 0.0223 |
| elo | 1.0071 | 0.6013 | 52.32% | 0.0337 |
| poisson | 1.0058 | 0.6002 | 50.90% | 0.0185 |
| logistic | 0.9973 | 0.5951 | 52.23% | 0.0320 |
| xgboost | 1.0042 | 0.6005 | 52.32% | 0.0287 |

เลือก **logistic** จาก validation; baseline ที่ดีที่สุดบน validation คือ elo Challenger ผ่านเกณฑ์ทั้งสามลีกและทั้งสอง fold ก่อนดู holdout ผล holdout มี Log Loss ต่ำสุดในตัวเลขที่วัด แต่ไม่ได้กล่าวว่าชนะทุกโมเดลอย่างมีนัยสำคัญใน holdout

Accuracy 95% CI แบบ date-cluster bootstrap: 48.97%–55.23% (500 รอบ) ความสัมพันธ์ระหว่างทีม/ฤดูกาลและปัญหาข้อมูลยังอาจทำให้ช่วงนี้มองโลกดีเกินจริง

| ลีก · โมเดลที่เลือก | n | Log Loss | Brier | Accuracy |
|---|---:|---:|---:|---:|
| en.1 | 380 | 0.9894 | 0.5913 | 52.63% |
| es.1 | 370 | 0.9819 | 0.5835 | 54.05% |
| de.1 | 305 | 1.0258 | 0.6141 | 49.51% |

La Liga holdout มีผลขาด 10 นัด และ Bundesliga มี awarded ที่ไม่นำเข้า 1 นัด ทั้งห้าโมเดลประเมินบนตัวอย่างเดียวกัน การเลือกชุดข้อมูลอาจทำให้ผลมี bias

## Registry และ reproducibility

- Candidate ล่าสุด: `v1-c991e0a91b8f`
- Dataset SHA-256: `830c9f5aa1230b5a7ff9ba037e69c82d0fe02d0b0cfd77135854ca873a0ff200`
- Source commit: `e6744429ee395bc86f247348c6184bb08d4eb361`
- Frozen policy SHA-256: `ffcfe1dd520a3f72a985b5c3e394e52ee3fb6f5d6a42438785a46f48247b7932`
- Active model: `None`; MODEL_AUTO_PROMOTE=false
- ตรวจ checksum และ training code provenance ผ่าน; เก็บ ZIP พร้อม SHA-256 ใน reports แล้ว ยังไม่อัปโหลด
- Importer รันซ้ำให้ dataset hash เดิม; challenger training ซ้ำใน tests ให้ probabilities เหมือนเดิม; evaluation ที่รันซ้ำระหว่างตรวจ artifact metadata ให้ metrics เท่าเดิม โดยไม่เปลี่ยนเกณฑ์หรือ hyperparameters
- Deployment artifact refit ถึงก่อน 2026-07-01; metrics มาจาก estimator ตามแต่ละ fold ไม่ใช่นำ deployment refit มาวัดบนข้อมูลที่เคยฝึก

## ผลตรวจที่รันจริง

| คำสั่ง | ผล |
|---|---|
| python -m pytest -q | 23 passed; หลังปรับ rollback test รันซ้ำเฉพาะ registry อีก 2 passed |
| python -m ruff check ml scripts | ผ่าน |
| npm test | 13 passed รวม D1 concurrency/cache/auth/replay/locking/feature history |
| npm run lint | ผ่าน |
| npm run typecheck / npm run build | ผ่าน |
| npm run worker:check | dry-run bundle ผ่าน ไม่มี deployment |
| npm run db:migrate:local | migrations 0001 และ 0002 ผ่านบน local D1 |
| npm run db:seed:local | ผ่าน, 3 mock fixtures และผล holdout จริง |
| npm run test:ui | 1 passed, desktop/mobile/filters/details/performance/quality, ไม่มี browser runtime error |
| npm audit --audit-level=moderate | 0 vulnerabilities |
| python -m pip check | ผ่าน |
| Client bundle credential identifier scan | ผ่าน ไม่พบตัวระบุ secret ฝั่ง server ใน JS client |
| Offline batch / model checksum / local ZIP packaging | ผ่าน |

ภาพตรวจอยู่ใน reports/dashboard-desktop.png, dashboard-mobile.png, performance-desktop.png, calibration.png

Application Control บล็อก DLL ของ scikit-learn จึงใช้ NumPy/SciPy และ XGBoost native API ที่โหลดได้ โดยไม่เปลี่ยนนโยบายความปลอดภัย Wrangler รุ่นแรกเริ่ม local runtime ไม่ได้; pin คู่ stable ที่ทดสอบแล้วแทน ดู ADR

## ส่วนที่ยังไม่สำเร็จและยังไม่เปิดใช้งาน

- API-Football จริง: **0 requests**; ยังไม่ตรวจบัญชี season permission, coverage, reset headers, minute limit, pagination และ Terms จริง
- Cloudflare/GitHub cloud: ยังไม่สร้าง resources, secrets, production DB หรือ deployment; CI/workflows ยังไม่ได้รันบน GitHub
- Live provider identity mapping และ live feature rebuilding ยังต้องตรวจ/ต่อผ่านข้อมูลจริง; ตอนนี้ feature builder/batch ใช้ข้อมูล historical ที่ยืนยัน provenance ได้และ mock fixtures
- Current fixture schedule เป็น mock, historical features เก่า; ห้ามใช้สาธิตนี้อ้างเป็นคำทำนายเกมจริงปัจจุบัน
- Public UI เป็น initial dashboard ยังไม่ใช่ระบบ admin ครบทุกหน้า, exact T-24h/T-6h/T-1h scheduling หรือ live-score service
- Live sync เริ่มแค่หนึ่งลีก/หนึ่ง page; paging continuation, automatic season rollover, result-correction evaluation revisions, admin rate limits, nonce/ledger retention และ deployed CPU/free-tier measurement เป็นงานก่อนเปิดจริง
- ไม่ตั้ง billing limits แทนผู้ใช้ และไม่รับประกันค่าใช้จ่ายจากโค้ดเพียงอย่างเดียว

## ขั้นต่อไปสำหรับ integration

1. ตรวจบัญชี API-Football direct/RapidAPI และ free-season availability โดยผู้ใช้ตั้ง key เป็น secret เอง
2. ขออนุมัติ integration test หนึ่งลีกหนึ่งหน้า: คาด 1 billable fixtures request; status แยกตรวจว่า exempt จริงก่อนใช้
3. ตรวจข้อมูล provider/team crosswalk, dates/status/pagination/headers แล้วต่อ current feature updates พร้อม parity tests
4. ตั้ง Cloudflare Free/D1/secrets/limits และ GitHub private repo/workflow permissions ด้วยการอนุมัติแยก; เริ่ม preview mock ก่อน
5. วัด Worker CPU, DB writes/reads/storage, failure recovery, rollback และ fresh predictions ก่อน production/scheduler

ไฟล์ที่สร้างทั้งหมดดู reports/created-files.json; รายละเอียดจำนวนทุกลีก/ฤดูกาลดู reports/quality-by-season.csv; คำสั่งรันและ architecture อยู่ README.md, docs/ADR-0001.md และ docs/OPERATIONS.md


## เพิ่มเติม — การคัดกรองอย่างละเอียด

สร้างตัวทดลอง selective-research-v1 แยกจาก frozen baseline และ Model Registry เลือกจาก 12 กติกาบน validation ก่อนทดสอบ 2025/26 โดย estimator ฝึกจากข้อมูลก่อนช่วง test นี้เท่านั้น

กติกาที่เลือก: probability-p70; เลือก 67/1066 คู่ ถูก 57 คู่ (85.07%) แต่ confirmation_passed=false เพราะจำนวนตัวอย่างรวมและ EPL ไม่ถึงเกณฑ์

เพิ่มหน้าเว็บ “การคัดกรอง”, read-only /api/filtering และ /api/filtering/matches, migration 0003 และ seed หลักฐานรายคู่ 1,066 แถวแบบ immutable พร้อม pagination, league/status filters, เหตุผล/คำเตือนและ probability ก่อน-หลัง calibration

ผลตรวจล่าสุด: Python 29 passed, TypeScript/D1 17 passed, UI desktop/mobile 2 passed, lint/typecheck/build และ Worker dry-run ผ่าน; migrations/seed ทั้งหมดเป็น local เท่านั้น

ดู docs/DETAILED_FILTERING_TH.md และ reports/selection-v1/ สำหรับผล รายงานและภาพหน้าจอ ยังไม่เรียก API-Football จริง ไม่ deploy และไม่ promote โมเดล
