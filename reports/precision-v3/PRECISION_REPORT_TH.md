# ผลพัฒนาและวิเคราะห์ Football Prediction AI: Precision v3

วันที่ 26 ตุลาคม 2026 (Asia/Bangkok) · รุ่น `precision-v3-9f46ca6392a2` · สถานะ research only

## ผลที่วัดได้และขอบเขต

โมเดล 1X2 ที่คัดจาก validation ทายถูก **103/121 = 85.12%** ในช่วงทดสอบ 2025/26 โดยเลือก **3.76% ของ 3,220 แมตช์** เท่านั้น Wilson 95% CI **77.71–90.38%**, date-cluster bootstrap CI **78.06–90.80%** หมายถึงผลย้อนหลังของกลุ่มที่เลือก ไม่ใช่รับประกันว่าจะถูกในอนาคตหรือทายได้ทุกวัน

ถ้าบังคับทายทุกคู่: Accuracy **50.56%**, multiclass Log Loss **1.003452**, Brier **0.599642** ยังไม่ถึง 70–80% ไม่มีหลักฐานที่จะรับประกันความแม่นยำตามตัวเลขนั้นกับทุกเกม ผลนี้แยกจาก exact score, สูงต่ำ, BTTS และการถูกครบชุด

ช่วงทดสอบเหล่านี้เคยถูกตรวจจากงานวิจัยรุ่นก่อนแล้ว จึงเรียกว่า retrospective comparison แม้ training ของแต่ละ fold ใช้เฉพาะอดีต การเปรียบเทียบผู้ท้าชิงหลายตัวทำให้ validation มี selection bias ได้; CI ไม่ได้ปรับ multiplicity และไม่ลบอคตินั้น ต้องใช้คำทำนายที่ล็อกก่อนแข่งจริงชุดใหม่ต่อไป

**เกณฑ์ยืนยันรวมยังไม่ผ่าน**: EPL และ Serie A คัดเพียงลีกละ 8 คู่ ต่ำกว่าเกณฑ์ 20 ต่อทุกลีกที่รองรับ ไม่ตัดลีกออกหรือผ่อนเกณฑ์หลังเห็นผล `prospective_certified=false`, active model ยังเป็น null

## สิ่งที่แก้จริง

1. เพิ่มฟีเจอร์จาก 11 เป็น 58 ค่า: ฟอร์ม 5/10/20 นัด, ประตูได้เสีย, ความแข็งแกร่งคู่แข่ง, residual points เทียบ Elo ก่อนเกม, ประวัติ 365 วัน, จำนวนเกมฤดูกาล, ระยะห่างเกมลีก และตัวบ่งชี้ลีก ข้อมูลวันเดียวกันทำนายก่อนอัปเดตผลทั้งหมด
2. สร้าง Dixon–Coles ที่ประมาณ attack/defence โดยปรับตามคู่แข่งและความได้เปรียบเจ้าบ้าน ใช้น้ำหนักตามอายุเกม, shrinkage และ low-score correction เปรียบเทียบ half-life 180/365 วันตามแผนที่ล็อก ไม่สับสน expected goals จากสกอร์กับ event-based xG
3. ฝึก Logistic 11 ค่าเดิม, Logistic 58 ค่า, league-shrunk Logistic, XGBoost depth 2/3 และ ensemble Logistic/Dixon–Coles น้ำหนักคงที่ 50:50 เปรียบเทียบ raw กับ temperature calibration ที่ใช้ OOF ของฤดูกาลก่อนหน้าเท่านั้น
4. เปรียบเทียบ 22 model/calibration candidates ด้วย validation Log Loss ต่ำสุด แล้วทดสอบกติกาคัด 6 แบบบน validation ตาม protocol ที่บันทึกก่อนประเมิน ไม่เปลี่ยนกติกาจากผล test
5. สร้าง inference engine ที่ใช้ฟีเจอร์ 58 ค่าเหมือนตอนฝึก มี parity test ระดับ 1e-10, ตรวจ checksum/cutoff, probability sum, สอดคล้องของตลาดสูงต่ำ และไม่ใส่ผลเป้าหมาย 0–0 ปลอม
6. เพิ่มหน้าหลักฐานความแม่นยำ API `/api/research/precision`, snapshots แบบ immutable และผูก threshold/eligibility ของกติกาที่ validation เลือกเข้ากับหน้าสรุปคู่จำลอง
7. เตรียม enrichment contract สำหรับ injuries/lineups/xG ที่มี coverage/license/timestamp โดยไม่เรียก API-Football และไม่ถือว่าข้อมูลขาดคือไม่มีนักเตะเจ็บ

