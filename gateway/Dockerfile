FROM python:3.12-slim

EXPOSE 8090
COPY ./run.sh /

WORKDIR /app
COPY ./log_config.json .

RUN pip install --no-cache-dir "crunch-numinous>=0.5.0"

CMD ["sh", "/run.sh"]
