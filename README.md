# AURA // Multi-Agent Stock Prediction Panel

AURA is a dockerized stock price prediction application that analyzes financial news, press releases, and market fundamentals using a multi-agent **Panel of Experts** pattern built on **LangGraph** and **FastAPI**.

It features a premium, interactive glassmorphic dashboard UI with live timeline status visualization, financial metrics display, real-time agent debate chat bubbles, and stock price chart projections.

---

## Architecture & Multi-Agent Flow

AURA uses a sequential multi-agent debate and synthesis workflow modeled in LangGraph:

1. **Market Data Node**: Fetches live stock details, price history, and key metrics (P/E ratio, Forward P/E, EPS, Market Capitalisation) using `yfinance`.
2. **Bullish Analyst (Advocate)**: Reviews the fundamentals and press release to build the strongest possible bullish growth or undervaluation case.
3. **Bearish Analyst (Challenger)**: Criticizes the advocate's assumptions, identifying valuation risks (e.g. high P/E ratio, weak PEG), competitor threats, and execution hurdles.
4. **Moderator (Synthesizer)**: Acts as the investment committee head. Evaluates both arguments, checks key data, resolves the debate, and writes a finalized investment decision report along with numeric price predictions.

### LLM & Fallback Mode
* **LLM Mode**: Uses LangChain (`ChatOpenAI` or `ChatGoogleGenerativeAI`) to power the debate agents when API keys are available in `.env`.
* **Rules-Based Fallback Mode**: If API keys are absent, a mock analysis engine executes. It evaluates the stock's actual fundamentals (such as P/E ratio triggers and news sentiment) to assemble realistic, context-specific debate transcripts. This ensures the app works immediately out-of-the-box.

---

## Directory Structure

This project follows modern Python directory practices (using a `src/` layout and hatchling backend):
```
python-stock/
├── pyproject.toml              # Project dependencies and build settings
├── .env                        # Configuration file for keys and ports
├── Dockerfile                  # Multi-stage build utilising uv
├── docker-compose.yml          # Container orchestration config
├── README.md                   # Setup and usage guide
└── src/
    └── stock_predictor/
        ├── main.py             # FastAPI backend & static assets server
        ├── agent/              # LangGraph workflow structure
        │   ├── state.py        # Shared agent state definitions
        │   ├── graph.py        # LangGraph StateGraph assembly
        │   └── nodes.py        # Bull, Bear, and Moderator nodes logic
        ├── services/           # Underlying stock query & sentiment APIs
        │   ├── data_fetcher.py # yfinance data fetching with offline fallbacks
        │   └── sentiment.py    # VADER sentiment analysis
        └── static/             # Frontend Single Page App (HTML, CSS, JS)
```

---

## Getting Started

### Prerequisites
* Python 3.11+
* [Podman](https://podman.io/) (and optionally `podman-compose` or `docker-compose`)

### 1. Configuration
Open `.env` in the root folder and configure your settings:
```bash
# Set your preferred provider (openai or gemini)
LLM_PROVIDER=openai

# Provide your API key
OPENAI_API_KEY=your_openai_api_key_here
```
*If you leave the API key blank, the application will automatically activate the rules-based fallback debate engine.*

---

## Running with Podman (Recommended)

Since this app is containerized, you can build and run it immediately using Podman.

### Build the Image
```bash
podman build -t stock-predictor .
```

### Run the Container
```bash
podman run -d -p 8000:8000 --name stock-predictor-app --env-file .env stock-predictor
```

### Or using Podman Compose
If you have `podman-compose` installed:
```bash
podman-compose up --build -d
```

Open your browser and navigate to **`http://localhost:8000`** to view the dashboard!

---

## Running Locally

If you wish to run the application on your host machine without containerization, you can run it using your local Python launcher:

### 1. Set up a virtual environment (using `uv` for speed)
First, make sure `uv` is installed globally:
```bash
py -m pip install uv
```

Initialize the virtual environment and install the package dependencies:
```bash
uv venv
# On Windows:
.venv\Scripts\activate
# Install the package in editable mode
uv pip install -e .
```

### 2. Start the Backend Server
Run the FastAPI application locally:
```bash
py src/stock_predictor/main.py
```
Open **`http://localhost:8000`** to view the app.