โมเดลที่เลือกคือ **`enhanced-logistic-dc-equal:raw`** ซึ่งดีที่สุดใน candidates ที่เปรียบเทียบบน validation และมี test Log Loss ต่ำสุดในชุดเปรียบเทียบครั้งนี้ด้วย Calibration แบบ raw ชนะใน 1X2 จึงไม่บังคับใช้การสอบเทียบที่ทำผลแย่ลง ส่วน BTTS เลือก previous-OOF Platt

## ข้อมูลที่นำมาใช้

หน้าต่างผลย้อนหลัง **[2021-10-25, 2026-10-25)** ใช้ accepted ledger เดิม **17,027 นัด** จาก 12 ลีก ไม่ได้เพิ่มจำนวน labels จากข่าวหรือข้อมูลนักเตะในรอบนี้ สร้าง supervised feature rows ได้ **16,528 แถว**; ที่เหลือใช้เป็นประวัติเริ่มต้นหรือยังไม่พอเงื่อนไขสร้างฟีเจอร์ ไม่ใช่ทุก accepted row ถูกใช้เป็น target ฝึกทันที

| ลีก | Accepted ledger |
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

จำนวน accepted / supervised features / quarantine แยกทุกลีกและฤดูกาลอยู่ใน [quality-and-features-by-season.csv](quality-and-features-by-season.csv)

OpenFootball commit **`e6744429ee395bc86f247348c6184bb08d4eb361`** และ frozen OpenLigaDB snapshot ยังคงเดิม Dataset SHA **`5e415c968c86eda662d30db72040e9e6680e89831104b78c1dd4e1e4535a91b1`**; merged duplicate evidence 2,885, cross-source agreement 2,705 เป็นหลักฐานประกอบ ไม่เพิ่มนับเป็นแมตช์ใหม่สองครั้ง Fjelstul cross-check แยกจาก training เพราะไม่มีวันแข่งต่อแมตช์ในตารางที่ใช้

กัก **4,363 รายการ**, excluded **902** จำนวนกักรวมรายการโปรแกรมที่ยังไม่มีสกอร์และหลักฐานแต่ละแหล่ง จึงไม่ใช่จำนวนแมตช์ที่เล่นจบผิดทั้งหมด

| เหตุผลกัก | จำนวน |
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

66 นัด EPL 2019/20 ที่วันที่ผิดลำดับยังไม่ถูกแก้เดาและไม่ถูกนำกลับเข้าฝึก อยู่ในหลักฐานกักเดิมนอกหน้าต่างห้าปีนี้ ไม่มีการเปลี่ยนข้อมูล `D:\Live score Project`

## การแบ่งเวลาและกติกา

