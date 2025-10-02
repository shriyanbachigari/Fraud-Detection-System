# Fraud Detection System

Small end-to-end demo I built to stream fake transactions through Kafka, score them with a simple model, and show live fraud alerts in a tiny dashboard.

## What’s inside

- Producer (Python): publishes fake transactions to Kafka (`transactions` topic)
- Consumer (Java/Spring Boot): reads events, computes a few features, calls the model API, writes to Postgres, streams alerts over SSE
- Model API (Python/FastAPI): loads a trained model + a decision threshold and returns fraud probability + is_fraud
- Redis: tracks short-term velocity and novelty (new country/device)
- Postgres: stores transactions and fraud flags
- Kafka (single broker): message bus

Ports I use locally:
- Dashboard (consumer): http://localhost:8081/
- Model API: http://localhost:8000/health
- Postgres: localhost:5432 (frauddb)
- Redis: localhost:6379
- Kafka: localhost:9092

## Quick start (Docker)

```powershell
docker compose up -d --build
```

Give it ~10–20 seconds. Then:

- Dashboard: open http://localhost:8081/ (live fraud alerts)
- Model health: 
	```powershell
	curl.exe http://localhost:8000/health
	```
- Quick DB check:
	```powershell
	docker compose exec postgres psql -U fraud_user -d frauddb -c "SELECT COUNT(*) AS txns FROM transactions; SELECT COUNT(*) AS flags FROM flags;"
	```

If flags is > 0, the stream should start showing rows shortly.

## How it decides “fraud”

The consumer uses a mix of model + simple rules:
- Ask model: probability + is_fraud (based on a threshold)
- Also flag if:
	- velocity (last 60s per user) > 8, or
	- new country + new device + amount > 500, or
	- new country + amount > 1000

Features sent to the model:
- amount
- hour (UTC)
- country_novelty (0/1)
- device_novelty (0/1)
- user_velocity_60s (int)

