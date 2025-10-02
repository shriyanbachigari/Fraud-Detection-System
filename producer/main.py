from faker import Faker
import json
import os
import random
import time
from datetime import datetime, timezone
from confluent_kafka import Producer as KProducer
from confluent_kafka.admin import AdminClient, NewTopic

BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TOPIC = os.getenv("TXN_TOPIC", "transactions")
TPS = int(os.getenv("TPS", "100"))
FRAUD_RATE = float(os.getenv("FRAUD_RATE", "0.02"))

fake = Faker()

COUNTRIES = ["US", "IN", "GB", "CA", "DE", "SG"]
USER_IDS = [f"u{n:05d}" for n in range(2000)]  # fewer users so features stabilize per user

# Stable user profile: persistent device and home country per user during container lifetime
USER_PROFILES = {
    uid: {
        "device_id": fake.md5(raw_output=False),
        "home_country": random.choice(COUNTRIES),
    }
    for uid in USER_IDS
}

def maybe(percent: float) -> bool:
    return random.random() < percent

def generateFake():
    user = random.choice(USER_IDS)
    profile = USER_PROFILES[user]

    # Base amount distribution
    amount = abs(random.gauss(40, 20))

    # Decide fraud upfront to perturb features realistically
    is_fraud = random.random() < FRAUD_RATE
    if is_fraud:
        amount *= random.uniform(5, 20)

    # Country behavior: mostly stable, rare change; higher chance to change when fraudulent
    if is_fraud and maybe(0.50):
        country = random.choice([c for c in COUNTRIES if c != profile["home_country"]])
    elif maybe(0.03):  # legit small drift
        country = random.choice([c for c in COUNTRIES if c != profile["home_country"]])
    else:
        country = profile["home_country"]

    # Device behavior: mostly stable, rare change; higher chance to change when fraudulent
    if is_fraud and maybe(0.60):
        device_id = fake.md5(raw_output=False)
    elif maybe(0.02):  # legit device change (new device)
        device_id = fake.md5(raw_output=False)
        # Optionally update profile to simulate user keeps new device
        USER_PROFILES[user]["device_id"] = device_id
    else:
        device_id = profile["device_id"]

    return {
        "txn_id": f"t{int(time.time()*1000)}{random.randint(0,9999):04d}",
        "user_id": user,
        "amount": round(amount, 2),
        "currency": "USD",
        "country": country,
        "device_id": device_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "label": int(is_fraud),
    }

def delivery_report(err, msg):
    if err is not None:
        print(f'Message delivery failed: {err}')

if __name__ == "__main__":
    print(f"connecting to kafka at {BROKER}")
    
    # Create admin client to check connection
    admin_client = AdminClient({'bootstrap.servers': BROKER})
    
    retry_count = 0
    while retry_count < 30:
        try:
            metadata = admin_client.list_topics(timeout=5)
            print(f"connected to kafka, topics={len(metadata.topics)}")
            break
        except Exception as e:
            retry_count += 1
            time.sleep(2)
    
    if retry_count >= 30:
        print("failed to connect to kafka")
        exit(1)
    
    # Create topic if it doesn't exist
    # refresh metadata before checking topic existence
    metadata = admin_client.list_topics(timeout=5)
    if TOPIC not in metadata.topics:
        topic = NewTopic(TOPIC, num_partitions=1, replication_factor=1)
        fs = admin_client.create_topics([topic])
        for topic_name, f in fs.items():
            try:
                f.result()
                print(f"created topic: {topic_name}")
            except Exception as e:
                print(f"topic exists or creation failed: {e}")
    
    # Create producer
    producer = KProducer({
        'bootstrap.servers': BROKER,
        'compression.type': 'snappy',
        'linger.ms': 10,
        'batch.size': 16384
    })
    
    print(f"starting producer: {TPS} tps, {FRAUD_RATE*100}% fraud rate")
    batch_count = 0
    
    while True:
        start = time.time()
        for _ in range(TPS):
            txn = generateFake()
            producer.produce(
                TOPIC, 
                value=json.dumps(txn).encode('utf-8'),
                callback=delivery_report
            )
        producer.flush()
        batch_count += 1
        
        if batch_count % 10 == 0:
            print(f"sent {batch_count * TPS} transactions")
        
        time.sleep(max(0, 1 - (time.time() - start)))
