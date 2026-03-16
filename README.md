# Nexus AI – Telegram Illegal Trade Intelligence Agent

Nexus AI is a **3‑agent system** that monitors **public Telegram channels** to detect coded illegal trade (crypto pump‑and‑dump, scams, drugs) using semantic analysis instead of simple keyword matching.

> For research/demo use only. Use only on **public** channels and always comply with laws and platform policies.

---

## 🔍 Core Idea

Criminals constantly change slang (e.g., `snow → white → white girl`), so keyword‑based and static ML systems quickly become useless.

Nexus AI:
- Automatically discovers suspicious Telegram channels  
- Understands **semantic meaning** of messages using embeddings + clustering  
- Detects **new slang** via cluster/centroid drift  
- Surfaces **key organizers (kingpins)** instead of just suspicious messages

---

## 🧠 3‑Agent Workflow

### 1️⃣ Agent 1 – Channel Hunter
- Searches public Telegram channels using threat‑related terms (e.g., "crypto signals", "pump", "fixed match").  
- Filters channels by member count, message volume, and freshness.  
- Sends selected channels to the processing pipeline.

### 2️⃣ Agent 2 – Semantic Linguist
- Fetches recent messages from each channel.  
- Cleans text and embeds it with a sentence transformer.  
- Clusters embeddings with **HDBSCAN** and detects **evolving slang** by monitoring centroid drift.  
- Optionally sends new slang patterns to a human‑in‑the‑loop for validation and updates the slang knowledge.

### 3️⃣ Agent 3 – Threat Intelligence Brain
- Uses an LLM to score each cluster for likelihood of illegal activity.  
- Builds a **graph** of users, channels, and messages to find **central/kingpin accounts**.  
- Outputs structured alerts and summaries that can be consumed by dashboards or existing SOC / investigation tools.

---

## ▶️ End‑to‑End Flow

1. Agent 1 discovers and selects suspicious public channels.  
2. Agent 2 embeds and clusters messages, learning new slang over time.  
3. Agent 3 scores risk, finds organizers, and produces alerts/evidence.

Nexus AI is designed to plug in as an **intelligence layer** on top of existing security and investigation systems.

---

## 🎥 Demo Video

Watch the full demo and walkthrough:

[![Nexus AI Demo](https://img.youtube.com/vi/KAX3dJXgsoA/0.jpg)](https://www.youtube.com/watch?v=KAX3dJXgsoA)

**[▶️ Watch on YouTube](https://www.youtube.com/watch?v=KAX3dJXgsoA)**

---

## 🚀 Live Deployment
