import yfinance as yf
import time
import pytz
import smtplib
import os
import logging
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

# -------------------
# CONFIGURATION
# -------------------
load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

PARIS_TZ = pytz.timezone('Europe/Paris')

PORTFOLIO_USD = 1_000_000
PORTFOLIO_DAX = 0
last_hour_report = None

# -------------------
# LOGGING CONFIG
# -------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# -------------------
# ENVOI EMAIL
# -------------------
def send_email(subject, message):
    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = TO_EMAIL

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, TO_EMAIL, msg.as_string())
        logging.info(f"Email envoyé : {subject}")
    except Exception as e:
        logging.error(f"Erreur envoi email: {e}")

# -------------------
# RECUPERATION DES DONNEES
# -------------------
def get_last_two_candles():
    try:
        ticker = yf.Ticker("^GDAXI")
        df = ticker.history(interval="15m", period="1d")
        if len(df) < 3:
            return None, None
        return df.iloc[-2], df.iloc[-3]
    except Exception as e:
        logging.error(f"Erreur récupération des données: {e}")
        return None, None

# -------------------
# LOGIQUE TRADING
# -------------------
def trading_bot():
    global PORTFOLIO_USD, PORTFOLIO_DAX, last_hour_report

    now = datetime.now(PARIS_TZ)

    # ✅ Bot actif uniquement entre 09:30 et 17:30
    if now.hour < 9 or (now.hour == 9 and now.minute < 30) or (now.hour > 17 or (now.hour == 17 and now.minute > 30)):
        logging.info("Bot en veille (hors horaires)")
        time.sleep(60)
        return

    # Vente automatique à 17:30
    if now.hour == 17 and now.minute >= 30 and PORTFOLIO_DAX > 0:
        last_candle, _ = get_last_two_candles()
        if last_candle is not None:
            close_price = last_candle["Close"]
            PORTFOLIO_USD += PORTFOLIO_DAX * close_price
            PORTFOLIO_DAX = 0
            logging.info("Fin de journée : positions fermées")
            send_email("Clôture GDAXI", f"Positions fermées.\nUSD: {PORTFOLIO_USD:.2f}\nDAX: {PORTFOLIO_DAX}")
        return

    # Récupération des 2 bougies terminées
    candle_m1, candle_m2 = get_last_two_candles()
    if candle_m1 is None or candle_m2 is None:
        logging.warning("Pas assez de données")
        time.sleep(60)
        return

    # Calcul M1 et M2
    M1 = (candle_m1["Open"] + candle_m1["High"] + candle_m1["Low"] + candle_m1["Close"]) / 4
    M2 = (candle_m2["Open"] + candle_m2["High"] + candle_m2["Low"] + candle_m2["Close"]) / 4

    # Achat si M1 > M2
    if M1 > M2:
        current_price = candle_m1["Close"]
        PORTFOLIO_USD -= current_price
        PORTFOLIO_DAX += 1

    # Rapport toutes les heures pile
    if last_hour_report != now.hour:
        last_hour_report = now.hour
        report = f"Heure : {now.strftime('%H:%M')}\nUSD : {PORTFOLIO_USD:.2f}\nDAX : {PORTFOLIO_DAX}"
        logging.info(report)
        send_email("Rapport horaire GDAXI", report)

    time.sleep(60)

# -------------------
# BOUCLE PRINCIPALE
# -------------------
if __name__ == "__main__":
    logging.info("Bot GDAXI démarré...")
    while True:
        try:
            trading_bot()
        except Exception as e:
            logging.error(f"Erreur inattendue: {e}")
            time.sleep(60)
