FROM python:3.10.8-slim-bullseye

# Ensure system tools are available and up to date
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies and install
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -U pip
RUN pip install --no-cache-dir -U -r /requirements.txt
RUN pip install --no-cache-dir edge-tts

# Create working directory
WORKDIR /Neon-Bot
COPY . .

# Run the bot
CMD ["python", "bot.py"]
