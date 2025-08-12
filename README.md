## Playwright Featured Deals Scraper (Maui)

### First time

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install playwright pandas
python -m playwright install

# Go!
python extract_maui_deals.py --headed
```

This project uses Playwright (Python, sync API) to scrape the "Featured Deals" section from Costco Travel's Maui Vacation Packages page and outputs a pretty console table plus JSON/CSV files.

### Setup

Create a virtual environment and install dependencies via Make:

```bash
python -m venv .venv
. .venv/bin/activate
make setup
```

Alternatively, on Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
make setup
```

### Run (headed)

```bash
python extract_maui_deals.py --headed
```

### Custom URL

```bash
python extract_maui_deals.py --url "https://www.costcotravel.com/Vacation-Packages/Hawaii/Maui" --headed
```

You can also adjust timeouts in milliseconds:

```bash
python extract_maui_deals.py --timeout 45000 --headed
```

To pause after navigation and inspect selectors using the Playwright inspector (to refine if the site changes):

```bash
python extract_maui_deals.py --headed --debug-selectors
```

### Outputs

- `featured_deals.csv`: CSV file in the project root
- `featured_deals.json`: JSON file in the project root

Open the CSV in your preferred spreadsheet application, or preview it directly in your editor. The JSON can be loaded by other tools or viewed in any JSON viewer.

### Notes

- The scraper prints a formatted table with columns: `#`, `Title`, `Price`, `Link`.
- If the site structure changes, see selector notes inside `extract_maui_deals.py` near the Featured Deals section and card locators to adjust.