- ใช้ 2022/23 สร้าง OOF เริ่มต้น; validation 2023/24 + 2024/25; test 2025/26; audit ต้น 2026/27 ถึงก่อน 25 ตุลาคม
- Classifier แต่ละ fold ฝึกก่อน 1 กรกฎาคมของ fold; goal model refit ทุกสองเดือนจากอดีต; ปิดการเห็นแมตช์วันเดียวกัน
- เลือก `standard_history-p75`: ความน่าจะเป็นอย่างน้อย 75%, เกมตามสนามเหย้า/เยือนอย่างน้อยฝั่งละ 8, ประวัติ 365 วันอย่างน้อย 15 และ gap เกมลีกไม่เกิน 45 วัน รวม validation sample ≥150 และ ≥50 ต่อ fold, coverage ≥3%, calibration gap ≤8 จุดเปอร์เซ็นต์
- แต่ละลีกที่รองรับต้องมี predicted selections ใน validation ≥20; ไม่ใช้ผล target เลือกชื่อลีก
- Tier target80 ต้อง accuracy validation ≥80% และ lower bounds ≥70%; test ยืนยันขั้นต่ำ 100 รวม, 20 ต่อทุกลีกที่รองรับ, coverage ≥3%, point ≥80%, lower bounds ≥70%
- Validation ที่เลือกถูก **233/283 = 82.33%**

## ผล 1X2 รายลีกเฉพาะคู่ที่เลือก

| ลีก | คัด | ถูก | Accuracy | Wilson 95% CI |
|---|---:|---:|---:|---|
| Bundesliga | 20 | 16 | 80.00% | 58.40–91.93% |
| 2. Bundesliga | 0 | 0 | — | — |
| Premier League | 8 | 7 | 87.50% | 52.91–97.76% |
| Championship | 0 | 0 | — | — |
| La Liga | 20 | 19 | 95.00% | 76.39–99.11% |
| Ligue 1 | 0 | 0 | — | — |
| Serie A | 8 | 6 | 75.00% | 40.93–92.85% |
| Eredivisie | 20 | 18 | 90.00% | 69.90–97.21% |
| Primeira Liga | 45 | 37 | 82.22% | 68.67–90.71% |

ลีกที่ไม่มีคู่เลือกต้องไม่รายงานเป็น accuracy 0% หรือ 100%; ลีกที่ไม่มีข้อมูล test เลยก็ไม่รับรองจาก training ของลีกอื่น

## เปรียบเทียบโมเดลทุกตัวบน test เดียวกัน

| Model/calibration | Log Loss ↓ | Brier ↓ | Accuracy ทุกคู่ |
|---|---:|---:|---:|
| enhanced-logistic-dc-equal:raw | 1.003452 | 0.599642 | 50.56% |
| enhanced-logistic-dc-equal:previous-oof-temperature | 1.004267 | 0.600182 | 50.56% |
| enhanced-xgb-d2:raw | 1.005000 | 0.601019 | 49.97% |
| enhanced-xgb-d2:previous-oof-temperature | 1.005021 | 0.601025 | 49.97% |
| dc365-r4:raw | 1.005481 | 0.601202 | 49.84% |
| dc365-r4:previous-oof-temperature | 1.005594 | 0.601252 | 49.84% |
| enhanced-xgb-d3:raw | 1.005707 | 0.601410 | 50.00% |
| enhanced-xgb-d3:previous-oof-temperature | 1.005866 | 0.601469 | 50.00% |
| legacy-logistic:previous-oof-temperature | 1.007626 | 0.602869 | 49.38% |
| enhanced-logistic:raw | 1.007705 | 0.602063 | 50.22% |
| dc180-r4:raw | 1.007956 | 0.602765 | 49.88% |
| dc180-r4:previous-oof-temperature | 1.008079 | 0.602839 | 49.88% |
| legacy-logistic:raw | 1.008672 | 0.603536 | 49.38% |
| legacy-elo:previous-oof-temperature | 1.016822 | 0.607754 | 50.03% |
| legacy-elo:raw | 1.017947 | 0.608845 | 50.03% |
| enhanced-logistic:previous-oof-temperature | 1.020056 | 0.611316 | 50.22% |
| legacy-poisson:raw | 1.021465 | 0.612062 | 48.82% |
| legacy-poisson:previous-oof-temperature | 1.021504 | 0.612085 | 48.82% |
| league-shrunk-logistic:raw | 1.025862 | 0.613395 | 48.63% |
| league-shrunk-logistic:previous-oof-temperature | 1.028256 | 0.617304 | 48.63% |
| league-prior:previous-oof-temperature | 1.076485 | 0.651359 | 43.60% |
| league-prior:raw | 1.076772 | 0.651483 | 43.60% |

