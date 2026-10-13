import json
import pdfplumber
import requests
import pandas as pd
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import warnings
from datetime import datetime, timedelta, timezone
import re


warnings.filterwarnings("ignore")

# =====================
# KONFIGURACJA
# =====================

BASE_DIR = Path(__file__).parent
KATALOG_PDF = BASE_DIR / "data/reports"
KATALOG_XLSX = BASE_DIR / "data/reports"
SCIEZKA_NEWS = BASE_DIR / "data/news_links.json"
KATALOG_SZABLONOW = BASE_DIR / "templates"
SCIEZKA_WYNIKOWA = BASE_DIR / "output/newsletter.html"

LM_STUDIO_URL = "http://localhost:1234"
MODEL_NAME = "mistralai/mistral-7b-instruct-v0.3"

# =====================
# FUNKCJA LLM
# =====================

def llm_call(prompt, text):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": f"{prompt}\n\n{text[:8000]}"
            }
        ],
        "temperature": 0.1,
        "max_tokens": 700
    }

    try:
        response = requests.post(
            f"{LM_STUDIO_URL}/v1/chat/completions",
            json=payload,
            timeout=120000
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print(f"❌ Błąd LLM: {e}")
        return ""

        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"❌ Błąd LLM: {e}")
        return ""

# =====================
# PDF
# =====================

def wyciagnij_tekst_pdf(sciezka):
    tekst = ""
    with pdfplumber.open(sciezka) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                tekst += page.extract_text() + "\n"
    return tekst

def wczytaj_wszystkie_pdf(katalog):
    calosc = ""
    for pdf in katalog.glob("*.pdf"):
        print(f"   → PDF: {pdf.name}")
        calosc += f"\n\nŹRÓDŁO PDF: {pdf.name}\n"
        calosc += wyciagnij_tekst_pdf(pdf)
    return calosc

# =====================
# EXCEL – KLUCZOWA ZMIANA
# =====================

def streszczenie_excel(df, nazwa):
    opis = []
    opis.append(f"Plik Excel: {nazwa}")
    opis.append(f"Liczba wierszy: {len(df)}")
    opis.append(f"Liczba kolumn: {len(df.columns)}")

    num = df.select_dtypes(include="number")

    if not num.empty:
        for col in num.columns[:5]:
            opis.append(
                f"{col}: min={num[col].min()}, "
                f"max={num[col].max()}, "
                f"średnia={round(num[col].mean(), 2)}"
            )

    return "\n".join(opis)

def wczytaj_wszystkie_excel(katalog):
    calosc = ""
    for plik in katalog.glob("*.xlsx"):
        print(f"   → Excel: {plik.name}")
        try:
            df = pd.read_excel(plik)
            calosc += "\n\nŹRÓDŁO EXCEL:\n"
            calosc += streszczenie_excel(df, plik.name)
        except Exception as e:
            print(f"❌ Excel error {plik.name}: {e}")
    return calosc

# =====================
# PODSUMOWANIE DOKUMENTÓW
# =====================

def podsumowanie_dokumentow():
    prompt = Path(BASE_DIR / "prompts/pdf_summary.txt").read_text(encoding="utf-8")

    tekst_pdf = wczytaj_wszystkie_pdf(KATALOG_PDF)
    tekst_excel = wczytaj_wszystkie_excel(KATALOG_XLSX)

    surowy = "\n\n".join([tekst_pdf, tekst_excel]).strip()

    if not surowy:
        return {"streszczenie": "", "kluczowe_wnioski": []}

    wynik = llm_call(prompt, surowy)

    streszczenie = []
    wnioski = []

    for line in wynik.splitlines():
        if line.strip().startswith(("-", "•")):
            wnioski.append(line.lstrip("-• ").strip())
        elif line.strip():
            streszczenie.append(line.strip())

    return {
        "streszczenie": " ".join(streszczenie),
        "kluczowe_wnioski": wnioski
    }

# =====================
# NEWSY
# =====================

def wyciagnij_tekst_artykulu(url):
    r = requests.get(url, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    p = soup.find_all("p")
    return " ".join(x.get_text() for x in p[:15])

def podsumowanie_news():
    prompt = Path(BASE_DIR / "prompts/news_summary.txt").read_text(encoding="utf-8")

    with open(SCIEZKA_NEWS, encoding="utf-8") as f:
        linki = json.load(f)

    wynik = []

    for link in linki:
        try:
            print(f"   → News: {link}")
            txt = wyciagnij_tekst_artykulu(link)
            pod = llm_call(prompt, txt)
            wynik.append({
                "tytul": link.split("/")[2],
                "podsumowanie": pod,
                "link": link
            })
        except Exception as e:
            print(f"❌ News error: {e}")

    return wynik

# =====================
# HTML
# =====================

def generuj_email(zawartosc):
    env = Environment(loader=FileSystemLoader(KATALOG_SZABLONOW))
    template = env.get_template("email_template.html")

    html = template.render(
        streszczenie=zawartosc["streszczenie"],
        kluczowe_wnioski=zawartosc["kluczowe_wnioski"],
        najwazniejsze_news=zawartosc["najwazniejsze_news"]
    )

    SCIEZKA_WYNIKOWA.write_text(html, encoding="utf-8")

# =====================
# MAIN
# =====================

def main():
    print("📄 PDF + Excel")
    dokumenty = podsumowanie_dokumentow()

    print("📰 Newsy")
    newsy = podsumowanie_news()

    print("✉️ Generowanie HTML")
    generuj_email({
        "streszczenie": dokumenty["streszczenie"],
        "kluczowe_wnioski": dokumenty["kluczowe_wnioski"],
        "najwazniejsze_news": newsy
    })

    print(f"✅ GOTOWE → {SCIEZKA_WYNIKOWA}")

if __name__ == "__main__":
    main()
