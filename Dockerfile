FROM python:3.10

# Systempakete für Chrome
RUN apt-get update && apt-get install -y wget unzip xvfb libxi6 libgconf-2-4 libnss3 libxss1 libappindicator1 fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 libnspr4 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 xdg-utils


# Chrome installieren
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    dpkg -i google-chrome-stable_current_amd64.deb || apt-get -fy install

# Python requirements
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

CMD ["python", "termin_backend.py"]
