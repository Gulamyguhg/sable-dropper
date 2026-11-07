FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    openjdk-17-jdk-headless \
    wget unzip \
    && rm -rf /var/lib/apt/lists/*

RUN wget -q https://github.com/iBotPeaches/Apktool/releases/download/v2.9.3/apktool_2.9.3.jar -O /usr/local/bin/apktool.jar \
    && printf '#!/bin/sh\nexec java -jar /usr/local/bin/apktool.jar "$@"\n' > /usr/local/bin/apktool \
    && chmod +x /usr/local/bin/apktool

RUN wget -q https://dl.google.com/android/repository/build-tools_r34-linux.zip \
    && unzip -q build-tools_r34-linux.zip -d /opt/android \
    && cp /opt/android/android-14/zipalign /usr/local/bin/ \
    && cp /opt/android/android-14/apksigner /usr/local/bin/ \
    && cp /opt/android/android-14/lib/apksigner.jar /usr/local/bin/ 2>/dev/null || true

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

CMD gunicorn -b 0.0.0.0:$PORT app:app