เทียบ Logistic เดิม: Log Loss 1.008672 → 1.003452, Brier 0.603536 → 0.599642, Accuracy 49.38% → 50.56% เป็นการดีขึ้นของค่าประเมินจุดเดียว ยังไม่ได้ทดสอบ paired significance ของความต่างจึงไม่เรียกว่าชนะอย่างมีนัยสำคัญทุกกรณี ต้นฤดู 2026/27 โมเดลที่เลือกไม่ได้มี all-match Log Loss ต่ำสุดในบรรดา controls จึงไม่มีหลักฐานว่าชนะทุกช่วง

## ตลาดประตู

| ตลาด | LL โมเดล ↓ | LL baseline ลีก ↓ | Binary accuracy | โมเดล |
|---|---:|---:|---:|---|
| over_1.5 | 0.523703 | 0.528097 | 77.70% | dc365-r4-w50:raw |
| over_2.5 | 0.681877 | 0.686789 | 56.40% | dc365-r4-w50:raw |
| over_3.5 | 0.599202 | 0.604197 | 70.47% | dc365-r4-w50:raw |
| btts_yes | 0.683448 | 0.684669 | 56.34% | dc365-r4-w75:previous-oof-platt |

Binary accuracy ใช้ทั้งคำทำนายว่าเกิด/ไม่เกิดที่ threshold 0.5 ไม่ใช่อัตราแทงสูงอย่างเดียว เช่น over_3.5 ส่วนใหญ่ทายไม่ถึงสี่ลูกได้ง่ายกว่า จึงห้ามนำ 70.47% ของตลาดนั้นมาอ้างแทนความแม่นยำผู้ชนะ สูง 2.5 ยังประมาณ 56.40% ไม่มีการแต่งให้ถึง 70%

## คู่ผิดและความพอเพียงของรายวัน

คัด 121 คู่ เป็นเหย้าชนะ 101 และเยือนชนะ 20 คู่ ไม่มีเสมอในกลุ่มที่เลือก คู่ผิด 18 เป็นผลเสมอ 14, ทีมเยือนชนะ 2, เจ้าบ้านชนะ 2 เก็บทุกแถวไว้ใน `error-and-capacity-analysis.json` ไม่รู้เหตุการณ์ใบแดง/บาดเจ็บของแมตช์เหล่านี้จึงไม่อ้างว่าเป็นสาเหตุ และไม่เพิ่มตัวกรองใหม่จากความผิดเหล่านี้บน test เดิม

มีคู่ผ่านใน 80 วันปฏิทิน มี ≥3 คู่ 8 วัน และ ≥5 คู่ 1 วัน เฉลี่ย 0.33 คู่/วันตลอดปี แสดงว่ากติกาเข้มนี้ไม่รองรับชุด 3–5 คู่ทุกวัน ห้ามเติมคู่ด้อยคุณภาพให้ครบ

ข้อมูลนี้นับตามวันในแหล่งย้อนหลังซึ่ง kickoff ยังไม่ยืนยันทั้งหมด จึงเป็น capacity diagnostic ไม่ใช่ผล backtest รอบ 06:00–06:00 กรุงเทพที่ยืนยันแล้ว หน้าระบบใช้รอบนั้นจริงกับ fixtures ที่มี UTC และบังคับไม่ซ้ำทีม/คู่ ชุดคูณโอกาสยังสมมติอิสระ: ถ้าแต่ละคู่ถูก 80%, ถูกครบ 3 คู่เพียง 51.2% และครบ 5 คู่ 32.768% ภายใต้สมมติฐานนั้น ต้องวัดผลครบชุดจริงภายหลัง

