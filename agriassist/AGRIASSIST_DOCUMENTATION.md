# AgriAssist — Comprehensive Project Documentation

> **Built with ❤️ for Indian Farmers** | Team: Pixel Pirates (TS2630)
> Platform Version: 2.0.0-BETA | Stack: FastAPI · Neo4j · Google Gemini · YOLOv8 · Shardeum

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Core Features (with Technical Detail)](#3-core-features-with-technical-detail)
4. [System Architecture](#4-system-architecture)
5. [User Flows](#5-user-flows)
6. [Tech Stack](#6-tech-stack)
7. [AI & ML Components](#7-ai--ml-components)
8. [Data Flow](#8-data-flow)
9. [Innovation & Originality](#9-innovation--originality)
10. [Real-World Impact & Feasibility](#10-real-world-impact--feasibility)
11. [Challenges & How They Were Solved](#11-challenges--how-they-were-solved)
12. [Future Roadmap](#12-future-roadmap)

---

## 1. Project Overview

**AgriAssist** is an AI-driven agricultural ecosystem built to empower every type of farmer in India — from rural smallholders tending several hectares of land to urban residents growing food on a 3 m² apartment balcony. The platform unifies computer-vision-based plant scanning, graph-database-powered crop intelligence, Admin land verification, Twilio voice calls in Hindi, and a no-code admin AI agent into a single, deployable web application.

At its core, AgriAssist answers three questions every farmer has:

- **What should I grow?** — Personalised crop recommendations based on soil type, irrigation, season, and local trend data pulled from a Neo4j knowledge graph.
- **Is my crop healthy?** — A dual-engine scanner (YOLOv8 for object detection + Google Gemini Vision for botanical classification) that identifies species, flags invasive threats, and instantly alerts every farmer within 5 km via Twilio SMS.
- **Is my land legitimately mine?** — An admin-gated document-verification workflow that, upon approval, records an immutable audit trail on the  auto-calculates the farm's carbon credit portfolio.

For urban farmers, a separate module uses Gemini Vision to analyse a user-drawn polygon on a balcony or terrace photo and generate a complete, week-by-week planting plan with an SVG layout diagram, budget breakdown, and monthly yield estimates — all persisted natively in Neo4j.

Administrators do not need SQL skills: they interact with the platform through a Perplexity-style streaming AI chat interface backed by a LangChain + Gemini orchestrator that routes queries to five specialised agents (portfolio analysis, personalised campaigns, churn detection, crop advisor audit, and data visualisation with matplotlib charts streamed as live SSE events).

---

## 2. Problem Statement

### Rural Dimension

India has more than 140 million farm holdings, the majority of which are smaller than 2 hectares (smallholder/marginal farmers). These farmers face:

| Challenge | Detail |
|---|---|
| **Information asymmetry** | Crop decisions are made by word-of-mouth, with no awareness of what neighbouring farms are planting or what the soil data suggests. |
| **Invasive species spread** | Weeds like *Parthenium hysterophorus* (congress grass) and crop blights spread silently across farm boundaries. By the time a farmer notices the problem, neighbours are already infected. There is no early-warning system. |
| **No carbon credit access** | Smallholders generate real carbon sequestration value but have zero tooling to quantify, verify, or monetise it. |
| **Language and literacy barriers** | Most agricultural advisory services are English-first and text-heavy, inaccessible to Hindi-speaking farmers with limited smartphone fluency. |
| **Land verification friction** | Getting a farm officially recognised for government schemes or insurance requires physical documentation workflows that can take months. |

### Urban Dimension

Urban India is experiencing a rapid rise in rooftop and balcony farming, driven by food safety concerns and sustainability awareness. However:

- There is no tool that analyses a specific photo of a balcony and tells a city dweller *exactly* what to grow in *exactly* that amount of space, factoring in sunlight direction, container sizes, and Indian market prices.
- Urban farmers have no path to carbon credits despite their measurable contribution to urban cooling and carbon offsetting.
- Personalised, bilingual AI guidance for container gardening in an Indian context is absent from the market.

### Administrative Dimension

Platform operators managing thousands of farmer records need business intelligence without needing a data scientist. Manual SQL queries, static dashboards, and Excel exports are too slow for real-time decision making.

**AgriAssist addresses all three dimensions in a single, integrated platform.**

---

## 3. Core Features (with Technical Detail)

### 3.1 Farm Mapping & Registration

**What it does:** Farmers draw the boundary of their farm on an interactive map. The system calculates the exact area in hectares and acres, records soil type, water source, and irrigation type, and stores the GPS polygon both in SQLite (relational) and Neo4j (graph).

**How it works technically:**
1. The frontend (JavaScript + Leaflet.js) allows the farmer to click points on a map to define a polygon. Each vertex is stored as `{"lat": float, "lon": float}`.
2. On submission, the backend (`POST /api/farms/`) passes the coordinate list to `FarmCalculator.calculate_area()`.
3. `FarmCalculator` uses **Shapely** to create a polygon and **PyProj** to reproject it from WGS-84 (GPS lat/lon) to UTM Zone 43N (EPSG:32643), which is the metric coordinate system covering peninsular India. This ensures area calculations are geographically accurate regardless of longitude variation.
4. The resulting area (hectares, acres, square meters, perimeter) is stored in the `farms` SQL table.
5. Simultaneously, a **Neo4j** `Farm` node is created with a native `point({latitude, longitude})` property, enabling future spatial distance queries in Cypher.
6. The farmer can then upload a land ownership document (PDF, JPEG, PNG). The farm's `verification_status` becomes `"pending"` and the admin is notified.

**Technologies:** FastAPI, SQLAlchemy, Shapely, PyProj, Neo4j Python Driver, Leaflet.js.

**User value:** Farmers get an instantly calculated farm size (useful for fertiliser and seed estimates) and a pathway to carbon credit calculation and government scheme eligibility.

---

### 3.2 Invasive Species Detection & Alert System

**What it does:** When a farmer scans a plant and the AI flags it as invasive or diseased, the system automatically finds all other registered farmers within a 5 km radius and sends them an SMS warning via Twilio.

**How it works technically:**
1. After Gemini Vision identifies a plant as invasive (`is_invasive: true`), the detection is written to the `plant_detections` SQL table.
2. The detection is simultaneously recorded in Neo4j as a `Plant` node with GPS coordinates: `SET p.location = point({latitude, longitude})`.
3. A Cypher spatial query is executed via `GraphService.find_nearby_farmers()`:

```cypher
MATCH (plant:Plant {id: $plant_id})
MATCH (neighbor:Farmer)-[:OWNS]->(farm:Farm)
WHERE neighbor.id <> $farmer_id
  AND plant.location IS NOT NULL
  AND farm.location IS NOT NULL
  AND point.distance(plant.location, farm.location) < 5000
RETURN neighbor.phone, 
       toInteger(point.distance(plant.location, farm.location)/1000) AS distance_km
```

4. For each neighbor returned, a **Twilio** SMS is sent with a personalised message: *"⚠️ AgriAssist Alert: [Species] detected [N]km near your farm! Please remain vigilant."*
5. If Twilio credentials are not configured, the system logs a simulation message (graceful degradation).

**Technologies:** Neo4j spatial `point()` type, Cypher `point.distance()`, Twilio REST API, FastAPI background tasks.

**User value:** Creates a community early-warning network. A disease detected by one farmer becomes protection for every farmer nearby — turning individual vigilance into collective intelligence.

---

### 3.3 Plant Scanner (Dual-Engine: YOLOv8 + Gemini Vision)

**What it does:** A farmer uploads a photo of a plant. Within seconds, the system returns the species name (common, Latin, and local Indian name), an invasive/safe verdict, a threat level, confidence score, and detailed treatment or care instructions.

**How it works technically — Dual-Engine Design:**

| Engine | Role | Model |
|---|---|---|
| **YOLOv8** (offline) | Object detection — draws bounding boxes on detected objects, generates an annotated image | `yolov8n.pt` (Ultralytics) |
| **Gemini Vision** (cloud) | Botanical classification — identifies exact species, assesses invasiveness, generates removal/care advice | `gemini-1.5-flash` |

**Processing pipeline (`POST /api/plants/identify`):**
1. Image is validated (max 10 MB) and compressed via Pillow.
2. **Engine 1 (YOLO):** `VisionService.scan_plant()` runs inference on the saved image path. Bounding boxes are plotted using YOLO's built-in `.plot()` method. The annotated image is saved to disk.
3. **Engine 2 (Gemini Vision):** The original bytes are sent to `GeminiService.identify_plant()` with a structured JSON-forcing prompt that requests species, common name, local name, invasiveness flag, threat level, confidence score, and removal/care instructions.
4. Gemini's response is cleaned of any Markdown fences and parsed as JSON.
5. If Gemini fails (network error, quota), the system falls back to the YOLO predictions silently.
6. Results are persisted and **gamification points** are awarded (50 for any scan, 100 for an invasive species).
7. Simultaneously, the Neo4j graph is updated and the alert pipeline (3.2) is triggered if invasive.

**Technologies:** Ultralytics YOLOv8, OpenCV, Pillow, Google Generative AI SDK (`google-generativeai`), FastAPI UploadFile.

**User value:** Farmers get professional-grade botanical identification accessible from any smartphone camera, with automatic community protection activated on invasive findings.

---

### 3.4 Crop Recommendation Engine (Budget + Season + Soil + Graph-Aware)

**What it does:** Given a farmer's budget and chosen season, AgriAssist recommends the single best high-yield crop and variety, complete with an investment breakdown, expected profit range, risk factors, and a personalised advice paragraph.

**How it works technically:**
1. The farmer selects their farm, enters budget (INR) and season (Kharif/Rabi/Zaid).
2. The farm must be **admin-approved** before recommendations are unlocked (prevents exploiting unverified data).
3. `GraphService.get_farm_context_for_ai()` runs a Cypher spatial query to find all **neighbour farms within 10 km** and returns their soil type distribution and average farm size.
4. This "local context" is merged with the farmer's own soil/water/irrigation profile.
5. Both are sent to `GeminiService.generate_crop_recommendation()` which calls `gemini-1.5-flash` with a richly structured prompt:

```
FARMER'S FARM DATA:   soil_type, water_source, irrigation_type, area_hectares
FARMER'S PREFERENCES: season, budget (INR)
NEO4J GRAPH CONTEXT:  neighbor_count, soil_distribution, avg_neighbor_farm_size
```

6. Gemini returns a **strict JSON object** with crop name, variety, profit range, investment breakdown by category (Seeds, Fertiliser, Labour, Irrigation), risk factors, timeline, and advice.

**Technologies:** Google Gemini (`gemini-1.5-flash`), Neo4j spatial queries, SQLAlchemy, FastAPI.

**User value:** Farmers receive hyper-local, data-driven crop advice that incorporates what their neighbours are planting — not generic national recommendations.

---

### 3.5 Carbon Credit Portfolio

**What it does:** Once a farm is admin-approved, AgriAssist automatically calculates its annual carbon credit potential based on farm area, soil type, and crop type, and stores a 5-year and 10-year projected value.

**How it works technically:**

The `CarbonService.calculate_credits()` method uses research-based coefficient tables:

```
Annual Credits = Area (ha) × Crop Factor × Soil Factor × 0.8 (efficiency)
Annual Value (INR) = Credits × ₹2,200/credit
```

**Soil Factors (tonnes CO₂/ha/yr):**

| Soil Type | Factor |
|---|---|
| Black | 2.8 |
| Alluvial | 2.5 |
| Red | 2.3 |
| Laterite | 2.0 |
| Sandy | 1.5 |

**Crop Factors:** Sugarcane=1.8, Pulses=1.6, Vegetables=1.5, Cotton/Millets=1.4, Rice=1.2

Upon admin approval, the carbon calculation triggers automatically, the result is saved to `farms.carbon_credits_annual`, and the farmer's wallet (if provided) `.



**Technologies:** Python (custom formula engine)
**User value:** Farmers can see the monetary value of their environmental stewardship and receive on-chain crypto rewards, opening a new income stream previously inaccessible to smallholders.

---

### 3.6 Urban Farming Planner

**What it does:** Urban farmers (apartment residents) register a balcony, terrace, window sill, or indoor space by uploading a photo and drawing a polygon around their available planting area. Gemini Vision analyses the exact marked zone and returns a complete growing plan.

**How it works technically:**
1. The user uploads up to 3 images and draws a polygon on each using the web canvas tool. Polygon coordinates are stored as relative (0.0–1.0) x/y values.
2. On analysis trigger, `urban_gemini_service.analyse_space()`:
   - Opens each image with Pillow.
   - Calls `_draw_polygon_on_image()` which overlays a **neon-yellow polygon** on the exact marked area using `ImageDraw.polygon()` with an RGBA fill overlay.
   - Sends all annotated images + a comprehensive prompt to `gemini-2.5-flash`.
3. Gemini returns a JSON object with:
   - `estimated_area_sqm`, `sunlight_level`, `sunlight_hours_per_day`
   - `recommended_crops` (list with variety, monthly yield, difficulty, container size, days to harvest)
   - `estimated_carbon_credits_per_year` (0.06 credits/m²/yr)
   - `estimated_monthly_income_inr` (based on Mumbai/Pune market rates)
   - `soil_recommendation`, `key_tips`, `overall_suitability`
4. Results are stored as properties on a `SpaceRecord` Neo4j node.
5. A second call to `generate_planting_plan()` creates a detailed week-by-week action plan including an **SVG layout diagram** of the container arrangement.
6. All space data (SpaceRecord → PlantingPlan → GrowthLog) is stored exclusively in Neo4j, making the urban module a fully graph-native feature.

**Technologies:** Gemini Vision (`gemini-2.5-flash`), Pillow `ImageDraw`, Neo4j (graph-native storage), FastAPI.

**User value:** Any city resident receives precise, actionable gardening guidance tailored to their exact space — not a generic "grow tomatoes on your balcony" article.

---

### 3.7 Admin Dashboard with AI Agent (LangChain + Gemini Orchestrator)

**What it does:** Administrators can type natural-language questions like *"Which farmers are at risk of churning?"* or *"Show me carbon credit distribution by soil type"* and receive live, streaming answers backed by real database queries, matplotlib charts, and Gemini synthesis — with Perplexity-style "thinking" indicators.

**How it works technically — Five-Agent Architecture:**

| Agent | File | Purpose |
|---|---|---|
| Portfolio Analysis | `agent_portfolio.py` | BI report: platform KPIs, soil/crop/state distribution, top farmers, health score |
| Personalised Campaigns | `agent_personalized.py` | Cross-sell/upsell opportunities, engagement scoring, targeted messages per farmer |
| Retention Analysis | `agent_retention.py` | Churn risk scoring, at-risk farmer identification, breakthrough area strategies |
| Crop Advisor Audit | `agent_crop_advisor.py` | Quality audit of AI recommendations given, top/underperforming crops |
| Data Visualization | `agent_visualization.py` | Generates matplotlib charts (bar, pie, heatmap) encoded as base64 PNG |

**Orchestration pipeline (`GET /api/admin/chat` → SSE stream):**
1. Each agent is wrapped as a **LangChain `@tool`** with a structured description and args schema.
2. `_gemini_select_tools()` builds a tool catalogue string and asks `gemini-2.5-flash` to return a JSON array of 1–3 tool names to call.
3. Each selected tool is executed (`_execute_tool()`), with the SQLAlchemy DB session injected via `threading.local` (since LangChain tool signatures must be JSON schema-compatible).
4. Results stream as **SSE events**: `thinking` → `tool_list` → `tool_pick` → `tool_start` → `tool_done` → `chart` (base64 image) → `answer` → `done`.
5. `_synthesize_with_langchain_results()` sends all tool outputs back to Gemini for a 150–250 word final narrative.

**Technologies:** LangChain Core (`langchain-core`), LangGraph, Google Generative AI SDK (`gemini-2.5-flash`), Matplotlib, NumPy, FastAPI `StreamingResponse`.

**User value:** Admins get instant, AI-powered business intelligence from live database data — no SQL, no dashboards, just natural language.

---

### 3.8 Gamification & Smart Alerts

**What it does:** Every meaningful action a farmer takes earns points and can unlock badges. A public leaderboard encourages friendly competition. Web-based alerts notify farmers of invasive species threats in their district or state.

**How it works technically:**

**Points System:**

| Action | Points |
|---|---|
| Any plant scanned | 50 |
| Invasive plant detected | 100 |
| Invasive plant destroyed (proof photo) | +25 bonus |
| Farm mapped and document approved | 100 |
| Crop recommendation used | 20 |

**Badge System** (unlocked by cumulative points):

| Badge | Icon | Threshold |
|---|---|---|
| Early Adopter | 🌟 | Registration |
| Carbon Champion | 🍃 | 100 points |
| Knowledge Seeker | 📚 | 250 points |
| Plant Guardian | 🌿 | 500 points |
| Top Farmer | 🏆 | 1,000 points |

**Level Tiers:** Novice Planter (0–999) → Growing Cultivator (1000–2499) → Skilled Agronomist (2500–4999) → Master Harvester (5000+).

Progress percentages within each tier are computed in real-time by `GamificationService.get_user_level()`.

**Alerts** are geographically scoped — alerts carry a `district` and `state` field. Farmers in matching districts/states see relevant alerts in their in-app notification feed.

**Technologies:** SQLAlchemy (points/badges stored on `Farmer` model as JSON column), FastAPI, Jinja2 templating.

---

### 3.9 Voice Assistant (Hindi IVR + Gemini AI)

**What it does:** Farmers can call an AgriAssist Twilio number (or use the in-app web call button) and interact via a Hindi IVR menu: crop advice (1), market prices (2), weather update (3), or open-ended AI assistant (4).

**How it works technically:**
1. Twilio sends a webhook (`POST /api/voice/webhook`) with the caller's phone number.
2. The system looks up the farmer in the database and greets them by first name in Hindi using Amazon Polly's `Polly.Aditi` neural TTS voice.
3. **Menu Option 1 (Crop Guidance):** Pulls the farmer's soil type and top neighbour crops from Neo4j's `get_local_trends()` query, then asks Gemini to generate 2 Hindi sentences recommending 1-2 crops.
4. **Menu Option 2 (Market Prices):** Calls `MarketService.update_market_db()` to ensure fresh data exists, then reads the latest 5 crop prices aloud (converted to per-quintal for farmer familiarity).
5. **Menu Option 3 (Weather):** Calls Open-Meteo API (free, no key required) with the farmer's GPS coordinates from their profile, maps the WMO weather code to a condition string, and asks Gemini to generate a 2-sentence agricultural weather report in Hindi.
6. **Menu Option 4 (AI Assistant):** Uses Twilio's `<Gather input="speech">` to transcribe the farmer's spoken Hindi question, sends it to Gemini with the farmer's farm profile as context, and speaks the answer back.

**Technologies:** Twilio Voice SDK, Twilio TwiML, Amazon Polly (`Polly.Aditi`), Open-Meteo API, Google Gemini, FastAPI.

---

### 3.10 Crop Donation System

> **Transparency note:** The codebase includes a fully built `Crop` data model with `total_profit_inr`, crop varieties, and a `MarketPrice` table with live price data. The recommendation service queries profitable crops across similar soil types — which forms the foundation of a peer-to-peer donation/marketplace. The crop and market infrastructure is production-ready; a dedicated donation UI with farmer-to-farmer listing is a near-term planned feature (see Section 12: Future Roadmap).

---

## 4. System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        USER LAYER                            │
│  Rural Farmer (Web/Mobile)  │  Urban Farmer  │  Admin        │
└──────────────┬──────────────┴───────┬─────────┴──────┬────────┘
               │                     │                 │
               ▼                     ▼                 ▼
┌──────────────────────────────────────────────────────────────┐
│               FRONTEND (Jinja2 Templates + JS)               │
│  dashboard.html │ farms/index.html │ plants/scanner.html      │
│  admin/dashboard.html │ urban_farmer/dashboard.html          │
│  Leaflet.js (map) │ Canvas API (polygon drawing)             │
└───────────────────────────────┬──────────────────────────────┘
                                │  HTTP / SSE
                                ▼
┌──────────────────────────────────────────────────────────────┐
│               FASTAPI APPLICATION (app/main.py)              │
│                                                              │
│  Routers:                                                    │
│   /api/auth      /api/farms     /api/plants                  │
│   /api/recommendations          /api/admin                   │
│   /api/voice     /api/alerts    /api/gamification            │
│   /urban/space/*  (Urban Farmer module)                      │
│                                                              │
│  Middleware: CORS, JWT (python-jose), AppException handler   │
└──────┬──────────────────┬───────────────────┬───────────────┘
       │                  │                   │
       ▼                  ▼                   ▼
┌────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│  SQLite /  │  │   NEO4J GRAPH    │  │   EXTERNAL SERVICES  │
│ PostgreSQL │  │   DATABASE       │  │                      │
│            │  │                  │  │ Google Gemini API    │
│ farmers    │  │ (:Farmer)        │  │  gemini-1.5-flash    │
│ farms      │  │ (:Farm)          │  │  gemini-2.5-flash    │
│ crops      │  │ (:Plant)         │  │                      │
│ plant      │  │ (:UrbanFarmer)   │  │ Twilio              │
│ detections │  │ (:SpaceRecord)   │  │  SMS / Voice / JWT  │
│ alerts     │  │ (:PlantingPlan)  │  │                      │
│ gamific.   │  │ (:GrowthLog)     │  │                      │
│ market     │  │ (:Region)        │  │                      │
│ prices     │  │                  │  │                      │
│            │  │ Relationships:   │  │ Open-Meteo API       │
│ SQLAlchemy │  │  -[:OWNS]->      │  │  (free weather)      │
│ ORM        │  │  -[:SCANNED]->   │  │                      │
│            │  │  -[:OWNS_SPACE]->│  │ YOLOv8 (local)      │
│            │  │  -[:HAS_PLAN]->  │  │  ultralytics         │
│            │  │  -[:HAS_LOG]->   │  │  yolov8n.pt          │
│            │  │  -[:LIVES_IN]->  │  │                      │
└────────────┘  └──────────────────┘  └──────────────────────┘
```

### Layer Descriptions

| Layer | Component | Role |
|---|---|---|
| **Presentation** | Jinja2 HTML + Vanilla JS | Server-rendered pages, interactive maps, canvas polygon drawing, SSE chat UI |
| **API Gateway** | FastAPI + Uvicorn | RESTful endpoints, JWT auth middleware, streaming SSE for admin AI chat |
| **Business Logic** | `app/services/` | Domain services (GeminiService, VisionService, GraphService, CarbonService, GamificationService, etc.) |
| **AI Orchestration** | `app/services/agents/` | LangChain tool wrappers, Gemini tool router, 5-agent orchestrator with SSE streaming |
| **Relational DB** | SQLite (dev) / PostgreSQL (prod) | Transactional data — users, farms, detections, alerts, market prices, gamification events |
| **Graph DB** | Neo4j (Bolt protocol) | Spatial relationships, neighbourhood queries, urban farmer graph, plant detection network |
| **AI/Vision** | Google Gemini + YOLOv8 | Plant identification, crop recommendations, urban space analysis, voice text generation |
| **Communications** | Twilio | SMS alerts, Voice IVR (Hindi), web-based calling via Twilio Client |

---

## 5. User Flows

### 🌾 Rural Farmer Flow

```
REGISTER/LOGIN
  Phone + Password → JWT issued (24h expiry)

DASHBOARD
  View own farms (from SQL)
  View ALL farms on interactive map (GPS polygons)
  See gamification level, badges, points summary

ADD NEW FARM
  Draw polygon on map → auto-calculate area (Shapely + UTM)
  Enter soil type, water source, irrigation type
  Submit → Farm saved to SQL + Neo4j node created with GPS point
  Upload land document (PDF/JPEG/PNG) → status = "pending"

AWAIT ADMIN APPROVAL
  Admin reviews document → Approves or Rejects (with reason)
  On Approval:
    → Carbon credits auto-calculated and saved
    → 100 gamification points awarded
    → SHM reward sent to farmer wallet (if provided)

VIEW FARM DETAILS
  See carbon credit portfolio (annual credits, INR value, 5yr/10yr)
  View farm statistics and history

CROP RECOMMENDATION  [Only available after admin approval]
  Enter budget + season
  → Gemini generates personalised advice
  → Neo4j graph consulted for 10km neighbour soil/trend context
  → Returns: crop, variety, profit range, investment breakdown, risks
  → 20 gamification points awarded

PLANT SCANNER
  Upload image + GPS location
  → Engine 1: YOLOv8 → bounding boxes drawn on annotated image
  → Engine 2: Gemini Vision → species, invasiveness, treatment advice
  If invasive:
    → Plant geolocated in Neo4j
    → Spatial query finds farmers within 5km
    → Twilio SMS sent to each neighbour
  → 50/100 gamification points awarded
  → Can mark plant as destroyed → upload proof → +25 bonus points

VOICE ASSISTANT  (Twilio call or in-app web call)
  Hindi IVR:
    1 → Crop guidance (Gemini + Neo4j neighbour trends)
    2 → Market prices (live from database)
    3 → Weather update (Open-Meteo + Gemini Hindi report)
    4 → Open AI assistant (speech-to-text → Gemini → TTS)

LEADERBOARD
  Public ranking of all farmers by points
  Tier icons and badge display
```

---

### 🏙️ Urban Farmer Flow

```
REGISTER/LOGIN
  (Separate auth, stored in Neo4j as :UrbanFarmer node)
  Name, Phone, City, Ward, Housing Society, Floor, UPI ID, Aadhaar

URBAN DASHBOARD
  View all registered spaces
  See analysis status (pending_analysis / analyzed / planned)
  Market prices for crops currently in planting plans

ADD URBAN SPACE
  Provide name + space type (balcony/terrace/window_sill/indoor)
  Upload up to 3 images
  Draw polygon on each image using canvas tool
  → SpaceRecord node created in Neo4j with OWNS_SPACE relationship

TRIGGER ANALYSIS
  Click "Analyse" on a pending space
  → Yellow polygon overlay drawn on images using Pillow ImageDraw
  → Images + prompt sent to gemini-2.5-flash
  → Returns: area m², sunlight, recommended crops, carbon credits, income, tips
  → Results persisted as SpaceRecord node properties in Neo4j

GENERATE PLANTING PLAN
  Click "Generate Plan"
  → Gemini creates week-by-week schedule including:
       Planting steps (crop, action, week, description)
       Budget breakdown (Seeds, Soil, Containers, Tools)
       SVG layout diagram
       Maintenance tips
  → Plan saved as :PlantingPlan node linked to :SpaceRecord

PLANT HEALTH SCANNER
  Upload image of a balcony plant
  → Dual-engine (YOLO + Gemini) → species + health status
  → Detection logged in Neo4j

GROWTH LOG
  Add text notes + optional photo to any planting plan
  → Logged as :GrowthLog nodes linked to :PlantingPlan

AI CHAT
  Context-aware Gemini chat that knows user's spaces and plans
  Responds in Hindi or English based on user's tone
```

---

### 🛠️ Admin Flow

```
ADMIN LOGIN
  admin_id (e.g., "T12478") + password → JWT cookie (httponly, 24h)
  First admin auto-created on startup from environment variables

FARM SUBMISSIONS DASHBOARD
  View all farms across all farmers:
    - Farm name, area (ha + acres), soil type
    - Farmer name, document URL (clickable to view/download)
    - Verification status badge (pending/approved/rejected)
    - Carbon credits (calculated on approval)
    - GPS polygon overlay on mini-map

APPROVE / REJECT
  Approve triggers:
    1. Carbon credits calculated + saved to farm record
    2. Gamification: 100 points awarded to farmer
    3. Shardeum audit TX: SHA-256(farm_id + status + timestamp) recorded on-chain
    4. SHM reward: token transfer to farmer's Ethereum-compatible wallet
  Reject: MUST provide written reason → saved to farmer's verification_comments

AI AGENT CHAT  (Perplexity-style streaming)
  Type any natural language query:
    "How many farmers are at risk of becoming inactive?"
    "Show soil distribution chart"
    "Which crops are underperforming?"
  System:
    → Streams "thinking" events (real-time progress)
    → Shows all 5 available LangChain tools with icons/descriptions
    → Gemini selects 1-3 best tools
    → Executes tools, streaming "tool_start" and "tool_done" events
    → Streams base64 matplotlib charts directly as "chart" SSE events
    → Gemini synthesises 150-250 word actionable narrative
    → "done" event closes stream
```

---

## 6. Tech Stack

| Technology | Version | Why It Was Chosen |
|---|---|---|
| **Python** | 3.11+ | Primary backend language; extensive ML/AI ecosystem support |
| **FastAPI** | 0.109.0 | Async REST framework with automatic OpenAPI docs; excellent for AI/streaming |
| **Uvicorn** | 0.27.0 | High-performance ASGI server for FastAPI |
| **SQLAlchemy** | 2.0.25 | Mature ORM; supports both SQLite (dev) and PostgreSQL (prod) via `DATABASE_URL` swap |
| **SQLite** (dev) | — | Zero-configuration, file-based; perfect for hackathon-speed development |
| **PostgreSQL** (prod) | — | Scales to millions of records; supported via `psycopg2-binary` already in requirements |
| **Neo4j** | 5.16.0 (driver) | Native graph database with built-in `point()` spatial type for farm proximity queries |
| **Pydantic v2** | 2.x | Request/response validation with zero boilerplate; Pydantic-Settings for `.env` loading |
| **Google Generative AI SDK** | 0.8.6 | Official Python SDK for Gemini 1.5 Flash + 2.5 Flash multimodal models |
| **LangChain Core** | 1.2.x | Provides `@tool` decorator for structured tool metadata introspection |
| **LangGraph** | 1.1.x | Agent orchestration primitives (used for tool routing infrastructure) |
| **Ultralytics (YOLOv8)** | 8.4.21 | Industry-standard object detection; offline inference for bounding boxes |
| **OpenCV** | 4.11.0 | Image reading for YOLO; annotated image writing to disk |
| **Pillow** | 12.x | Image processing; RGBA polygon overlay for urban space analysis |
| **Shapely** | 2.0.2 | GPS polygon geometry for accurate farm area computation |
| **PyProj** | 3.6.1 | CRS reprojection (WGS-84 → UTM-43N) for metric-accurate area calculation |
| **Twilio** | 9.0.0 | SMS alert delivery + Hindi Voice IVR + web-based calling |
| **Matplotlib** | 3.10.x | Server-side chart generation for admin dashboard (bar, pie, heatmap) |
| **NumPy** | 1.26.4 | Numerical array operations for activity heatmap visualisation |
| **httpx** | 0.26.0 | Async HTTP client for Open-Meteo weather API |
| **Jinja2** | 3.1.3 | Server-side HTML templating for all page renders |
| **python-jose** | 3.3.0 | JWT token creation and verification |
| **passlib + bcrypt** | — | Password hashing for rural farmer authentication |
| **Argon2-cffi** | 23.x | Password hashing for urban farmer authentication (stored in Neo4j) |
| **python-multipart** | 0.0.6 | Multipart file upload handling (images, documents) |
| **Open-Meteo API** | — | Free real-time weather data by GPS — no API key required |
| **Leaflet.js** | — | Interactive slippy map for farm polygon drawing in browser |
| **Railway / Nixpacks** | — | Cloud deployment (`Procfile` + `railway.toml` + `nixpacks.toml` all present) |

---

## 7. AI & ML Components

### 7.1 Google Gemini Integration

AgriAssist uses **three distinct Gemini model configurations** depending on the task:

| Model | Task | Reasoning |
|---|---|---|
| `gemini-1.5-flash` | Plant identification (Vision), crop recommendations, voice text generation | Low latency; balanced cost/accuracy for high-frequency farmer-facing calls |
| `gemini-2.5-flash` | Urban space analysis, planting plan generation, urban AI chat | Larger context window handles multi-image inputs + long plan generation |
| `gemini-2.5-flash` | Admin agent tool selection and answer synthesis | Best reasoning capability for accurate tool routing and BI narrative |

#### Prompt Engineering Patterns

**JSON Forcing:** Every Gemini call that returns machine-parseable data ends with *"Return ONLY a raw JSON object (no markdown, no backticks)"*. The response handler defensively strips `\`\`\`json` fences before `json.loads()`. This pattern is applied in every one of the 6+ distinct Gemini prompt handlers.

**Contextual Grounding:** Prompts are never generic. Each includes the farmer's actual data:
- *Plant identification:* actual PIL Image bytes passed as a multimodal part
- *Crop recommendation:* farmer's soil + Neo4j neighbourhood context merged into the prompt
- *Urban analysis:* annotated JPEG bytes (with user's polygon drawn in neon yellow overlaid)
- *Voice assistant:* farmer's GPS location, soil type, neighbourhood crops from Neo4j

**Graceful Degradation:** If any Gemini call fails (network error, quota exceeded), the system falls back automatically:
- Plant scanner → uses YOLOv8 predictions
- Crop recommendation → uses generic `_get_generic_recommendations()` formula
- Voice assistant → returns a pre-written Hindi apology message

### 7.2 YOLOv8 Integration

The `VisionService` class wraps `ultralytics.YOLO` around the bundled `yolov8n.pt` model (~6.5 MB nano variant), initialized lazily on first request.

**Role in the dual-engine design:**
- YOLO runs **entirely offline** on the server — zero latency, no network call.
- It detects objects and plots bounding boxes using YOLO's `.result.plot()` which returns a BGR numpy array.
- The annotated image is saved via OpenCV `cv2.imwrite()` and served as a separate URL.
- Users see both the raw uploaded image and the AI-annotated version with bounding boxes.

**Current model limitation:** `yolov8n.pt` is the COCO-pretrained general model (80 classes: people, vehicles, animals). It is not trained on plant species or diseases. The dual-engine design compensates by using Gemini for accurate botanical classification, while YOLO provides the visual bounding-box overlay. Fine-tuning on a plant disease dataset is a roadmap priority.

### 7.3 Neo4j Graph as AI Context Engine

Neo4j is not just a database — it is the **spatial intelligence substrate** that makes crop recommendations and alerts hyper-local.

**Graph Schema (confirmed from production `neo4j_export.cypher`):**

```
(:Farmer) -[:OWNS]-> (:Farm)
(:Farmer) -[:SCANNED]-> (:Plant)
(:UrbanFarmer) -[:OWNS_SPACE]-> (:SpaceRecord)
(:SpaceRecord) -[:HAS_PLAN]-> (:PlantingPlan)
(:PlantingPlan) -[:HAS_LOG]-> (:GrowthLog)
(:UrbanFarmer) -[:LIVES_IN]-> (:Region)
```

**Spatial Query Capabilities:**
Neo4j's native `point({latitude, longitude})` type stores GPS coordinates on Farm and Plant nodes. The `point.distance()` function computes sphere-surface distance in metres, enabling sub-millisecond geospatial range queries without PostGIS or spatial indexing setup:

```cypher
-- Plant alert: find farmers within 5km
point.distance(plant.location, farm.location) < 5000

-- Crop recommendation: find neighbour soil distribution within 10km
point.distance(target.location, neighbor.location) < 10000
```

**Key usage locations:**
- `find_nearby_farmers()` — Alert radius for invasive species (5 km)
- `get_farm_context_for_ai()` — Neighbourhood soil/size context for Gemini crop prompt (10 km)
- `get_local_trends()` — Popular crops scanned/planted by nearby farmers (10 km)

### 7.4 LangChain + Gemini Admin Agent Architecture

The admin AI system (`agent_orchestrator.py`) implements a **hybrid tool-routing pattern**:

```
LangChain @tool  →  provides structured JSON schema (name, description, args)
         +
Gemini 2.5 Flash  →  reads tool catalogue, selects 1-3 tools, returns JSON array
         +
Python thread executor  →  invokes LangChain .invoke() on selected tools
         +
Gemini synthesis  →  reads all tool outputs, writes 150-250 word narrative
         +
FastAPI StreamingResponse (SSE)  →  streams every step as JSON events
```

This architecture was specifically designed to avoid the `langchain-google-genai` package (not available in the production environment) while preserving LangChain's benefit of structured tool introspection.

**Five Admin Agent Capabilities:**

| Agent | What It Analyses | Output |
|---|---|---|
| Portfolio | All farmers, farms, soil distribution, carbon credits, top users | Health score 0-100, executive summary, KPIs |
| Personalized | Engagement scoring per farmer, feature adoption gaps | Named campaign suggestions per farmer |
| Retention | Login recency, activity frequency, inactivity patterns | At-risk farmers list, breakthrough areas map |
| Crop Advisor | Recommendation quality, profit/loss ratio by crop | Advisory quality score, best/worst crops |
| Visualization | All live database data | 6 chart types: soil bar, carbon pie, verification pie, activity heatmap, top-farmers bar, land distribution pie |

---

## 8. Data Flow

### 8.1 Invasive Species Detection → Community Alert

```
Farmer uploads image + GPS
    │
    ▼
POST /api/plants/identify
    │
    ├── 1. Validate image size (max 10MB) + compress via Pillow
    │
    ├── 2. VisionService.scan_plant(image_path, output_dir)  [YOLOv8 offline]
    │       └─ Bounding boxes drawn → annotated_image saved to disk
    │
    ├── 3. GeminiService.identify_plant(image_bytes)  [Gemini Vision cloud]
    │       └─ Returns JSON: {species, is_invasive, threat_level, confidence, ...}
    │
    ├── 4. PlantDetection record saved to SQLite
    │
    ├── 5. GamificationService.add_points() → SQLite commit
    │       └─ Check for new badges based on total points
    │
    ├── 6. GraphService.create_detection_record()  [Neo4j]
    │       └─ MERGE Farmer node
    │       └─ CREATE Plant node
    │       └─ MERGE (Farmer)-[:SCANNED]->(Plant)
    │       └─ SET Plant.location = point({lat, lon})
    │
    └── 7. IF is_invasive AND GPS coords present:
            GraphService.find_nearby_farmers()  [Neo4j spatial query]
            └─ Returns [{phone, distance_km}, ...]
            │
            └─ FOR EACH neighbor:
                 Twilio.messages.create(
                   body="⚠️ [Species] [Nkm] near your farm!",
                   to="+91{phone}",
                   from_=TWILIO_PHONE_NUMBER
                 )

HTTP Response: {status, detection, gamification, neighbors_alerted: N}
```

### 8.2 Admin Chat Query → Streamed Answer

```
Admin types: "Show me which soils have the highest carbon credit potential"
    │
    ▼
GET /api/admin/chat?query=... → FastAPI StreamingResponse (SSE)
    │
    ▼
stream_orchestrator(query, db)  [async generator]
    │
    ├── EMIT: {type:"thinking", text:"Received query..."}
    ├── EMIT: {type:"tool_list", tools:[5 tools with icons, descriptions]}
    │
    ├── _gemini_select_tools(query)  [Gemini 2.5 Flash]
    │     └─ Reads LangChain tool catalogue
    │     └─ Returns: [{"tool_name":"data_visualization_tool", "args":{"chart_query":"..."}}]
    │
    ├── EMIT: {type:"tool_pick", selected:[...]}
    │
    ├── loop.run_in_executor → _execute_tool("data_visualization_tool", args, db)
    │     └─ run_visualization_agent(db, query)
    │           └─ Gemini picks chart IDs from catalogue
    │           └─ Matplotlib → bar chart, pie chart → base64 PNG strings
    │           └─ Returns {charts:[...], ai_narrative}
    │
    ├── EMIT: {type:"tool_done", summary:"2 charts generated"}
    ├── EMIT: {type:"chart", label:"Carbon Credits by Soil Type", image:"data:image/png;..."}
    │
    ├── _synthesize_with_langchain_results(query, all_results)  [Gemini]
    │     └─ Reads all tool outputs → 150-250 word actionable narrative
    │
    ├── EMIT: {type:"answer", text:"Based on the analysis..."}
    └── EMIT: {type:"done"}
```

### 8.3 Urban Space Analysis Data Flow

```
User draws polygon on balcony photo, submits form
    │
    ▼
POST /urban/space/submit
  - Images saved to uploads/urban_spaces/{space_id}_{uuid}.ext
  - Neo4j: CREATE SpaceRecord node, MERGE OWNS_SPACE relationship
  - Status: "pending_analysis"
    │
    ▼
POST /urban/space/{space_id}/analyze   [user-triggered]
  For each image:
    1. Open with Pillow → convert to RGB
    2. Draw user's polygon as neon-yellow RGBA overlay (ImageDraw)
    3. Convert annotated image to JPEG bytes (in-memory BytesIO)
  Send [prompt_text + all annotated image bytes] to gemini-2.5-flash
    │
    ▼
Gemini returns JSON analysis
  {area_sqm, sunlight_level, recommended_crops[], carbon, income, tips...}
    │
    ▼
Neo4j: SET SpaceRecord properties from analysis, status = "analyzed"
    │
    ▼
POST /urban/space/{space_id}/plan   [user-triggered]
  Send analysis context back to Gemini → generate planting plan
    │
    ▼
Neo4j: CREATE PlantingPlan node
       CREATE (SpaceRecord)-[:HAS_PLAN]->(PlantingPlan)
       SET SpaceRecord.status = "planned"
```

---

## 9. Innovation & Originality

### What Makes AgriAssist Unique

| Innovation | Description |
|---|---|
| **Geo-fenced community alert mesh** | The combination of Neo4j spatial queries + Twilio SMS creates a real-time, automated community protection network for invasive species — no existing Indian agri-app does this. |
| **Dual-engine plant scanner** | Cascading offline YOLO (visual bounding boxes) + cloud Gemini Vision (botanical taxonomy + treatment advice) — combining speed, visual output, and semantic precision. |
| **Neo4j as AI context** | Crop recommendations are grounded in graph data from neighbouring farms (soil, trend, size) within 10 km — making advice genuinely hyperlocal rather than nationally generic. |
| **Polygon-anchored urban space analysis** | Drawing the user's selection as a neon-yellow overlay on the photo before sending to Gemini forces the model to analyse exactly the right region — a novel prompt-engineering + image-preprocessing technique. |
| **Perplexity-style admin AI with live charts** | The SSE-streaming orchestrator that shows tool selection, execution, and matplotlib chart generation in real time creates an admin experience that no agricultural SaaS has shipped. |
| **LangChain + Gemini hybrid routing** | Using LangChain `@tool` schemas for introspection while using the bare Gemini SDK for routing decisions solves a real production compatibility problem elegantly. |
| **Carbon credits for smallholders** | Making the carbon market accessible to <2 ha farmers via an automated formula engine, with on-chain verification via Shardeum, democratises a previously elite financial instrument. |

| **Hindi-native voice interface** | Polly.Aditi neural TTS + Gemini for Hindi agricultural context generation creates a genuinely useful IVR for farmers with low smartphone literacy — not a translated English UI. |
| **Fully graph-native urban module** | Urban farmer data (spaces, plans, logs) is stored entirely in Neo4j graph nodes, not SQL tables — making the module architecturally distinct and optimised for relationship traversal. |

---

## 10. Real-World Impact & Feasibility

### Target Users & Potential Reach

| User Segment | India Population | Platform Fit |
|---|---|---|
| Rural marginal farmers (< 2 ha) | ~86 million households | Farm mapping, crop recommendations, plant scanner, voice IVR in Hindi |
| Rural smallholders (2-5 ha) | ~14 million households | Full feature usage including carbon credit portfolio |
| Urban balcony/terrace farmers | ~50 million urban households (growing segment) | Urban Farming Planner module |
| District agricultural authorities | ~700 districts | Admin AI dashboard for policy intelligence |

### Feasibility Assessment

| Dimension | Status |
|---|---|
| **Technical readiness** | All core features implemented. Neo4j export confirms real farmer data (Thane district, Maharashtra). Railway/Render deployment files present. |
| **API cost estimate (1,000 users/month)** | Gemini free tier: large quota; Twilio SMS: ~₹1.50/message; Open-Meteo: free; Shardeum: ~₹0.001/TX; Total infra: < ₹8,000/month |
| **Language expansion** | Gemini supports 40+ languages. Marathi, Tamil, Telugu support requires a single `language` parameter change in prompts. |
| **Farm verification** | Aadhaar-linked document upload + admin approval + on-chain record creates a credible KYC chain for government integration. |
| **Offline resilience** | Voice IVR (Twilio) requires only a 2G phone call — no smartphone, no app, no internet required for the farmer. |
| **Sensor readiness** | `Farmer.latitude` and `Farmer.longitude` fields already support GPS. IoT sensor integration requires only a data ingest endpoint. |

---

## 11. Challenges & How They Were Solved

| Challenge | Solution |
|---|---|
| **Accurate farm area from browser GPS** | GPS lat/lon degrees cannot be used for area calculation (1° longitude ≠ constant metres). Solved by reprojecting WGS-84 → UTM Zone 43N (EPSG:32643) with PyProj before Shapely polygon area computation. |
| **Gemini returning Markdown-wrapped JSON** | Gemini occasionally wraps JSON in ` ```json ``` ` fences despite instructions. Solved by defensive stripping of both ` ```json ` and ` ``` ` prefixes/suffixes before `json.loads()` — applied in all 6+ Gemini handlers. |
| **LangChain without `langchain-google-genai`** | The Google-backed LangChain integration package wasn't available in the target environment. Solved by using LangChain `@tool` purely for structured metadata, routing via bare `google-generativeai` SDK — achieving both frameworks' strengths. |
| **Urban farmer graph storage vs SQL** | Urban farmers have fundamentally different data models with deep relationships that don't fit relational tables cleanly. Solved by making the entire urban module Neo4j-native (UrbanFarmer → SpaceRecord → PlantingPlan → GrowthLog), separating the two user journeys architecturally. |
| **Gemini Vision analysing wrong image region** | Without anchoring, Gemini might focus on background walls or sky rather than the planting zone. Solved by drawing the user's polygon as a neon-yellow RGBA overlay on the JPEG before sending — forcing visual attention to the correct area. |
| **Geospatial SMS alerts without PostGIS** | SQL `BETWEEN` queries on lat/lon are inaccurate (great-circle distance ≠ rectangular box). Solved by storing plant GPS as Neo4j native `point()` properties and using `point.distance()` for precise sphere-surface distance calculations. |
| **Dual authentication systems** | Rural farmers authenticate via SQL/JWT; urban farmers via Neo4j/Argon2id. Solved by parallel auth routers with separate `get_current_user` and `get_current_urban_farmer` FastAPI dependencies — zero coupling. |

| **Carbon credit gaming** | Farmers could claim credits without verified land. Solved by hard server-side gating: both `calculate-carbon` and `advise` endpoints check `farm.verification_status == "approved"` and return HTTP 403 otherwise. |
| **Market price freshness** | Hardcoded prices go stale. Solved with `MarketService.update_market_db()` which checks for today's records before inserting — called on-demand during the voice IVR "market prices" menu option, ensuring callers always hear fresh data. |

---

## 12. Future Roadmap

| Priority | Feature | Description |
|---|---|---|
| 🔴 High | **Fine-tuned YOLO model** | Train YOLOv8 on curated dataset of Indian invasive species (Parthenium, Lantana, Prosopis) and crop diseases (blight, rust, mildew) — replacing the generic COCO model |
| 🔴 High | **WhatsApp alerts** | Add WhatsApp Business API alongside Twilio SMS — higher open rates, richer media support (images, location pins, interactive buttons) |
| 🔴 High | **Crop Donation/Marketplace** | Complete the farmer-to-farmer surplus produce listing UI — infrastructure (crop/market tables) already production-ready in SQL |
| 🟡 Medium | **Mobile App (React Native)** | Native Android/iOS app. The FastAPI backend is already API-first and decoupled from the frontend |
| 🟡 Medium | **Agmarknet live prices** | Replace simulated market prices with live data from the Government of India Agmarknet commodity price API |
| 🟡 Medium | **Multi-language support** | Extend voice IVR and Gemini prompts to Marathi, Tamil, Telugu, Kannada — `Farmer.language_preference` field already in the schema |
| 🟡 Medium | **Disease spread forecasting** | Use historical Neo4j detection data to train a time-series model predicting when/where diseases will spread next season |
| 🟢 Low | **IoT sensor integration** | Connect soil moisture, pH, and temperature sensors to farm profiles via MQTT — `Farmer.latitude/longitude` already support GPS localisation |
| 🟢 Low | **NGO / Government data API** | Expose an anonymised geospatial API for district-level agricultural planning, with farmer consent management |
| 🟢 Low | **Carbon credit marketplace** | Partner with Verra/Gold Standard to allow farmers to sell calculated credits through the platform — Shardeum wallet infrastructure already built |

---

## Appendix A: API Endpoint Summary

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/auth/register` | POST | — | Register new rural farmer |
| `/api/auth/login` | POST | — | Login → JWT token |
| `/api/auth/me` | GET | Farmer JWT | Current user profile |
| `/api/farms/` | POST | Farmer JWT | Create farm (polygon + soil) |
| `/api/farms/` | GET | Farmer JWT | List farmer's farms |
| `/api/farms/all` | GET | Farmer JWT | All farm polygons (map view) |
| `/api/farms/{id}` | GET | Farmer JWT | Farm detail |
| `/api/farms/{id}/document` | POST | Farmer JWT | Upload land document |
| `/api/farms/{id}/calculate-carbon` | POST | Farmer JWT | Carbon credits (approved only) |
| `/api/farms/{id}/advise` | POST | Farmer JWT | AI crop recommendation (approved only) |
| `/api/plants/identify` | POST | Farmer JWT | Upload image → dual scan + alerts |
| `/api/plants/history` | GET | Farmer JWT | Detection history |
| `/api/plants/{id}/mark-destroyed` | POST | Farmer JWT | Mark invasive plant destroyed |
| `/api/recommendations/` | POST | Farmer JWT | Standalone crop recommendations |
| `/api/alerts/` | GET | Farmer JWT | Geo-scoped farmer alerts |
| `/api/gamification/leaderboard` | GET | Farmer JWT | Top farmers by points |
| `/api/gamification/my-stats` | GET | Farmer JWT | Personal points/badges/level |
| `/api/voice/token` | GET | Farmer JWT | Twilio web call token |
| `/api/voice/webhook` | POST | — | Twilio IVR webhook |
| `/api/admin/login` | POST | — | Admin login |
| `/api/admin/dashboard` | GET | Admin JWT | All farms with verification |
| `/api/admin/farms/{id}/verify` | POST | Admin JWT | Approve/Reject farm doc |
| `/api/admin/chat` | GET | Admin JWT | Streaming AI agent chat (SSE) |
| `/api/admin/agents/*` | GET | Admin JWT | Individual agent endpoints |
| `/urban/auth/register` | POST | — | Urban farmer registration |
| `/urban/auth/login` | POST | — | Urban farmer login |
| `/urban/space/submit` | POST | Urban JWT | Submit space + images + polygons |
| `/urban/space/{id}/analyze` | POST | Urban JWT | Gemini Vision analysis |
| `/urban/space/{id}/plan` | POST | Urban JWT | Generate planting plan |
| `/urban/space/chat` | POST | Urban JWT | Context-aware AI garden chat |
| `/urban/space/scan/disease` | POST | Urban JWT | Plant disease scan |

---

## Appendix B: Environment Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Yes | — | JWT signing secret |
| `GEMINI_API_KEY` | Yes | — | Google AI Studio API key |
| `NEO4J_URI` | Yes | `bolt://localhost:7687` | Neo4j Bolt URI |
| `NEO4J_PASSWORD` | Yes | — | Neo4j database password |
| `DATABASE_URL` | No | `sqlite:///./agritech.db` | Relational DB (swap to PostgreSQL for prod) |
| `TWILIO_ACCOUNT_SID` | Optional | — | Enable SMS/Voice features |
| `TWILIO_AUTH_TOKEN` | Optional | — | Enable SMS/Voice features |
| `TWILIO_PHONE_NUMBER` | Optional | — | Sender number for SMS alerts |
| `TWILIO_API_KEY` | Optional | — | Web-based calling |
| `TWILIO_TWIML_APP_SID` | Optional | — | Web-based calling |


