# Reference data

The app embeds pages from **J.P. Morgan Asset Management — *Guide to the Markets (U.S.)***. The PDF is NOT committed to this repo (copyright).

## How to obtain

1. Download the latest edition from JPM:
   - https://am.jpmorgan.com/us/en/asset-management/adv/insights/market-insights/guide-to-the-markets/
2. Save the PDF to this folder as `mi-guide-to-the-markets-us.pdf`.
3. Restart the app.

## Verify

Page indices hard-coded in `app/guide_extractor.py` (p.4–8, 18, 33, 45, 56, 58) correspond to the **U.S.** edition, Q1 2026 layout. If JPM renumbers pages in a later quarter, update the `GUIDE_INDEX` dict in that file.

## Disclaimer

This repo uses the Guide strictly for educational demonstration of an LLM workflow. The embedded page images inherit JPM's original copyright and disclaimers. Do not redistribute rendered decks externally without JPM's permission.