## การตรวจเพิ่มและหลักฐานอนาคต

ต้นฤดู 2026/27 มีทั้งหมด 556 คู่ คัด 13 ถูก 11 = 84.62%, Wilson CI 57.77–95.67% ตัวอย่างยังน้อยมากและไม่ผ่านเกณฑ์

ได้เรียก public OpenLigaDB 2 requests และบันทึกโปรแกรมจริงก่อนเตะ 16 คู่ใน private research ledger (ไม่รวมเป็น training/test accuracy) กักจาก unresolved mapping 2 คู่ จาก 16 ที่บันทึกไม่มีคู่ผ่านตัวกรอง: ทุกคู่ต่ำกว่า probability threshold, บางคู่ประวัติไม่พอหรืออยู่ลีกที่ validation ไม่รองรับ ไม่มีการแนะนำคู่จากชุดนี้ ผลจริงยังไม่มี, source/mapping ยัง unverified, certified accuracy = null API-Football calls = 0

## ข้อมูลที่ขาดและลำดับพัฒนาต่อ

1. **ผลล่าสุดและโปรแกรม/เวลาเตะที่ตรวจแล้ว**: ให้ fixture identity, season, status, postponement และข้อมูลทีมตรงกันก่อนส่งคำทำนายจริง แยก source first_seen_at/available_at จาก date แข่ง ไม่ตีความวันแข่งเก่าว่า provider รู้ผล ณ ตอนนั้นแน่นอน
2. **Lineups / unavailable players / minutes และความสำคัญนักเตะ**: ต้องรู้ก่อนจุดล็อกคำทำนายและมี coverage ต่อคู่ ไม่ใช้จำนวนคนเจ็บล้วนโดยไม่พิจารณานาที/บทบาท ข้อมูลขาดคือ unknown
3. **สถิติโอกาสยิง / xG ของแมตช์ก่อนหน้า**: ช่วยแยกคุณภาพการเล่นจากสกอร์ แต่ต้องได้สิทธิใช้และข้อมูลต่อเนื่องในลีกเป้าหมาย ห้ามใช้ xG ของ target match หรือ payload ที่มาเกินเวลาทำนาย
4. **เวลาพักและภาระเกมทุกถ้วย, การเปลี่ยนโค้ช/ย้ายทีม**: gap ปัจจุบันเป็นเกมลีกในข้อมูลที่มี ไม่ใช่วันพักจริงทุกการแข่งขัน ต้องเติมจาก fixtures ทุกถ้วยที่ตรวจแล้ว
5. **อัตราต่อรองเป็น benchmark เสริมเมื่อมีสิทธิและเวลาบันทึก**: ยังไม่มีเข้าโมเดล ไม่มีการอ้างกำไรจาก accuracy เพราะไม่ทราบราคาและต้นทุน
6. **หลักฐานอนาคตและ drift**: ล็อก model/policy ก่อนแข่ง, เก็บทุกคู่ที่รับ/ปฏิเสธ, ตรวจ settlement, calibration และ coverage แยกลีก/ตลาด ห้ามคัดเลือกเฉพาะคู่ชนะเข้ารายงาน

[คู่มือ API-Football ทางการ](https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide) อธิบาย coverage ตามลีก/ฤดูกาลและ endpoints แต่ยังไม่ได้ตรวจสิทธิของบัญชีผู้ใช้ จึงไม่รับรองฟรีแพลนว่ามี injuries/lineups/xG ทุกคู่ ก่อนทดสอบจริงต้องแจ้ง coverage, season availability, rate limit และ request budget จากจำนวน pages/unique fixtures/retries ที่คำนวณแล้ว เก็บ API key เป็น secret และยังไม่เรียกจริงในรอบนี้

