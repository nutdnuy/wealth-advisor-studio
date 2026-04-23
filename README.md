# Wealth Advisor Studio — Streamlit

LLM-powered personalized wealth-review presentation generator, in a single-file Streamlit app. Drop in a client's portfolio → pulls live prices from Alpha Vantage → runs deterministic analytics in Python → LLM writes the narrative → renders a dark-theme PDF deck with pages from JPM's *Guide to the Markets* embedded.

This is the Streamlit edition of [wealth-advisor-studio](../wealth-advisor-studio) (FastAPI edition). Same backend modules, different UI.

## Highlights

- **Compliance-first architecture**: numbers computed in Python, LLM only writes narrative around them.
- **Alpha Vantage** pricing with rate-limiting + 15-min cache, plus manual per-ticker price overrides.
- **CSV upload** or manual `data_editor` table.
- **Guide to the Markets** pages auto-embedded based on portfolio tilt.
- **QuantSeras dark theme** (Material-dark + desaturated green).
- **PDF output** via WeasyPrint (no headless browser, small image).
- Deployable to **Streamlit Community Cloud**, **Docker**, or any VPS.

## Quick start — local

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# macOS system deps
brew install pango cairo gdk-pixbuf libffi shared-mime-info poppler

cp .env.example .env     # then edit with your OpenAI + Alpha Vantage keys
streamlit run streamlit_app.py
```

Open http://localhost:8501.

## Quick start — Streamlit Community Cloud

1. Fork / push this repo to GitHub.
2. Go to https://share.streamlit.io → New app → point at this folder.
3. Add secrets:

```toml
WAS_OPENAI_API_KEY = "sk-..."
WAS_ALPHA_VANTAGE_KEY = ""
WAS_MODEL = "gpt-4o-mini"
```

4. Deploy. `packages.txt` and `requirements.txt` are auto-installed.

## Quick start — Docker

```bash
cp .env.example .env
docker build -t wealth-advisor-streamlit .
docker run -d --env-file .env -p 8501:8501 --name was-streamlit wealth-advisor-streamlit
```

## Architecture

```
streamlit_app.py           Single-page Streamlit UI (replaces FastAPI + HTML)
app/
├── config.py              Settings from env / .env / st.secrets
├── schemas.py             Pydantic models (Client, Holding, Narrative...)
├── llm.py                 Async OpenAI client, structured output
├── market_data.py         Alpha Vantage GLOBAL_QUOTE + OVERVIEW + cache
├── portfolio.py           MTM / allocation / P&L / concentration
├── guide_extractor.py     Rasterize Guide PDF pages, auto-select by tilt
├── charts.py              Matplotlib in dark theme → base64 PNG
├── recommender.py         Build LLM narrative with strict schema
└── deck_builder.py        HTML deck template + WeasyPrint → PDF
data/
└── mi-guide-to-the-markets-us.pdf   (included)
```

## Disclaimer

Outputs are informational only and not investment advice. Numerical calculations are deterministic; narrative is LLM-generated and must be reviewed by a licensed advisor before sharing with a client.
