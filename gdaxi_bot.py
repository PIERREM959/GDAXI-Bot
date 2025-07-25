import yfinance as yf
import time
import pytz
import smtplib
import os
import logging
from email.mime.text import MIMEText
from datetime import datetime, timedelta
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

INITIAL_CAPITAL = 1_000_000
PORTFOLIO_USD = INITIAL_CAPITAL
PORTFOLIO_DAX = 0
last_hour_report = None

MARKET_OPEN = (9, 30)   # 09:30
MARKET_CLOSE = (17, 30) # 17:30

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
# ATTENTE JUSQU'À PROCHAINE OUVERTURE
# -------------------
def wait_until_open():
    now = datetime.now(PARIS_TZ)
    next_open = now.replace(hour=MARKET_OPEN[0], minute=MARKET_OPEN[1], second=0, microsecond=0)
    if now > next_open:
        next_open += timedelta(days=1)
    sleep_seconds = (next_open - now).total_seconds()
    logging.info(f"⏸ Marché fermé : reprise à {next_open.strftime('%Y-%m-%d %H:%M')}")
    time.sleep(sleep_seconds)

# -------------------
# LOGIQUE TRADING
# -------------------
def trading_bot():
    global PORTFOLIO_USD, PORTFOLIO_DAX, last_hour_report

    now = datetime.now(PARIS_TZ)
    market_open_time = now.replace(hour=MARKET_OPEN[0], minute=MARKET_OPEN[1])
    market_close_time = now.replace(hour=MARKET_CLOSE[0], minute=MARKET_CLOSE[1])

    # Si avant ouverture → attendre
    if now < market_open_time:
        wait_until_open()
        return

    # Si après fermeture → vente + bilan + pause
    if now > market_close_time:
        if PORTFOLIO_DAX > 0:
            last_candle, _ = get_last_two_candles()
            if last_candle is not None:
                close_price = last_candle["Close"]
                PORTFOLIO_USD += PORTFOLIO_DAX * close_price
                PORTFOLIO_DAX = 0
                gain = PORTFOLIO_USD - INITIAL_CAPITAL
                message = (
                    f"Clôture du marché :\n"
                    f"USD final : {PORTFOLIO_USD:.2f}\n"
                    f"Gain du jour : {gain:+.2f}\n"
                    f"DAX : {PORTFOLIO_DAX}"
                )
                logging.info("📩 " + message.replace("\n", " | "))
                send_email("Clôture GDAXI", message)
        wait_until_open()
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
        report = (
            f"Heure : {now.strftime('%H:%M')}\n"
            f"USD : {PORTFOLIO_USD:.2f}\n"
            f"DAX : {PORTFOLIO_DAX}"
        )
        logging.info("⏱ Rapport : " + report.replace("\n", " | "))
        send_email("Rapport horaire GDAXI", report)

    time.sleep(60)

# -------------------
# BOUCLE PRINCIPALE
# -------------------
if __name__ == "__main__":
    logging.info("✅ Bot GDAXI démarré...")
    while True:
        try:
            trading_bot()
        except Exception as e:
            logging.error(f"Erreur inattendue: {e}")
            time.sleep(60)