[Hudl/StatsBomb Open Data](https://github.com/hudl/open-data) มี event data บางการแข่งขัน แต่ตรวจ [LICENSE.pdf](https://github.com/hudl/open-data/blob/master/LICENSE.pdf) ฉบับ 8 กันยายน 2023 แล้วพบข้อจำกัดเกี่ยวกับการเผยแพร่/การใช้เชิงพาณิชย์และเงื่อนไขการเข้าถึง จึงยังไม่รวม event data เข้าระบบ ไม่ส่งชื่อหรืออีเมลสมัคร และไม่ตีความคำว่า open ว่าเผยแพร่แอปได้ทุกกรณี [ClubElo API](http://clubelo.com/API) ตอบ 403 ขณะตรวจจึงยังไม่นำเข้า ไม่มีการเลี่ยงข้อจำกัดของ Football-Data.co.uk ผ่าน mirror

หลักการสอบเทียบและแยกข้อมูลอ้างอิงจาก [เอกสาร calibration](https://scikit-learn.org/stable/modules/calibration.html) และ [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html); ใช้ custom NumPy/SciPy ในโปรเจกต์ ไม่ได้ติดตั้ง sklearn ที่ถูก Windows block แนวคิด low-score Dixon–Coles อ้างอิง [งานวิจัยการขยายโมเดล](https://arxiv.org/abs/2307.02139) และ selective prediction ใช้แนวคิด risk/coverage จาก [งานวิจัย](https://arxiv.org/abs/1705.08500) ซึ่งไม่ได้เป็นหลักฐานรับประกันฟุตบอล

## ไฟล์และการตรวจงาน

- `ml/config/precision_v3.json`: เกณฑ์ล่วงหน้าและการแบ่งเวลา
- `ml/precision/{goals,features,calibration,selection,experiment}.py`: ฝึก/คัด/ประเมินจริง
- `ml/precision_predict.py`, `ml/enrichment.py`, `ml/precision_shadow.py`: inference, ข้อมูลเสริม, private collection
- `ml/tests/test_precision.py`, `test_precision_shadow.py`: leakage, reproducibility, probability, missing values, immutable records
- `apps/web/src/PrecisionPanel.tsx`, `App.tsx`, `MatchDetail.tsx`, `MatchCentre.tsx`: หน้าหลักฐานและการแสดงโมเดล
- `apps/api/analysis.ts`, `index.ts`, `packages/football/{types,selection}.ts`: API/chunked evidence/กติกาแต่ละ snapshot
- `scripts/{prepare_precision,precision_diagnostics,verify_precision,package_precision}.py`, `prepare_centre.py`, `seed_recent.mjs`: เตรียมข้อมูลและแพ็กถาวร
- `tests/precision.test.ts`, `tests/ui/precision.spec.ts`, `tests/helpers.ts`: local D1/domain/UI integration
- `db/seed-precision.sql`, `package.json`, `.github/workflows/{ci,precision-research}.yml`, README และคู่มือปฏิบัติการ

ผลทดสอบล่าสุดดู [verification.json](verification.json); หลักฐานฝึกซ้ำ [reproducibility.json](reproducibility.json); แพ็กและ checksum [package.json](package.json) มี model artifact, feature schema, dataset version/cutoff, source SHA, metrics, configuration, code และ runtime ไม่อาศัย Actions artifact ที่หมดอายุเป็นแหล่งถาวรเพียงแห่งเดียว ยังไม่ได้อัปโหลด GitHub Release หรือรัน Actions จริง

ภาพหน้าจอ [desktop](precision-desktop.png) / [mobile](precision-mobile.png) และ [คู่มือรัน/เชื่อมระบบ](../../docs/PRECISION_V3_OPERATIONS_TH.md)

ยังไม่สำเร็จ: ความแม่นยำ 70–80% ทุกคู่/ทุกวัน, การยืนยันอนาคตและรายลีกครบเกณฑ์, enrichment ที่มีสิทธิพร้อมใช้งาน, live API account checks, settlement ของ private prospective collector, production deployment ไม่มีการเรียกใช้บริการเสียเงินหรือแก้โปรเจกต์เดิม
