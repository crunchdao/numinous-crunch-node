uvicorn numinous.gateway.app:app \
  --host 0.0.0.0 \
  --port 8090 \
  --log-level info \
  --log-config /app/log_config.json \
  2>&1 | tee -a /app/logs/gateway.log
