import json
import pdfplumber
import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from openai import OpenAI
from pathlib import Path

# =====================
# CONFIG
# =====================

BASE_DIR = Path(__file__).parent
PDF_PATH = BASE_DIR / "data/reports/market_report.pdf"
NEWS_PATH = BASE_DIR / "data/news_links.json"
TEMPLATE_DIR = BASE_DIR / "templates"
OUTPUT_PATH = BASE_DIR / "output/newsletter.html"

LM_STUDIO_URL = "http://127.0.0.1:1234"
MODEL_NAME = "google/gemma-3n-e4b"

# =====================
# LLM CLIENT
# =====================

client = OpenAI(
    base_url=LM_STUDIO_URL,
    api_key="lm-studio"
)

# =====================
# UTILS
# =====================

def load_prompt(path):
    return Path(path).read_text(encoding="utf-8")

def chunk_text(text, size=1500):
    words = text.split()
    return [" ".join(words[i:i+size]) for i in range(0, len(words), size)]

def llm_call(system_prompt, user_content):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content.strip()

# =====================
# PDF PIPELINE
# =====================

def extract_pdf_text(path):
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
    return text

def summarize_pdf(pdf_path):
    system_prompt = load_prompt(BASE_DIR / "prompts/pdf_summary.txt")
    raw_text = extract_pdf_text(pdf_path)
    chunks = chunk_text(raw_text)

    partial_summaries = []
    for chunk in chunks:
        partial_summaries.append(llm_call(system_prompt, chunk))

    # Final synthesis
    final_summary = llm_call(
        system_prompt,
        "\n\n".join(partial_summaries)
    )

    # Simple parsing
    lines = final_summary.splitlines()
    executive_summary = []
    key_insights = []

    for line in lines:
        if line.strip().startswith(("-", "•")):
            key_insights.append(line.replace("-", "").replace("•", "").strip())
        elif line.strip():
            executive_summary.append(line.strip())

    return {
        "executive_summary": " ".join(executive_summary),
        "key_insights": key_insights
    }

# =====================
# NEWS PIPELINE
# =====================

def extract_article_text(url):
    response = requests.get(url, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")
    paragraphs = soup.find_all("p")
    return " ".join(p.get_text() for p in paragraphs[:20])

def summarize_news():
    system_prompt = load_prompt(BASE_DIR / "prompts/news_summary.txt")

    with open(NEWS_PATH, "r", encoding="utf-8") as f:
        links = json.load(f)

    highlights = []

    for link in links:
        try:
            article_text = extract_article_text(link)
            summary = llm_call(system_prompt, article_text)

            highlights.append({
                "title": link.split("/")[2],
                "summary": summary,
                "link": link
            })
        except Exception as e:
            print(f"Failed to process {link}: {e}")

    return highlights

# =====================
# HTML GENERATION
# =====================

def generate_email(content):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("email_template.html")

    html = template.render(
        executive_summary=content["executive_summary"],
        key_insights=content["key_insights"],
        market_highlights=content["market_highlights"]
    )

    OUTPUT_PATH.write_text(html, encoding="utf-8")

# =====================
# MAIN
# =====================

def main():
    print("📄 Processing PDF...")
    pdf_content = summarize_pdf(PDF_PATH)

    print("📰 Processing news...")
    news = summarize_news()

    print("✉️ Generating email...")
    generate_email({
        "executive_summary": pdf_content["executive_summary"],
        "key_insights": pdf_content["key_insights"],
        "market_highlights": news
    })

    print(f"✅ Newsletter ready: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
