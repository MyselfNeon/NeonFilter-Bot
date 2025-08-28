FROM python:3.10.8-slim-bullseye

# Update system and install git
RUN apt update && apt upgrade -y
RUN apt install git -y

# Copy Python dependencies and install
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -U pip
RUN pip install --no-cache-dir -U -r /requirements.txt
RUN pip install --no-cache-dir edge-tts

# Create custom working directory
RUN mkdir /Neon-Bot
WORKDIR /Neon-Bot

# Copy bot code into working directory
COPY . /Neon-Bot

# Run the bot
CMD ["python", "bot.py"]

