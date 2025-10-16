# Use an official lightweight Ubuntu image
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/lib/chromium-browser"

# Update and install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libgbm1 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxrender1 \
    libxcursor1 \
    libxi6 \
    libxtst6 \
    libappindicator3-1 \
    xdg-utils \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Manually download and install Google Chrome 114.0.5735.90
RUN wget -q -O google-chrome.deb "https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_114.0.5735.90-1_amd64.deb" \
    && dpkg -i google-chrome.deb || apt-get -fy install \
    && rm google-chrome.deb

# Install ChromeDriver 114.0.5735.90
RUN wget -q https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm chromedriver_linux64.zip

# Install Python dependencies
RUN pip3 install --no-cache-dir \
    selenium==4.9.1 \
    webdriver-manager \
    argparse

# Verify installations
RUN which google-chrome && google-chrome --version \
    && which chromedriver && chromedriver --version \
    && python3 -c "import selenium; print('Selenium Installed:', selenium.__version__)"

# Set working directory
WORKDIR /app

# Copy script to container
COPY take_screenshot.py /app/take_screenshot.py

# Set default command to run the script
ENTRYPOINT ["python3", "/app/take_screenshot.py"]
