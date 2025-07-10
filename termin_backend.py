from flask import Flask, jsonify
import threading
import time
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta

app = Flask(__name__)

URL = "https://www.duisburg.de/allgemein/fachbereiche/90/terminvereinbarung-buergerservice.php"
aktuelle_termine = []
neu_gefunden = False

def format_datum(tag, monat, jahr):
    return f"{jahr}-{int(monat)+1:02d}-{int(tag):02d}"

def ist_in_den_naechsten_7_tagen(datum_str):
    datum = datetime.strptime(datum_str, "%Y-%m-%d").date()
    heute = datetime.today().date()
    return heute <= datum <= heute + timedelta(days=7)

def termine_unterschiede(old, new):
    # Einfacher Vergleich: Termine mit Datum und Zeiten
    old_set = {(t['datum'], tuple(t['zeiten'])) for t in old}
    new_set = {(t['datum'], tuple(t['zeiten'])) for t in new}
    return not new_set.issubset(old_set)  # Wenn neue Termine da sind

def finde_termine():
    global aktuelle_termine, neu_gefunden
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get(URL)

        wait = WebDriverWait(driver, 20)
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, "iframe")))

        wait.until(EC.element_to_be_clickable((By.ID, "sg46564txt"))).click()
        time.sleep(1)

        wait.until(EC.element_to_be_clickable((By.ID, "90496"))).click()
        time.sleep(1)

        wait.until(EC.element_to_be_clickable((By.ID, "bp1"))).click()

        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "table.ui-datepicker-calendar")))

        monat_value = driver.find_element(By.CSS_SELECTOR, "select.ui-datepicker-month option[selected]").get_attribute("value")
        jahr_text = driver.find_element(By.CSS_SELECTOR, ".ui-datepicker-year").text.strip()

        tage = driver.find_elements(By.CSS_SELECTOR, "table.ui-datepicker-calendar td.dayA a.ui-state-default")
        alle_termine = []

        for i in range(len(tage)):
            tage = driver.find_elements(By.CSS_SELECTOR, "table.ui-datepicker-calendar td.dayA a.ui-state-default")
            tag_link = tage[i]
            tag_text = tag_link.get_attribute("data-date")

            datum_str = format_datum(tag_text, monat_value, jahr_text)

            if not ist_in_den_naechsten_7_tagen(datum_str):
                continue

            try:
                wait.until(EC.invisibility_of_element_located((By.ID, "loader")))
                tag_link.click()
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.timeslot")))
            except:
                continue

            freie_zeiten = driver.find_elements(By.CSS_SELECTOR, "li.timeslot")
            termine_text = [z.text.strip() for z in freie_zeiten if z.text.strip()]

            if termine_text:
                alle_termine.append({"datum": datum_str, "zeiten": termine_text})

        # Prüfe auf neue Termine
        if termine_unterschiede(aktuelle_termine, alle_termine):
            neu_gefunden = True
        else:
            neu_gefunden = False

        aktuelle_termine = alle_termine
        driver.quit()

    except Exception as e:
        print("Fehler beim Terminprüfen:", e)
        aktuelle_termine = []
        neu_gefunden = False

@app.route('/termine')
def api_termine():
    return jsonify(aktuelle_termine)

@app.route('/has_new')
def api_has_new():
    global neu_gefunden
    # Nach Abfrage das Flag zurücksetzen (optional)
    gefunden = neu_gefunden
    neu_gefunden = False
    return jsonify({"neu": gefunden})

@app.route('/')
def home():
    return "✅ Termin-Checker API läuft!"

def refresh_termine_periodisch():
    while True:
        print("🔁 Starte Terminprüfung...")
        finde_termine()
        print("✅ Termine aktualisiert:", aktuelle_termine)
        time.sleep(300)  # Alle 5 Minuten

if __name__ == "__main__":
    threading.Thread(target=refresh_termine_periodisch, daemon=True).start()

    port = os.environ.get('PORT')
    if port is None:
        port = 5000
    else:
        port = int(port)

    app.run(host='0.0.0.0', port=port)
