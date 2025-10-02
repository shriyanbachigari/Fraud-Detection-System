from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np
import logging
import os
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Fraud Detection API")

try:
    model = joblib.load("model.pkl")
    logger.info("model loaded")
except Exception as e:
    logger.error(f"failed to load model: {e}")
    model = None

# Load decision threshold from file or env (fallback default)
DEFAULT_THRESHOLD = 0.98
THRESHOLD = DEFAULT_THRESHOLD
try:
    tf = Path(__file__).with_name("threshold.json")
    if tf.exists():
        THRESHOLD = float(json.loads(tf.read_text()).get("threshold", DEFAULT_THRESHOLD))
    else:
        THRESHOLD = float(os.getenv("MODEL_THRESHOLD", str(DEFAULT_THRESHOLD)))
    logger.info(f"threshold={THRESHOLD}")
except Exception as e:
    logger.warning(f"Failed to load threshold, using default {DEFAULT_THRESHOLD}: {e}")
    THRESHOLD = DEFAULT_THRESHOLD

class TransactionFeatures(BaseModel):
    amount: float
    hour: int
    country_novelty: int
    device_novelty: int
    user_velocity_60s: int

class FraudScore(BaseModel):
    fraud_probability: float
    is_fraud: bool
    confidence: str

@app.post("/score", response_model=FraudScore)
async def score_transaction(features: TransactionFeatures):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not available")
    
    try:
        # Prepare features (need to match training: amount, hour, new_country, new_device, velocity, amount_zscore, is_night)
        amount_zscore = (features.amount - 100) / 200  # Rough normalization
        is_night = 1 if features.hour >= 23 or features.hour <= 5 else 0
        
        feature_array = np.array([[
            features.amount,
            features.hour,
            features.country_novelty,
            features.device_novelty,
            features.user_velocity_60s,
            amount_zscore,
            is_night
        ]])
        # Get fraud probability
        fraud_prob = float(model.predict_proba(feature_array)[0][1])

        # Decision using configured threshold (calibrated or env/default)
        is_fraud = fraud_prob >= THRESHOLD

        # Confidence levels
        if fraud_prob > 0.80:
            confidence = "high"
        elif fraud_prob > 0.50:
            confidence = "medium"
        else:
            confidence = "low"
        
        return FraudScore(
            fraud_probability=fraud_prob,
            is_fraud=is_fraud,
            confidence=confidence
        )
        
    except Exception as e:
        logger.error(f"scoring error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "threshold": THRESHOLD
    }

@app.get("/")
async def root():
    return {"message": "Fraud Detection API - ready to score transactions"}