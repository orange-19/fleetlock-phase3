# FleetLock — AI-Powered Parametric Income Insurance for India's Gig Economy

**Guidewire DEVTrails 2026 | University Hackathon**
**Team: LeadToWin — Department of Computer Science and Engineering**

> FleetLock delivers automated, verifiable, fraud-resistant income protection to India's 12 million platform-based delivery workers — without paper forms, without adjusters, and without waiting weeks for a claim decision.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Who We Are Building For](#2-who-we-are-building-for)
3. [What Changed from v2 to v3](#3-what-changed-from-v2-to-v3)
4. [Our Approach — Earnings Floor Protection](#4-our-approach--earnings-floor-protection)
5. [Payout Formula — Explained](#5-payout-formula--explained)
6. [System Architecture — v3 Layered Design](#6-system-architecture--v3-layered-design)
7. [Machine Learning Architecture](#7-machine-learning-architecture)
8. [Parametric Triggers — Fully Automated](#8-parametric-triggers--fully-automated)
9. [Fraud Detection and Anti-Spoofing Strategy](#9-fraud-detection-and-anti-spoofing-strategy)
10. [Insurance Plans and Weekly Premium Model](#10-insurance-plans-and-weekly-premium-model)
11. [Coverage Exclusions — What Is Not Covered and Why](#11-coverage-exclusions--what-is-not-covered-and-why)
12. [External API Integrations](#12-external-api-integrations)
13. [Disruption Simulator — Stress Testing the Network](#13-disruption-simulator--stress-testing-the-network)
14. [Technology Stack](#14-technology-stack)
15. [Project Structure](#15-project-structure)
16. [Getting Started](#16-getting-started)
17. [Team](#17-team)

---

## 1. Problem Statement

India has over 12 million platform-based delivery workers. They operate on Zomato, Swiggy, Amazon, Zepto, Blinkit, and similar platforms — earning between Rs. 300 and Rs. 800 per day with no employer benefits, no savings buffer, and no safety net.

When an external disruption occurs — a monsoon that shuts down deliveries, a local curfew that blocks access to pickup points, or a platform outage that kills order flow — these workers bear the full financial loss. Traditional insurance is built for salaried employees: monthly premiums, paper-based claim filing, adjuster review cycles measured in weeks. It does not serve the gig worker's reality in any meaningful way.

FleetLock solves this with parametric income insurance. Payouts are not triggered by "proving a loss" after the fact. They are triggered by objective, verifiable external data — and disbursed automatically within hours of a confirmed disruption, directly to the worker's UPI account.

---

## 2. Who We Are Building For

**Primary Persona: Ravi Kumar**

| Field | Details |
|---|---|
| Age | 26 |
| Role | Full-time food delivery partner — Zomato and Swiggy |
| City | Tier-1 Indian city: Chennai, Mumbai, Bengaluru, or Hyderabad |
| Daily Income | Rs. 600 to Rs. 1,000 |
| Weekly Income | Rs. 4,000 to Rs. 7,000 |
| Device | Android smartphone — UPI, WhatsApp, delivery apps |
| Financial Reality | Week-to-week income. No savings. Daily bike EMI. No employer benefits. |

One missed day due to a heavy monsoon equals Rs. 600 to Rs. 1,000 gone with no recourse. The disruption is not his fault, but he bears the entire cost. FleetLock exists to change that.

---

## 3. What Changed from v2 to v3

Version 2 established the product logic, ML architecture, and claim pipeline. A structured gap analysis identified 12 critical and high-severity gaps that prevented the platform from being operationally complete. Version 3 closes all of them.

### Critical Gaps Resolved

**Gap 01 — Parametric Auto-Trigger (was: manual admin button)**
The single biggest architectural gap in v2. Disruptions were triggered manually by an administrator clicking a button in the UI. In v3, a dedicated Scheduler Module runs a Celery Beat job every 5 minutes. It polls OpenWeatherMap and Tomorrow.io, evaluates real live readings against `PARAMETRIC_THRESHOLDS`, and auto-initiates claims for all active subscribers in the affected zone with no human involvement.

**Gap 02 — Real Weather API (was: manually entered form data)**
Weather inputs were typed by hand. In v3, `integrations/weather_client.py` pulls live `rainfall_mm`, `wind_speed_kmh`, `temperature_celsius`, and `aqi_index` from OpenWeatherMap every 5 minutes. Tomorrow.io serves as a secondary source for hyperlocal, street-level flood alerts. The DisruptionSeverityModel now operates entirely on live API data.

**Gap 03 — Real GPS and Telematics (was: Gaussian noise generator)**
Fraud features like `route_deviation_pct` and `gps_drift_meters` were synthetically generated using Gaussian random noise — meaning the fraud model was not detecting real spoofing, only simulated spoofing. In v3, `integrations/telematics_client.py` calls the Google Maps Routes API to compute actual route deviation by comparing the worker's submitted GPS trace against the expected delivery route. The fraud model now operates on real telematics signals.

**Gap 04 — Payment Disbursement (was: DB record only)**
Approved payouts in v2 were written to the database and displayed on the worker's dashboard, but no actual money moved. In v3, `services/payout_service.py` calls the Razorpay Payouts API to initiate a real UPI or NEFT transfer directly to the worker's registered account, in paise, with a transaction reference ID logged against the claim.

**Gap 05 — SQLite → PostgreSQL**
SQLite cannot handle concurrent writes. During a mass claim event — 500 workers in a zone all triggering simultaneously — v2 would serialise every write, causing severe latency and potential data corruption. v3 runs PostgreSQL 15 with a connection pool. Alembic manages schema migrations.

**Gap 06 — Real-Time Notifications (was: UI polling)**
Workers had to manually refresh the page to see claim updates. v3 adds WebSocket push via Socket.IO for in-app real-time updates, and integrates Twilio for SMS and WhatsApp delivery of claim state transitions: created, approved, and payment confirmed.

**Gap 08 — Async ML Inference (was: synchronous in HTTP cycle)**
In v2, the full ML pipeline — fraud scoring, payout auditing, severity classification — ran synchronously inside the HTTP request. Under load, this caused the API to block for several seconds per claim. In v3, all ML inference is offloaded to Celery workers. The API returns a `job_id` immediately. The result is pushed to the client via WebSocket when processing completes.

**Gap 09 — Regulatory Compliance / KYC (was: none)**
v2 had no identity verification, no consent logging, and no IRDAI-compliant audit trail. v3 integrates the Setu / DigiLocker API for Aadhaar OKYC and PAN verification during worker registration. Consent timestamps and IP addresses are stored in a write-once audit log table, making the platform defensible for IRDAI grievance handling and insurance product filings.

**Gap 11 — Platform Earnings Integration (was: Gaussian simulation)**
Worker earnings were generated from a 60-day Gaussian distribution seeded at startup. The baseline that every claim is measured against was fictional. v3 connects to partner APIs from Swiggy, Zomato, and Blinkit to pull verified earnings data directly. For the hackathon phase, a verified-screenshot upload flow is implemented as an interim path before B2B partner agreements are formalised.

### Additional Improvements in v3

- API Gateway layer (Kong / Traefik) with rate limiting, RBAC, and JWT RS256 validation added as Layer 1.5 between the frontend and backend
- Structured JSON logging via Loguru feeding a Grafana + Loki observability stack
- Sentry integration for exception tracking in ML inference and payment flows
- SHAP explainability endpoint at `GET /admin/claim/{id}/explain` for auditable model decisions
- Automated monthly ML model retraining pipeline via Celery, with experiment versioning tracked in MLflow
- Insurance policy PDF generation per subscription via ReportLab
- S3-compatible object storage (MinIO) for ML model artifacts, claim evidence photos, and audit logs

---

## 4. Our Approach — Earnings Floor Protection

Most parametric platforms take a simplistic approach:

```
CONVENTIONAL APPROACH:
If heavy rain detected in zone → Pay fixed Rs. 200
```

This is easy to build and easy to exploit. FleetLock does something fundamentally different:

```
FLEETLOCK APPROACH:
If worker's verified platform earnings drop 70% below their personal
30-day baseline for 30 or more continuous minutes
→ Cross-validate the disruption across multiple independent data signals
→ Compute the actual income loss — not a flat rate
→ Disburse to the worker's UPI account within 4 hours
```

The key insight is that verified platform earnings cannot be faked. A GPS coordinate can be spoofed from a home in Koramangala while a fraudster claims to be stranded in Andheri. But if Swiggy's own database shows that worker earned Rs. 350 during that window, the earnings data immediately contradicts the claimed loss — and the claim is rejected automatically before any human is involved.

---

## 5. Payout Formula — Explained

Every approved payout in FleetLock is computed deterministically. There is no discretion, no manual negotiation, and no ambiguity. The formula is disclosed to the policyholder with every payout notification.

### Core Payout Formula

```
Payout = Base Daily Income x Coverage Rate x Severity Multiplier x Loyalty Bonus
```

**Base Daily Income**
The trimmed mean of the worker's verified platform earnings over the preceding 60 days. The top 5% and bottom 5% of daily earnings are excluded before computing the mean. This eliminates the distortion of exceptional high-earning days and outlier low-earning days, producing a stable and representative baseline for each individual worker.

Example: If Ravi earned between Rs. 400 and Rs. 950 over 60 days, the trimmed mean might settle at Rs. 720 — his true representative daily income.

**Coverage Rate**

| Plan | Coverage Rate |
|---|---|
| Sahara (Level 1) | 40% of Base Daily Income |
| Kavach / Standard (Level 2) | 60% of Base Daily Income |
| Suraksha (Level 3) | 80% of Base Daily Income |

**Severity Multiplier**

| Severity Classification | Multiplier |
|---|---|
| Low | 0.75x |
| Medium | 1.00x |
| High | 1.25x |

Severity is determined from live external API data — rainfall intensity from OpenWeatherMap / IMD, AQI levels from CPCB, government notification status, or platform outage duration — not from the worker's self-report.

**Loyalty Bonus**
A multiplier between 1.00 and 1.15, applied on top of the base payout for workers with strong platform engagement.

| Input | Weight |
|---|---|
| Consecutive active days on platform | 40% |
| Policy renewal streak | 30% |
| Claim accuracy rate (legitimate claims vs. rejected) | 20% |
| Platform performance rating | 10% |

**Worked Example:**

Ravi holds a Kavach plan. A verified heavy monsoon event in his zone qualifies as High severity.

```
Base Daily Income   = Rs. 720 (60-day trimmed mean)
Coverage Rate       = 0.60 (Kavach plan)
Severity Multiplier = 1.25 (High)
Loyalty Bonus       = 1.10 (strong renewal streak)

Payout = 720 x 0.60 x 1.25 x 1.10
Payout = Rs. 594
```

This amount is disbursed directly to his UPI account via Razorpay Payouts API.

### Payout Categories and Their Computation Logic

| Disruption Category | Payout Logic |
|---|---|
| Environmental (rain, heat, flood, AQI) | 5% of previous day's earnings per blocked hour |
| Social (curfew, bandh, strike) | 2% of each cancelled order's value |
| Platform outage | 1% of previous day's earnings per confirmed outage hour |

All amounts are capped by the maximum covered days defined in the active policy window (3, 5, or 7 days depending on plan), and by the per-day payout ceiling for that plan.

---

## 6. System Architecture — v3 Layered Design

v3 introduces four new layers over the original five-layer v2 architecture: an External Data Ingestion layer, an API Gateway and Auth layer, a Job Queue and Cache layer, and a Real-time Notification layer.

```
LAYER 0 — EXTERNAL DATA INGESTION (NEW)
  OpenWeatherMap API, Tomorrow.io, CPCB AQI API
  Celery Beat CRON — polls every 5 minutes
  Feeds live weather signals into DisruptionSeverityModel
        |
        v
LAYER 1 — CLIENT
  React 18 + Vite + TailwindCSS + Socket.IO
  Worker portal, Admin dashboard, Live claim tracker
  Real-time updates via WebSocket — no manual refresh
        |
        v
LAYER 1.5 — API GATEWAY + AUTH (NEW)
  Kong / Traefik — centralized ingress
  Rate limiting, IP allowlisting, JWT RS256, RBAC
  Blocks unauthenticated requests before they reach the ML pipeline
        |
        v
LAYER 2 — FASTAPI CONTROLLER
  HTTP REST endpoints, Pydantic v2 schema validation
  WebSocket manager, background task dispatcher
  Delegates compute-heavy operations to Celery task queue
        |
        v
LAYER 3 — BUSINESS LOGIC ENGINE
  Auth, subscription pricing, claim lifecycle state machine
  Parametric Trigger Engine — auto-initiates claims on threshold breach
  Payout decision routing
        |
        v
LAYER 4 — JOB QUEUE + CACHE (NEW)
  Redis + Celery Workers
  Async ML inference — API returns job_id immediately
  ML output cached 10 minutes during mass claim events
        |
        v
LAYER 5 — ML INFERENCE ENGINE
  FraudRiskModel (XGBoost + Random Forest ensemble)
  PayoutAuditRegressor (XGBRegressor)
  DisruptionSeverityClassifier (XGBClassifier)
  In-memory model registry with versioning
  SHAP explainability per claim
        |
        v
LAYER 6 — ORM / DATA ACCESS
  SQLAlchemy 2.0, Repository pattern per entity
  Alembic migrations for schema versioning
  Atomic transactional writes for claims and payouts
        |
        v
LAYER 7 — PERSISTENCE
  PostgreSQL 15 (concurrent writes, replaces SQLite)
  Redis (ephemeral sessions, baseline cache, rate limiting)
  S3 / MinIO (ML model artifacts, audit logs, claim photos)
```

### End-to-End Claim Flow

```
Step 1 — Worker Registration and KYC
  Worker registers with phone number and delivery platform ID
  Aadhaar OKYC + PAN verification via Setu / DigiLocker API
  Consent timestamp and IP logged in immutable audit table
  Backend creates verified profile in PostgreSQL

Step 2 — Baseline Calculation
  ML Module 1 fetches verified 60-day earnings from Platform API
  Computes trimmed mean baseline per worker
  Cached in Redis for real-time 15-minute comparison

Step 3 — Automated Real-Time Monitoring
  weather_poller.py (Celery Beat) polls OpenWeatherMap every 5 minutes
  Evaluates reading against PARAMETRIC_THRESHOLDS
  Threshold breach → trigger_engine.py auto-initiates claims for all
    active subscribers in affected zone — no admin action required
  Simultaneously, backend monitors platform earnings baseline
  70% earnings drop sustained for 30+ minutes → claim initiated

Step 4 — Claim Validation Pipeline (automated, under 2 minutes)
  Layer 1: Exclusion Engine (deterministic, runs first)
    Checks EX-01 through EX-06 — any match → reject with reason code
  Layer 2: Earnings authenticity verification via Platform API
  Layer 3: Baseline comparison and disruption confirmation
  Layer 4: Accelerometer, GPS variance, IMU cross-reference
           Google Maps Routes API computes real route_deviation_pct
  Layer 5: Wi-Fi and cell tower triangulation
  Layer 6: Delivery zone history, peer validation, climate zone confirmation
  Fraud Risk Score computed → auto-approve / soft flag / hard flag

Step 5 — Payout Processing
  Payout = Base Daily Income x Coverage Rate x Severity Multiplier x Loyalty Bonus
  Razorpay Payouts API initiates UPI or NEFT transfer to worker's account
  Transaction ID logged in PostgreSQL
  Worker notified via WhatsApp SMS (Twilio) and WebSocket push
  Policy PDF generated and attached to claim record
  Weekly ledger updated
```

---

## 7. Machine Learning Architecture

FleetLock's intelligence runs across four ML modules, each serving a distinct role in the claim lifecycle. All models are served through an in-memory registry, versioned with MLflow, and retrained monthly from production claim data via an automated Celery pipeline.

---

### Module 1 — Earnings Baseline Engine

**Model Type:** Time-Series Rolling Average with Day-of-Week and Hour-of-Day Weighting

```
INPUT:
  60 days of verified hourly earnings from Platform API
  Day-of-week pattern weights (Friday peaks vs. Monday troughs)
  Hour-of-day pattern weights (lunch rush vs. late night)
  Zone-level order density from platform data

PROCESSING:
  Weighted rolling average computed per worker, per 15-minute window
  Disruption threshold: 70% drop in earnings sustained for 30+ minutes

OUTPUT:
  Personal baseline stored per worker in Redis cache
  Recalculated weekly as new earnings data arrives
  Primary trigger signal for all non-accident claims
```

---

### Module 2 — Fraud Detection Engine

**Model Type:** Ensemble — XGBoost (70%) + Random Forest (30%) + Deterministic Rule Layer + Isolation Forest

```
INPUT (per claim):
  Platform earnings data for the claim window (verified via Platform API)
  Order acceptance and completion log from Platform API
  Accelerometer and motion sensor data from device
  GPS coordinates, signal strength, and atmospheric variance
  route_deviation_pct and gps_drift_meters from Google Maps Routes API
  IMU gyroscope cross-reference against GPS movement
  Wi-Fi SSID and cellular tower triangulation
  Worker's 30-day delivery zone history
  OpenWeatherMap / CPCB data for the specific pin code and time window
  Earnings status of peer workers in the same zone
  Claim cluster density in zone over the last 10 minutes
  Device fingerprint hash and IP subnet
  Social graph flags (referral chain and simultaneous claims)

PROCESSING:
  Rule Layer applies instant hard flags:
    - Earnings data contradicts claimed loss → auto-reject
    - Claim cluster exceeds 20 in 10 minutes → batch auto-pause
    - Same device ID across multiple accounts → ring flag
    - GPS path smoothness score below threshold → spoofing flag
  Isolation Forest scores remaining claims on anomaly distance
  XGBoost + Random Forest ensemble assigns final fraud probability
  SHAP values computed per claim for full decision explainability

OUTPUT — Fraud Risk Score (0 to 100):
  Score 0 - 39   → Auto-approve
  Score 40 - 75  → Soft or medium verification step requested
  Score 76 - 100 → Hard flag, 50% provisional payout, human review
```

The ensemble is trained on production claim data (post-launch) using SMOTE oversampling to handle the natural rarity of fraud cases. Feature inputs include GPS telemetry from Google Maps Routes API, speed jump analysis, device context signals, and historical claim frequency. Models are versioned in MLflow and retrained monthly automatically.

---

### Module 3 — Dynamic Premium Calculator

**Model Type:** XGBoost Regression

The weekly premium each worker pays is recalculated every Sunday night for the coming week.

```
INPUT:
  Worker's current risk tier and zone
  Next-week weather forecast from OpenWeatherMap / Tomorrow.io
  Zone's historical claim rate for the same calendar week in prior years
  Worker's claim count and payout total in the past 4 weeks
  Worker's active platform days in the past 4 weeks

PROCESSING:
  XGBoost regression predicts expected weekly claim cost per worker
  Outputs a risk multiplier between 0.85x and 1.25x on base premium
  Total adjusted premium capped at 140% of base plan premium in any week

OUTPUT:
  Adjusted weekly premium per worker
  Worker notified by Friday of the premium for the coming Monday deduction
```

---

### Module 4 — Disruption Severity Classifier

**Model Type:** XGBoost Classifier with Rule-Based Fallback

```
INPUT:
  rainfall_mm — from OpenWeatherMap API (real, live data)
  temperature_celsius — from OpenWeatherMap API
  aqi_index — from CPCB AQI API
  wind_speed_kmh — from OpenWeatherMap API
  flood_alert_flag — from Tomorrow.io hyperlocal alerts
  active_claims_zone — live count from PostgreSQL
  baseline_claims_zone — historical average
  time_of_day_encoded — 0=night, 1=morning, 2=afternoon, 3=evening
  api_outage_flag — from Platform Status API
  disruption_type — "weather" | "platform_outage" | "civic_event"

PROCESSING:
  XGBClassifier assigns severity: low / medium / high
  Severity multiplier mapped: low=0.75, medium=1.00, high=1.25
  trigger_auto_claim flag output determines if parametric trigger fires
  Rule-based fallback activates automatically if model fails to load

OUTPUT:
  predicted_severity, severity_multiplier, confidence_map
  trigger_auto_claim: true/false
  model_version for audit traceability
```

**Parametric Auto-Trigger Logic (v3 — new):**
```
PARAMETRIC_THRESHOLDS = {
    "rainfall_mm":    (">", 75),   # Trigger if rainfall > 75mm
    "wind_speed_kmh": (">", 60),   # Trigger if wind > 60 km/h
    "aqi_index":      (">", 200),  # Trigger if AQI > 200
}
```
When any threshold is crossed, `trigger_engine.py` automatically initiates claims for all active subscribers in the affected zone. No administrator needs to take any action.

---

### Claim Decision Pipeline

The `ClaimDecisionEngine` in production orchestrates all modules in a strict sequential pipeline. Each step can independently block a claim. The reason is logged and disclosed to the worker on request.

```
CLAIM RECEIVED
      |
      v
EXCLUSION ENGINE (deterministic — runs first)
  EX-01 through EX-06 checked → reject with policy code if triggered
      |
      v
FRAUD DETECTION ENGINE (async via Celery)
  Rule Layer → Isolation Forest → XGBoost + RF Ensemble → SHAP
      |
      v
DISRUPTION SEVERITY CLASSIFIER
  Live weather API input → severity multiplier determined
      |
      v
PAYOUT CALCULATION ENGINE
  Base Daily Income x Coverage Rate x Severity Multiplier x Loyalty Bonus
      |
      v
POLICY ENGINE
  Coverage window and per-day limit checks
      |
      v
DISBURSEMENT
  Razorpay Payouts API → UPI / NEFT to worker account
      |
      v
NOTIFICATION
  WebSocket push + Twilio SMS/WhatsApp
```

---

## 8. Parametric Triggers — Fully Automated

All triggers in v3 are initiated automatically by the platform. Workers do not need to file a claim for any environmental, social, or platform event.

| Trigger | Data Source | Threshold | Payout Rule |
|---|---|---|---|
| Earnings Drop | Platform API (verified) | 70% drop from 30-day baseline for 30+ min | Actual loss computed by formula |
| Heavy Rain | OpenWeatherMap / IMD | Rainfall above 75mm/hr in pin code | 5% of previous day earnings per blocked hour |
| Flood Alert | Tomorrow.io / NDMA | Hyperlocal red alert issued for zone | 5% of previous day earnings per blocked hour |
| Extreme Heat | OpenWeatherMap | Temperature above 42°C, 11 AM to 4 PM | 5% of previous day earnings per blocked hour |
| Severe Air Pollution | CPCB AQI API | AQI above 200 in zone | 5% of previous day earnings per blocked hour |
| High Wind | OpenWeatherMap | Wind speed above 60 km/h | 5% of previous day earnings per blocked hour |
| Curfew or Bandh | Social / News API | Zone-level restriction confirmed | 2% of each cancelled order value |
| Platform Outage | Platform Status API | Confirmed downtime above 90 minutes | 1% of previous day earnings per confirmed outage hour |

The Celery Beat scheduler polls weather and platform status APIs every 5 minutes. When a threshold is crossed, `trigger_engine.py` fires claims for all active subscribers in the affected zone within the same polling window — typically under 5 minutes from the event onset.

---

## 9. Fraud Detection and Anti-Spoofing Strategy

### The Threat: Coordinated GPS Spoofing

A sophisticated fraud ring uses GPS-spoofing software to place themselves inside a declared weather zone while safely at home. They submit simultaneous claims during a real monsoon event.

This attack breaks any system that relies primarily on GPS as its validation signal. FleetLock is built to survive it.

### Why Platform Earnings Data Changes Everything

```
CONVENTIONAL SYSTEM (vulnerable):
  GPS spoofed → Appears in monsoon zone
  Weather API confirms rain → Real event is occurring
  500 simultaneous claims → System cannot distinguish genuine from fake

FLEETLOCK (resilient):
  Fraudster claims income loss during storm
  System queries Platform API: worker actually earned Rs. 350 during claimed window
  Earnings data contradicts claimed loss → auto-reject before human involvement
  Repeated for 490 fraudsters → all auto-rejected
  Liquidity pool intact
  10 genuine workers paid correctly
```

### Multi-Signal Validation — What a Home-Based Fraudster Cannot Fake Simultaneously

| Signal | Genuine Stranded Worker | GPS Spoofer at Home |
|---|---|---|
| Platform earnings | Actual drop visible in Platform API | Earnings continue or were never started |
| Order activity log | Was accepting orders until disruption | Not logged in or never active |
| Accelerometer | Shows outdoor motion, hand-held patterns | Device flat and stationary |
| GPS signal variance | Natural atmospheric jitter | Unnaturally smooth — software-generated |
| Route deviation (Google Maps Routes API) | Trace matches disrupted zone | Computed route shows no disruption |
| IMU cross-reference | Gyroscope matches movement claim | IMU shows stationary device |
| Cell tower triangulation | Independent estimate matches claimed zone | Network places device elsewhere |
| Delivery zone history | 30-day history in this zone | Zero or near-zero prior activity |
| Climate zone verification | OpenWeatherMap confirms event at pin code | No weather event at claimed pin code |
| Peer worker validation | Others in zone also show zero earnings | Only this worker claiming; peers show normal |

Six of ten signals must be consistent with genuine outdoor presence for auto-approval. A single inconsistent signal moves the claim to soft verification — never to instant rejection on its own.

### Fraud Risk Tiers and Worker-Facing Experience

```
Score 0 - 39    AUTO-APPROVE
                Payout initiated via Razorpay Payouts API immediately.
                Worker notified via WhatsApp and in-app WebSocket push.
                Timeline: under 5 minutes.

Score 40 - 60   SOFT FLAG
                Worker receives: "We are verifying your claim due to
                network conditions. You will hear back in 2 hours."
                Secondary cell tower and Wi-Fi triangulation runs automatically.
                If check passes: approved with zero penalty to worker.
                Worker is never informed they were flagged.
                Timeline: under 30 minutes.

Score 61 - 75   MEDIUM FLAG
                Worker is asked: "Please share a quick photo of your surroundings."
                Framed as weather confirmation — never as an accusation.
                Timestamp and GPS metadata auto-attached by the app.
                Timeline: under 10 minutes once photo submitted.

Score 76 - 100  HARD FLAG
                Claim enters human review queue.
                50% provisional payout issued immediately — worker is not left with zero.
                Worker may submit: photo, current location, or supporting document.
                Full appeal available via in-app support.
                Resolved within 24 hours.
                Only confirmed fraud leads to policy suspension.
```

**Expected Detection Rates:**

| Attack Type | Detection Rate | Primary Catch Mechanism |
|---|---|---|
| Solo GPS spoofer | 99%+ | Earnings contradiction + cell tower mismatch |
| Small ring (10 workers) | 95%+ | Device fingerprinting + behavioural clustering |
| Medium ring (100 workers) | 98%+ | Claim clustering + social graph analysis |
| Large ring (500 workers) | 99.5%+ | Batch auto-pause + all layers simultaneously |
| Professional coordinated attack | 99.9%+ | Multiple independent catches across all layers |

---

## 10. Insurance Plans and Weekly Premium Model

| Feature | Sahara (Level 1) | Kavach (Level 2) | Suraksha (Level 3) |
|---|---|---|---|
| Daily Premium | Rs. 29 | Rs. 59 | Rs. 99 |
| Coverage Rate | 40% of Daily Income | 60% of Daily Income | 80% of Daily Income |
| Max Covered Days / Window | 3 days | 5 days | 7 days |
| Target Worker | Part-time / occasional | Full-time delivery partner | Power users / high earners |

Premiums are structured on a weekly basis to match the natural financial cycle of gig workers. Premium is auto-deducted every Monday from the worker's platform payout — no separate bank debit required.

Each policy covers a 15-day window. The premium for each worker is dynamically adjusted by the Module 3 XGBoost model using a zone risk factor (0.85x to 1.20x) and a seasonal risk factor (0.90x to 1.25x). The combined adjustment will never cause the weekly premium to exceed 140% of the base plan rate. Workers are notified of the coming week's premium every Friday.

---

## 11. Coverage Exclusions — What Is Not Covered and Why

Every exclusion is enforced programmatically through the Exclusion Engine — the first layer in the `ClaimDecisionEngine` — using policy codes EX-01 through EX-06. A claim that triggers any exclusion code is rejected before it reaches fraud scoring or payout calculation. Every rejection includes the specific policy code, a plain-language explanation, and appeal instructions. The worker is never left without a reason.

**EX-01 — Health, Life, and Accident Exclusion**
Illness, injury, hospitalisation, disability, death, or accident-related expenses. FleetLock is an income protection product, not a health or life insurance product. These events require different actuarial models, underwriting frameworks, and regulatory compliance.

**EX-02 — Vehicle and Equipment Exclusion**
Vehicle breakdown, accident damage, maintenance costs, or loss or theft of delivery equipment. Vehicle costs are variable, discretionary, and driven by the worker's own maintenance behaviour — they cannot be objectively validated through external APIs. These fall under motor insurance categories outside the scope of parametric income coverage.

**EX-03 — Catastrophic Systemic Event Exclusion**
Income loss from war, terrorism, a government-declared national pandemic resulting in platform-wide suspension, nuclear or chemical contamination, or nationwide failure of critical infrastructure. These events create correlated simultaneous losses across the entire policyholder pool. No pooled premium model can fund claims when every insured worker in every zone is affected at the same time.

**EX-04 — Voluntary Inactivity Exclusion**
Any day on which the worker was voluntarily offline, logged out, or on personal leave — regardless of whether a qualifying disruption occurred in their zone. The platform API's login and activity logs provide the objective signal. A worker not logged in and accepting orders at the time of the trigger event has this exclusion applied automatically.

**EX-05 — Platform Conduct and Suspension Exclusion**
Income loss attributable to account suspension or deactivation by the delivery platform due to the worker's own conduct. FleetLock insures workers against things they cannot control. A platform suspension is a consequence of the worker's own actions. Covering it would create severe moral hazard.

**EX-06 — Platform Commercial Policy Exclusion**
Changes made by the delivery platform to its commission structure, payout rates, surge pricing algorithm, or delivery zone boundaries. These are business decisions made by a third-party commercial entity — not external disruptions. Insuring against commission changes would make FleetLock financially dependent on the internal strategy decisions of Zomato or Swiggy, which cannot be predicted, validated, or priced actuarially.

---

## 12. External API Integrations

All external integrations are isolated inside the `integrations/` module. No service layer file imports an HTTP client directly.

### Group 1 — Environmental Data (Fixes Gaps 02, 03)

**OpenWeatherMap API** — `integrations/weather_client.py`
Called by `scheduler/weather_poller.py` every 5 minutes. Provides live `rainfall_mm`, `temperature_celsius`, `wind_speed_kmh`, and `aqi_index` per zone lat/lon. Maps directly into DisruptionSeverityModel input features.

**Tomorrow.io API** — `integrations/weather_client.py`
Secondary weather source for hyperlocal, street-level flood and severe weather alerts. Both APIs are called on every polling cycle; the maximum severity reading from either source is used for conservative claim protection.

**CPCB AQI API** — `integrations/aqi_client.py`
Official Indian pollution monitoring data for AQI triggers above 200.

### Group 2 — Telematics and GPS (Fixes Gap 03)

**Google Maps Routes API** — `integrations/telematics_client.py`
Called during claim creation to compute `route_deviation_pct` and `gps_drift_meters` by comparing the worker's submitted GPS trace against the expected two-wheeler delivery route. Replaces the Gaussian noise generator that generated synthetic GPS features in v2. These computed values feed directly into the FraudRiskModel.

### Group 3 — Payments (Fixes Gap 04)

**Razorpay Payouts API** — `services/payout_service.py`
Called when `audit_flag = False` and the claim is auto-approved. Initiates a UPI or NEFT transfer to the worker's registered fund account in paise. Transaction reference ID is logged against the claim in PostgreSQL. Currently in test mode; production mode available from Phase 3.

### Group 4 — Notifications (Fixes Gap 06)

**Twilio SMS and WhatsApp API** — `integrations/notification_client.py`
Triggered on claim state transitions: created, approved, and payout disbursed. Also fires a subscription expiry reminder 48 hours before policy window end.

### Group 5 — Compliance and KYC (Fixes Gap 09)

**Setu / DigiLocker API** — `services/auth_service.py`
Called during worker registration. Verifies Aadhaar OKYC and PAN before account activation. Required for IRDAI-compliant insurance product launch in India. Consent timestamp and IP are stored in a write-once audit log table. Available via `sandbox.setu.co` for the hackathon phase.

### Group 6 — Platform Earnings Verification (Fixes Gap 11)

**Swiggy / Zomato / Blinkit Partner APIs** — `integrations/platform_client.py`
Called during worker onboarding and during the Earnings Baseline calculation to verify `base_daily_income` against the platform's own records. Replaces the Gaussian EarningRecord mock generator entirely. For the hackathon phase, a verified-screenshot upload flow is available as an interim path. Full partner API integration requires a B2B commercial agreement with each platform.

---

## 13. Disruption Simulator — Stress Testing the Network

The Admin Control Panel includes a purpose-built Disruption Simulator. This is a production risk management tool that allows operators to stress-test the insurance network against synthetic disruption scenarios before real events occur.

**Zonal Trigger Injection**
Administrators can target any registered high-risk zone — HSR Layout (Bengaluru), Andheri (Mumbai), T. Nagar (Chennai) — and inject a simulated disruption event of any category: heavy rainfall, platform outage, curfew, or extreme heat. The simulator fires the same parametric trigger pipeline that runs in production.

**Mass-Auto Processing**
A single simulation generates thousands of concurrent synthetic claim requests — one per active policy in the targeted zone. Every claim is processed individually through the full ML pipeline: Exclusion Engine, Fraud Detection, Payout Calculation, and Policy Validation. The simulator does not batch-approve. It exercises the full decision architecture under load.

**Financial Impact Forecasting**
The admin dashboard displays in real time:
- Approval and rejection rates as the ML engine processes each claim
- Running total of simulated payout disbursements
- Loss Ratio: the ratio of simulated payouts to premiums collected from the affected zone
- Fraud Flag Rate: the percentage of synthetic claims that triggered fraud scoring
- Liquidity Impact Chart: a time-series view showing how the payout pool would be affected if this disruption were real

If a simulated event produces a Loss Ratio above the actuarial threshold, it means the weekly premium for that zone needs adjustment — and Module 3 will reflect that in the following Sunday's recalculation.

---

## 14. Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| Mobile App | React Native (Android-first) | Single codebase, performant on low-end Android devices common among delivery workers |
| Web Dashboard | React 18, Vite, TailwindCSS, Recharts, Socket.IO | Fast SPA, real-time WebSocket updates for admin and worker views |
| Backend API | Python FastAPI + Pydantic v2 | Async, lightweight, ideal for serving ML models alongside REST and WebSocket endpoints |
| API Gateway | Kong / Traefik | Centralized rate limiting, RBAC, JWT RS256, IP allowlisting |
| ML Models | XGBoost, Random Forest, Scikit-Learn, Prophet, Isolation Forest, SMOTE | Industry-standard, deployable via FastAPI with Joblib serialisation |
| ML Explainability | SHAP | Per-claim decision explainability for admin audit and IRDAI compliance |
| ML Versioning | MLflow | Experiment tracking and model versioning across monthly retraining cycles |
| Primary Database | PostgreSQL 15 (production) / SQLite (development) | Concurrent writes for mass claim events; Alembic for schema migrations |
| Cache and Task Queue | Redis + Celery + Celery Beat | Earnings baseline cache, async ML inference, scheduled weather polling |
| Monitoring | Grafana + Loki + Sentry | Structured JSON logging, dashboards, exception tracking in ML and payment flows |
| Object Storage | S3 / MinIO | ML model artifacts, claim evidence photos, audit logs, policy PDFs |
| Earnings Data | Swiggy / Zomato / Blinkit Partner APIs | Verified platform earnings — the ground truth for baseline and fraud detection |
| Weather | OpenWeatherMap + Tomorrow.io | Live rain, temperature, AQI, and hyperlocal flood alerts at pin code level |
| AQI | CPCB API | Official Indian pollution monitoring data |
| Telematics | Google Maps Routes API | Real route deviation and GPS drift computation for fraud model |
| Payments | Razorpay Payouts API (test mode) | Actual UPI and NEFT disbursement to worker accounts |
| Notifications | Twilio SMS + WhatsApp | Claim event and payout confirmation delivery |
| KYC | Setu / DigiLocker API | Aadhaar OKYC + PAN verification for IRDAI compliance |
| Containerisation | Docker and Docker Compose | Consistent development and production environments |
| CI/CD | GitHub Actions | Automated testing and deployment pipeline |
| Hosting | Vercel (frontend) + Render (backend) | Free-tier friendly for hackathon phase; production-ready for scale |

---

## 15. Project Structure

```
FleetLock/
├── app/
│   ├── api/                    # Route definitions only — no business logic
│   │   ├── auth.py
│   │   ├── worker.py
│   │   ├── admin.py
│   │   └── websocket.py
│   │
│   ├── services/               # Business logic — no raw SQL, no ML imports
│   │   ├── auth_service.py     # KYC via Setu API on registration
│   │   ├── subscription_service.py
│   │   ├── claim_service.py
│   │   ├── payout_service.py   # Razorpay Payouts API integration
│   │   └── trigger_engine.py   # Parametric auto-trigger logic
│   │
│   ├── ml/                     # ML inference — pure prediction, no DB writes
│   │   ├── fraud_model.py      # XGBoost + RF ensemble
│   │   ├── payout_model.py     # XGBRegressor
│   │   ├── disruption_model.py # XGBClassifier
│   │   ├── model_registry.py   # In-memory registry with MLflow versioning
│   │   └── feature_builder.py  # Centralised feature engineering
│   │
│   ├── db/                     # ORM only — no business logic
│   │   ├── models.py
│   │   ├── database.py
│   │   └── repositories/
│   │       ├── worker_repo.py
│   │       ├── claim_repo.py
│   │       └── payout_repo.py
│   │
│   ├── scheduler/              # CRON jobs and async task workers
│   │   ├── celery_app.py
│   │   ├── tasks.py
│   │   └── weather_poller.py   # OpenWeatherMap + Tomorrow.io polling
│   │
│   └── integrations/           # External API clients — fully isolated
│       ├── weather_client.py   # OpenWeatherMap + Tomorrow.io
│       ├── aqi_client.py       # CPCB AQI API
│       ├── telematics_client.py# Google Maps Routes API
│       ├── platform_client.py  # Swiggy / Zomato / Blinkit partner APIs
│       ├── payment_client.py   # Razorpay Payouts API
│       └── notification_client.py # Twilio SMS + WhatsApp
│
├── tests/
│   ├── unit/                   # Per-module unit tests
│   └── integration/
│
├── alembic/                    # Database migrations
├── frontend/                   # React 18 + Vite
├── main.py
├── config.py                   # Pydantic Settings — all env vars
├── docker-compose.yml
└── .github/workflows/          # CI/CD via GitHub Actions
```

---

## 16. Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- PostgreSQL 15 (or use the Docker Compose setup)
- Redis (or use the Docker Compose setup)

### Environment Variables

Copy `.env.example` to `.env` and configure:

```
# Database
DATABASE_URL=postgresql://fleetlock:password@localhost:5432/fleetlock

# Redis
REDIS_URL=redis://localhost:6379

# Weather APIs
OPENWEATHERMAP_API_KEY=your_key_here
TOMORROW_IO_API_KEY=your_key_here

# Telematics
GOOGLE_MAPS_API_KEY=your_key_here

# Payments
RAZORPAY_KEY_ID=your_key_here
RAZORPAY_KEY_SECRET=your_key_here
RAZORPAY_ACCOUNT_NUMBER=your_account_here

# Notifications
TWILIO_ACCOUNT_SID=your_sid_here
TWILIO_AUTH_TOKEN=your_token_here
TWILIO_PHONE_NUMBER=your_number_here

# KYC
SETU_CLIENT_ID=your_client_id_here
SETU_CLIENT_SECRET=your_client_secret_here

# ML
MLFLOW_TRACKING_URI=http://localhost:5000
```

### Run with Docker (Recommended)

```bash
docker-compose up --build
```

This starts PostgreSQL, Redis, the FastAPI backend, Celery workers, Celery Beat scheduler, and the React frontend in a single command.

### Backend (Manual)

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
python main.py
```

Wait for: `FleetLock: Machine Learning engine initialized correctly.`

The server starts at `http://localhost:8000`. Interactive API documentation is available at `http://localhost:8000/docs`.

On first boot, the seeder automatically generates 60 days of historical earnings data for all seeded workers and trains the ML models from that data.

### Frontend (Manual)

```bash
cd frontend
npm install
npm run dev
```

The React frontend is available at `http://localhost:5173`.

Ensure `src/services/api.js` points to `http://localhost:8000` for local development. For production deployment on Vercel, update this to your Render backend URL.

### Start Celery Workers and Scheduler

```bash
# In separate terminal — async ML inference workers
celery -A app.scheduler.celery_app worker --loglevel=info

# In separate terminal — automated weather polling and retraining scheduler
celery -A app.scheduler.celery_app beat --loglevel=info
```

### Default Credentials (Auto-Seeded)

| Portal | Username | Password |
|---|---|---|
| Worker Dashboard | ravik | password123 |
| Admin Control Panel | admin | admin123 |

---

## 17. Team

**LeadToWin** — Department of Computer Science and Engineering

| Name | Role |
|---|---|
| S. Buubes | CSE |
| V. Pooja | CSE |
| N. Ram Narren Gowtham | CSE |
| V. Yogapoorvaja | CSE |

---

*FleetLock turns the unpredictability of the city into a solvable data problem — and ensures that every disruption a worker cannot control is one they will no longer have to absorb alone.*
