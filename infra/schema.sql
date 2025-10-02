CREATE TABLE IF NOT EXISTS transactions (
  txn_id       VARCHAR PRIMARY KEY,
  user_id      VARCHAR NOT NULL,
  amount       NUMERIC(12,2) NOT NULL,
  currency     VARCHAR(3) NOT NULL,
  country      VARCHAR(2) NOT NULL,
  device_id    VARCHAR NOT NULL,
  timestamp    TIMESTAMP NOT NULL,
  features_json TEXT
);

CREATE TABLE IF NOT EXISTS flags (
  id           BIGSERIAL PRIMARY KEY,
  txn_id       VARCHAR REFERENCES transactions(txn_id),
  score        DOUBLE PRECISION,
  label_pred   BOOLEAN,
  reasons_json TEXT,
  timestamp    TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_flags_txn ON flags(txn_id);
CREATE INDEX IF NOT EXISTS idx_txn_user_ts ON transactions(user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_flags_ts ON flags(timestamp);
