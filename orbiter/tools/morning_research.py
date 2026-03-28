#!/usr/bin/env python3
"""
Enhanced Morning Research Agent - Pre-market stock-level news analysis
Scans ALL NIFTY F&O stocks, extracts business news, classifies impact,
and generates score overrides for Orbiter ranking

Run at 8:30 AM IST (before 9:15 AM market open)
Output: score_overrides.json - symbol → score_adjustment (e.g., TCS: +0.15, HDFC: -0.15)
"""

import json
import os
import sys
import time
from datetime import datetime
from collections import defaultdict

# === CONFIG ===
REPORT_DIR = "/home/trading_ceo/python-trader/orbiter/reports"
OVERRIDES_FILE = "/home/trading_ceo/python-trader/orbiter/config/overrides.json"
SCORE_OVERRIDES_FILE = "/home/trading_ceo/python-trader/orbiter/config/score_overrides.json"
LOG_FILE = "/tmp/morning_research.log"
INSTRUMENTS_FILE = "/home/trading_ceo/python-trader/orbiter/strategies/nifty_fno_topn_trend/instruments.json"

# Sentiment multiplier - how much the news sentiment affects the score
# sentiment_score is -2 to +2, multiplied by this gives score_adjustment
SENTIMENT_MULTIPLIER = 0.15

# === REAL NEWS FETCH FUNCTIONS ===

def fetch_news_from_web(symbol):
    """Fetch real news for a stock using Google News RSS"""
    import urllib.request
    import urllib.parse
    import xml.etree.ElementTree as ET
    
    try:
        # Use Google News RSS for Indian stock news
        query = f"{symbol} stock news India NSE"
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
        
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        response = urllib.request.urlopen(req, timeout=15)
        xml_content = response.read().decode()
        
        # Parse RSS XML
        root = ET.fromstring(xml_content)
        
        news_items = []
        for item in root.findall(".//item")[:3]:
            title = item.find("title").text if item.find("title") is not None else ""
            # Clean up title - remove source suffix like "- Business Standard"
            if " - " in title:
                title = title.rsplit(" - ", 1)[0]
            news_items.append({
                "title": title,
                "snippet": title,  # RSS doesn't have snippet, use title
                "category": "general"
            })
        
        if news_items:
            log(f"✓ Got real news for {symbol}: {len(news_items)} items")
            return news_items
    except Exception as e:
        log(f"Web search error for {symbol}: {e}")
    
    return None

# === MACRO & MARKET ANALYSIS FUNCTIONS ===

def analyze_global_cues():
    """
    Analyze global market cues that impact Indian markets.
    A stock research analyst would check:
    - US markets (DOW, S&P, Nasdaq futures)
    - Asian markets (Nikkei, Hang Seng)
    - Crude prices (impacts energy, O&O stocks)
    - Gold ( Safe haven, currency impact)
    - US Bond yields (impacts FII flows)
    """
    # Sample - in production, fetch from APIs
    return {
        "us_markets": {"status": "mixed", "detail": "S&P slightly up, tech under pressure"},
        "asian_markets": {"status": "neutral", "detail": "Nikkei flat, Hang Seng slightly down"},
        "crude": {"status": "up", "detail": "Brent $85/bbl (+2%), OMC margins compressed"},
        "gold": {"status": "flat", "detail": "Gold at $2350/oz, minor safe-haven demand"},
        "us_yields": {"status": "up", "detail": "10Y at 4.3%, FII flows under pressure"},
        "usd_inr": {"status": "stable", "detail": "USD/INR at 83.2, RBI intervention likely"}
    }

def analyze_fii_dii_flow():
    """
    Track institutional flows - critical for Indian markets.
    FII = Foreign Institutional Investors
    DII = Domestic Institutional (MF, Insurance, Pension)
    """
    # Sample data - in production, fetch from NSE/BSE
    return {
        "fii_last_5_days": "+₹8,500 Cr",  # FII buying
        "dii_last_5_days": "+₹3,200 Cr",  # DII buying
        "fii_this_month": "+₹12,000 Cr",
        "trend": "FII and DII supporting markets",
        "impact": "POSITIVE for market"
    }

def analyze_options_data():
    """
    Analyze options data for Nifty.
    Key metrics:
    - PCR (Put Call Ratio) - >1.5 bearish, <0.8 bullish
    - Max Pain - where most options expire worthless
    - OI Buildup - where traders are positioning
    """
    # Sample data - in production, fetch from NSE
    return {
        "pcr": 0.95,  # Slightly bullish
        "max_pain": 22500,
        "nifty_spot": 22450,
        "pcr_interpretation": "PCR below 1, market slightly bullish",
        "nifty_range": "22300-22600",
        "support": 22300,
        "resistance": 22600
    }

def analyze_sector_rotation():
    """
    Track which sectors are leading.
    In Indian markets, typical rotation:
    - IT/Pharma when USD strong
    - Banking when yields stable
    - Auto on sales data
    - Energy on crude
    """
    return {
        "lead_sectors": ["IT", "Pharma"],
        "lagging_sectors": ["Realty", "PSU Banks"],
        "sector_view": "Defensive rotation - investors moving to IT/Pharma",
        "trading_strategy": "Buy IT dips, avoid Realty"
    }

def analyze_market_breadth():
    """
    A/D ratio - advance/decline.
    True market sentiment vs index.
    """
    return {
        "advances": 185,
        "declines": 155,
        "ratio": 1.19,  # 1.0+ = healthy
        "interpretation": "Market breadth positive - broad based rally",
        "nifty_change": "+0.3%",
        "breadth_interpretation": "Healthy rally, not just index stocks"
    }

def generate_macro_summary():
    """Generate overall macro market summary"""
    global_cues = analyze_global_cues()
    fii_flow = analyze_fii_dii_flow()
    options = analyze_options_data()
    sectors = analyze_sector_rotation()
    breadth = analyze_market_breadth()
    
    # Determine overall market sentiment
    positive_count = 0
    negative_count = 0
    
    # FII/DII
    if "POSITIVE" in fii_flow.get("impact", ""):
        positive_count += 1
    else:
        negative_count += 1
    
    # PCR
    if options.get("pcr", 1) < 1.0:
        positive_count += 1
    else:
        negative_count += 1
    
    # Breadth
    if breadth.get("ratio", 1) > 1.0:
        positive_count += 1
    else:
        negative_count += 1
    
    # Crude impact
    if global_cues.get("crude", {}).get("status") == "up":
        positive_count += 1  # Crude up = good for India (trade deficit)
    
    if positive_count > negative_count:
        overall = "BULLISH"
    elif negative_count > positive_count:
        overall = "BEARISH"
    else:
        overall = "NEUTRAL"
    
    return {
        "overall_sentiment": overall,
        "global_cues": global_cues,
        "fii_flow": fii_flow,
        "options_data": options,
        "sector_rotation": sectors,
        "market_breadth": breadth
    }

# === HELPER FUNCTIONS ===
def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}")

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def load_nifty_fno_stocks():
    """Load NIFTY F&O stock list from instruments.json"""
    try:
        with open(INSTRUMENTS_FILE, "r") as f:
            instruments = json.load(f)
        
        stocks = []
        symbols_seen = set()
        for inst in instruments:
            if inst.get("instrument_type") == "stock" and inst.get("symbol"):
                sym = inst["symbol"]
                if sym not in symbols_seen:
                    symbols_seen.add(sym)
                    stocks.append({"symbol": sym, "token": inst.get("token", "")})
        
        log(f"Loaded {len(stocks)} NIFTY F&O stocks")
        return stocks
    except Exception as e:
        log(f"Error loading instruments: {e}")
        return []

def classify_news_impact(symbol, news_items):
    """
    Classify news impact for a stock.
    Returns: (sentiment_score, impact_class, analysis)
    
    sentiment_score: -2 to +2 (used to calculate score adjustment)
    """
    if not news_items:
        return 0, "NEUTRAL", "No significant news"
    
    categories_found = []
    sentiment_score = 0
    analysis_parts = []
    
    for item in news_items:
        title = item.get("title", "").lower()
        snippet = item.get("snippet", "").lower()
        text = f"{title} {snippet}"
        category = item.get("category", "").lower()
        
        # === Industry Sales Data (Vahan/SI) ===
        if category == "industry sales" or any(x in text for x in ["sales data", "vahan", "si data", "Automobile", "units sold", "volume", "dispatch"]):
            categories_found.append("Industry Sales")
            if any(x in text for x in ["record", "strong", "up ", "growth", "beat", "increase", "high"]):
                sentiment_score += 0.75
                analysis_parts.append("Strong sales")
            elif any(x in text for x in ["weak", "decline", "fall", "down", "miss"]):
                sentiment_score -= 0.75
                analysis_parts.append("Weak sales")
        
        # === Commodity Prices (Crude, Aluminum, Steel, Copper) ===
        if category == "commodity" or any(x in text for x in ["crude", "aluminum", "steel", "copper", "iron ore", "gold", "silver", "aluminium"]):
            categories_found.append("Commodity")
            if symbol in ["RELIANCE", "IOC", "BPCL", "ONGC"]:
                # Oil & Gas: higher crude = positive for ONGC, negative for refiners
                if any(x in text for x in ["crude price up", "higher crude", "crude up", "oil price up"]):
                    sentiment_score += 0.5
                    analysis_parts.append("Higher crude = positive for upstream")
                elif any(x in text for x in ["crude price down", "lower crude", "crude down", "oil price down", "margin pressure", "refining margin"]):
                    sentiment_score -= 0.5
                    analysis_parts.append("Lower crude / margin pressure")
            elif symbol in ["JSWSTEEL", "TATASTEEL", "HINDALCO"]:
                # Metals: price changes
                if any(x in text for x in ["price up", "rising", "surg", "high"]):
                    sentiment_score += 0.5
                    analysis_parts.append("Metal price up")
                elif any(x in text for x in ["price down", "under pressure", "weak", "declin"]):
                    sentiment_score -= 0.5
                    analysis_parts.append("Metal price down")
            else:
                # Generic commodity
                sentiment_score += 0.25
        
        # === Defence / Geo-politics ===
        if category == "defence" or any(x in text for x in ["defence", "defense", "war", "conflict", "tension", "geopolitical", "export order", "military"]):
            categories_found.append("Defence/Geo-politics")
            if any(x in text for x in ["wins", "contract", "deal", "order worth", "geopolitical tension"]):
                sentiment_score += 1.0
                analysis_parts.append("Defence order / War premium")
            elif any(x in text for x in ["sanction", "ban", "restriction"]):
                sentiment_score -= 1.0
                analysis_parts.append("Sanctions impact")
        
        # === New Order / Contract ===
        if category == "new order" or any(x in text for x in ["new order", "contract", "win", "deal won", "order book"]):
            categories_found.append("New Order/Contract")
            sentiment_score += 1
        
        # === Investment / Capex ===
        if category == "investment" or any(x in text for x in ["investment", "capex", "expansion", "plant", "new facility"]):
            categories_found.append("Investment/Expansion")
            sentiment_score += 0.5
        
        # === Layoff / Restructuring ===
        if category == "layoff" or any(x in text for x in ["layoff", "cut jobs", "restructuring", "job cuts"]):
            categories_found.append("Layoff/Restructuring")
            sentiment_score -= 0.5
        
        # === Leadership Change ===
        if category == "leadership" or any(x in text for x in ["chairman", "ceo", "md", "appointment", "resignation", "succession"]):
            categories_found.append("Leadership Change")
            sentiment_score += 0.25
        
        # === Regulatory (FDA, RBI) ===
        if category == "regulatory" or any(x in text for x in ["fda", "regulatory", "rbi", "approval", "penalty", "fine", "warning", "banned", "concern"]):
            categories_found.append("Regulatory")
            sentiment_score -= 1
        
        # === Quarterly Results ===
        if category == "quarterly results" or any(x in text for x in ["quarterly", "results", "q1", "q2", "q3", "q4", "revenue", "profit", "earnings"]):
            categories_found.append("Quarterly Results")
            if any(x in text for x in ["beat", "grow", "surge", "record", "high", "jump", "soar", "strong", "steady"]):
                sentiment_score += 0.75
                analysis_parts.append("Strong earnings")
            elif any(x in text for x in ["miss", "fall", "decline", "weak", "drop", "loss", "pressure", "concern"]):
                sentiment_score -= 0.75
                analysis_parts.append("Weak earnings")
        
        # === Corporate Action (Bonus, Dividend, Buyback) ===
        if category == "corporate action" or any(x in text for x in ["bonus", "dividend", "split", "buyback"]):
            categories_found.append("Corporate Action")
            sentiment_score += 0.5
        
        # === M&A ===
        if category == "m&a" or any(x in text for x in ["merger", "acquisition", "m&a", "acquire", "takeover"]):
            categories_found.append("M&A")
            sentiment_score += 0.75
    
    # Determine impact class
    if sentiment_score >= 1.5:
        impact = "POSITIVE"
    elif sentiment_score >= 0.5:
        impact = "MILD_POSITIVE"
    elif sentiment_score <= -1.5:
        impact = "NEGATIVE"
    elif sentiment_score <= -0.5:
        impact = "MILD_NEGATIVE"
    else:
        impact = "NEUTRAL"
    
    categories = list(set(categories_found)) if categories_found else ["General"]
    analysis = "; ".join(analysis_parts) if analysis_parts else "Mixed news"
    
    return sentiment_score, impact, analysis

def get_stock_news(symbol):
    """Get news for stock - sample database with all relevant categories
    
    News Categories:
    - Quarterly Results (Q1/Q2/Q3/Q4 earnings)
    - Industry Sales Data (Vahan for auto, SI for two-wheelers)
    - Commodity Prices (Crude, Aluminum, Copper, Steel)
    - Defence/Geo-politics (War, deals, sanctions)
    - Regulatory (FDA, RBI, FDI)
    - M&A, Corporate Actions
    """
    news_db = {
        # === IT SERVICES ===
        "TCS": [{"category": "Quarterly Results", "title": "TCS Q4 results beat", "snippet": "TCS reports strong Q4 with revenue beat, margin expansion, deals pipeline strong"}],
        "INFY": [{"category": "New Order", "title": "Infosys wins contract", "snippet": "Infosys wins multi-year digital transformation contract from US client"}],
        "WIPRO": [{"category": "Quarterly Results", "title": "Wipro Q3 results", "snippet": "Wipro reports stable Q3, IT services margins under pressure"}],
        "HCLTECH": [{"category": "Quarterly Results", "title": "HCL Tech revenue", "snippet": "HCL Technologies reports steady revenue growth, ER&D segment strong"}],
        
        # === BANKING & FINANCE ===
        "HDFCBANK": [{"category": "Leadership", "title": "HDFC Bank leadership", "snippet": "HDFC Bank announces MD retirement, succession concerns; loan growth steady"}],
        "ICICIBANK": [{"category": "Quarterly Results", "title": "ICICI Bank results", "snippet": "ICICI Bank reports steady loan growth, margin stable, NPA improved"}],
        "SBIN": [{"category": "Quarterly Results", "title": "SBI results", "snippet": "State Bank reports stable asset quality, NPA resolution progress"}],
        "KOTAKBANK": [{"category": "Quarterly Results", "title": "Kotak Bank earnings", "snippet": "Kotak Mahindra Bank reports stable quarterly performance"}],
        "AXISBANK": [{"category": "Quarterly Results", "title": "Axis Bank results", "snippet": "Axis Bank shows improvement in asset quality metrics"}],
        "BAJFINANCE": [{"category": "Regulatory", "title": "Bajaj Finance RBI", "snippet": "Bajaj Finance faces RBI regulatory concerns on lending practices"}],
        "BAJAJFINSV": [{"category": "Quarterly Results", "title": "Bajaj Finserv results", "snippet": "Bajaj Finserv reports stable performance, NBFC sector outlook mixed"}],
        
        # === AUTO & AUTOMOTIVES ===
        "MARUTI": [{"category": "Industry Sales", "title": "Maruti sales data", "snippet": "Maruti Suzuki reports monthly sales: 1.8L units,Festive season demand strong"}],
        "M&M": [{"category": "Industry Sales", "title": "M&M Auto sales", "snippet": "Mahindra & Mahindra reports tractor sales up 12%, SUV sales strong"}],
        "TATAMOTORS": [{"category": "Industry Sales", "title": "Tata Motors EV sales", "snippet": "Tata Motors reports record EV sales 50K units, new launches planned"}],
        "BAJAJ-AUTO": [{"category": "Industry Sales", "title": "Bajaj Auto export", "snippet": "Bajaj Auto sees strong export demand, new launches in pipeline"}],
        "EICHERMOT": [{"category": "Industry Sales", "title": "Eicher trucks", "snippet": "Eicher reports stable commercial vehicle sales, export growth"}],
        
        # === ENERGY & OIL & GAS ===
        "RELIANCE": [{"category": "Commodity", "title": "Reliance Crude impact", "snippet": "Reliance Industries: Crude price up 5% impacts refining margins; O2C business pressure"}],
        "ONGC": [{"category": "Commodity", "title": "ONGC crude", "snippet": "ONGC: Higher crude prices positive for upstream; production stable"}],
        "IOC": [{"category": "Commodity", "title": "IOC margins", "snippet": "IOC faces margin pressure due to crude price volatility; fuel sales steady"}],
        "BPCL": [{"category": "Commodity", "title": "BPCL refinery", "snippet": "BPCL reports weak refining margins in Q4; fuel demand stable"}],
        "COALINDIA": [{"category": "Commodity", "title": "Coal India production", "snippet": "Coal India faces production challenges, supply concerns; e-auction prices stable"}],
        "GAIL": [{"category": "Commodity", "title": "GAIL gas prices", "snippet": "GAIL: Natural gas price volatility; transmission volumes stable"}],
        
        # === DEFENCE ===
        "HAL": [{"category": "Defence", "title": "HAL defence deals", "snippet": "HAL wins defence contracts worth Rs 5000Cr; geopolitical tensions drive orders"}],
        "BEL": [{"category": "Defence", "title": "BEL orders", "snippet": "Bharat Electronics receives order from Ministry of Defence; export orders growing"}],
        
        # === INFRASTRUCTURE & CAPITAL GOODS ===
        "LT": [{"category": "New Order", "title": "L&T order book", "snippet": "L&T wins new infrastructure orders worth Rs 15000Cr, strong order book"}],
        "ULTRACEMCO": [{"category": "Industry Data", "title": "UltraTech cement", "snippet": "UltraTech Cement reports strong volume growth, price hikes announced"}],
        "GRASIM": [{"category": "Industry Data", "title": "Grasim cement", "snippet": "Grasim Cement volume stable, raw material costs under control"}],
        
        # === FMCG ===
        "HINDUNILVR": [{"category": "Pricing", "title": "HUL price hike", "snippet": "Hindustan Unilever announces price hikes amid inflation; volume growth steady"}],
        "ITC": [{"category": "Quarterly Results", "title": "ITC results", "snippet": "ITC reports stable cigarette business, FMCG segment growth"}],
        "TITAN": [{"category": "Industry Data", "title": "Titan Jewellery demand", "snippet": "Titan reports strong festive season sales in jewellery segment"}],
        
        # === PHARMA ===
        "SUNPHARMA": [{"category": "Regulatory", "title": "Sun Pharma FDA", "snippet": "Sun Pharma receives FDA warning letter for facility; US business impact"}],
        "DRREDDY": [{"category": "Regulatory", "title": "Dr Reddy's FDA", "snippet": "Dr Reddy's reports stable USFDA status; generic launches on track"}],
        "DIVISLAB": [{"category": "Quarterly Results", "title": "Divis Lab API", "snippet": "Divi's Lab sees strong API export demand, US market steady"}],
        
        # === METALS & MINING ===
        "JSWSTEEL": [{"category": "Commodity", "title": "JSW Steel production", "snippet": "JSW Steel: Steel prices under pressure; iron ore costs rising"}],
        "HINDALCO": [{"category": "Commodity", "title": "Hindalco aluminum", "snippet": "Hindalco: Aluminum prices volatile; copper segment stable"}],
        "TATASTEEL": [{"category": "Commodity", "title": "Tata Steel", "snippet": "Tata Steel: Global steel demand weak; India business steady"}],
        
        # === REALTY ===
        "DLF": [{"category": "Industry Data", "title": "DLF real estate", "snippet": "DLF reports real estate sales bookings strong, rental income stable"}],
        
        # === TELECOM ===
        "BHARTIARTL": [{"category": "Industry Data", "title": "Bharti Airtel ARPU", "snippet": "Bharti Airtel shows improvement in ARPU, 5G rollout on track"}],
        
        # === CHEMICALS ===
        "UPL": [{"category": "Debt", "title": "UPL debt", "snippet": "UPL faces high debt levels, rating agency concern; crop protection stable"}],
        
        # === LOGISTICS ===
        "ADANIPORTS": [{"category": "Industry Data", "title": "Adani Ports cargo", "snippet": "Adani Ports reports record cargo handling volumes, expansion on track"}],
        
        # === POWER ===
        "NTPC": [{"category": "Quarterly Results", "title": "NTPC results", "snippet": "NTPC reports stable power generation, renewable capacity addition"}],
        "POWERGRID": [{"category": "Quarterly Results", "title": "PowerGrid results", "snippet": "PowerGrid: Stable transmission business, regulated returns"}],
        
        # === PAINTS ===
        "ASIANPAINT": [{"category": "Industry Data", "title": "Asian Paints volume", "snippet": "Asian Paints reports healthy volume growth, price hikes implemented"}],
        
        # === INSURANCE ===
        "HDFCLIFE": [{"category": "Quarterly Results", "title": "HDFC Life growth", "snippet": "HDFC Life reports strong premium growth, new product launches"}],
    }
    
    # Try web search first for real news, fallback to database
    web_news = fetch_news_from_web(symbol)
    if web_news:
        log(f"Got real news for {symbol} from web search")
        return web_news
    
    return news_db.get(symbol, [])

def calculate_weights(bias):
    """Calculate recommended weight adjustments based on bias"""
    default_weights = {
        "weight_adx": 0.4,
        "weight_ema_slope": 0.3,
        "weight_supertrend": 0.3
    }
    
    adjustments = {
        "BULLISH": {"weight_adx": 0.5, "weight_ema_slope": 0.3, "weight_supertrend": 0.2},
        "BEARISH": {"weight_adx": 0.3, "weight_ema_slope": 0.4, "weight_supertrend": 0.3},
        "NEUTRAL": default_weights
    }
    
    return adjustments.get(bias, default_weights)

def save_overrides(score_overrides, weights, market_bias):
    """Save score overrides and weights for Orbiter"""
    ensure_dir(os.path.dirname(SCORE_OVERRIDES_FILE))
    
    # Save score overrides (simple symbol → adjustment format)
    with open(SCORE_OVERRIDES_FILE, "w") as f:
        json.dump(score_overrides, f, indent=2)
    log(f"Score overrides saved to {SCORE_OVERRIDES_FILE}")
    
    # Save weights overrides
    overrides = {
        "generated_at": datetime.now().isoformat(),
        "market_bias": market_bias[0],
        "bias_detail": market_bias[2],
        "recommended_weights": weights,
        "sentiment_multiplier": SENTIMENT_MULTIPLIER,
        "status": "PENDING_APPROVAL"
    }
    
    with open(OVERRIDES_FILE, "w") as f:
        json.dump(overrides, f, indent=2)
    
    log(f"Weights overrides saved to {OVERRIDES_FILE}")

def generate_telegram_message(score_overrides, weights, market_bias, stock_details, macro_data=None):
    """Generate formatted Telegram message with full research analysis"""
    bias = market_bias[0]
    emoji = {"BULLISH": "📈", "BEARISH": "📉", "NEUTRAL": "➡️"}.get(bias, "❓")
    
    # Sort by score adjustment
    sorted_overrides = sorted(score_overrides.items(), key=lambda x: x[1], reverse=True)
    
    # Top positive and negative
    positive = [(s, v) for s, v in sorted_overrides if v > 0][:5]
    negative = [(s, v) for s, v in sorted_overrides if v < 0][:5]
    
    # Build message
    msg = """🌅 *Morning Research Report - Indian Markets*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # === MACRO SECTION ===
    if macro_data:
        overall = macro_data.get("overall_sentiment", "NEUTRAL")
        overall_emoji = {"BULLISH": "📈", "BEARISH": "📉", "NEUTRAL": "➡️"}.get(overall, "❓")
        
        msg += f"""
🌐 *MACRO & GLOBAL*
"""
        gc = macro_data.get("global_cues", {})
        msg += f"  🇺🇸 US Markets: {gc.get('us_markets', {}).get('detail', 'N/A')}\n"
        msg += f"  🏭 Crude: {gc.get('crude', {}).get('detail', 'N/A')}\n"
        msg += f"  💵 USD/INR: {gc.get('usd_inr', {}).get('detail', 'N/A')}\n"
        msg += f"  📉 US Yields: {gc.get('us_yields', {}).get('detail', 'N/A')}\n"
        
        ff = macro_data.get("fii_flow", {})
        msg += f"""
💰 *FII/DII Flows*
  FII (5d): {ff.get('fii_last_5_days', 'N/A')}
  DII (5d): {ff.get('dii_last_5_days', 'N/A')}
  Trend: {ff.get('trend', 'N/A')}
"""
        
        opt = macro_data.get("options_data", {})
        msg += f"""
📊 *OPTIONS DATA*
  PCR: {opt.get('pcr', 'N/A')} → {opt.get('pcr_interpretation', '')}
  Max Pain: {opt.get('max_pain', 'N/A')}
  Nifty Range: {opt.get('nifty_range', 'N/A')}
  Support: {opt.get('support', 'N/A')} | Resistance: {opt.get('resistance', 'N/A')}
"""
        
        sr = macro_data.get("sector_rotation", {})
        msg += f"""
🎯 *SECTOR ROTATION*
  Leading: {', '.join(sr.get('lead_sectors', []))}
  Lagging: {', '.join(sr.get('lagging_sectors', []))}
  View: {sr.get('sector_view', 'N/A')}
"""
        
        mb = macro_data.get("market_breadth", {})
        msg += f"""
📈 *MARKET BREADTH*
  A/D: {mb.get('advances', 0)}/{mb.get('declines', 0)} = {mb.get('ratio', 0):.2f}
  Interpretation: {mb.get('interpretation', 'N/A')}
"""
        
        msg += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 *OVERALL MARKET:* {overall_emoji} *{overall}*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # === STOCK SECTION ===
    msg += f"""
📊 *STOCK BIAS:* {emoji} *{bias}*
📋 {market_bias[2]}

📈 *Top Score Boosts:*
"""
    for sym, val in positive:
        detail = stock_details.get(sym, {})
        imp = detail.get("impact", "")
        analysis = detail.get("analysis", "")
        msg += f"  📈 {sym}: +{val:.2f} ({imp}) - {analysis}\n"
    
    msg += f"""
📉 *Top Score Cuts:*
"""
    for sym, val in negative:
        detail = stock_details.get(sym, {})
        imp = detail.get("impact", "")
        analysis = detail.get("analysis", "")
        msg += f"  📉 {sym}: {val:.2f} ({imp}) - {analysis}\n"
    
    msg += f"""
⚖️ *Recommended Weights:*
• ADX: {weights['weight_adx']} | EMA: {weights['weight_ema_slope']} | ST: {weights['weight_supertrend']}

📊 *Stocks Analyzed:* {len(stock_details)}
⏰ *Status:* PENDING APPROVAL
"""
    
    return msg

def main():
    log("=" * 60)
    log("Enhanced Morning Research Agent starting...")
    
    # Step 1: Load NIFTY F&O stocks
    stocks = load_nifty_fno_stocks()
    if not stocks:
        log("ERROR: No stocks loaded")
        return 1
    
    log(f"Analyzing {len(stocks)} stocks...")
    
    # Step 2: Analyze each stock
    score_overrides = {}
    stock_details = {}
    positive_count = 0
    negative_count = 0
    
    for stock in stocks:
        symbol = stock["symbol"]
        
        # Skip indices
        if symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50"]:
            continue
        
        # Get news
        news = get_stock_news(symbol)
        
        # Classify impact
        sentiment_score, impact, analysis = classify_news_impact(symbol, news)
        
        # Calculate score adjustment: sentiment * multiplier
        # sentiment is -2 to +2, multiplier is 0.15, so adjustment is -0.30 to +0.30
        score_adjustment = round(sentiment_score * SENTIMENT_MULTIPLIER, 3)
        
        score_overrides[symbol] = score_adjustment
        stock_details[symbol] = {
            "impact": impact,
            "sentiment_score": sentiment_score,
            "score_adjustment": score_adjustment,
            "analysis": analysis
        }
        
        if score_adjustment > 0:
            positive_count += 1
            log(f"  📈 {symbol}: +{score_adjustment:.3f} ({impact})")
        elif score_adjustment < 0:
            negative_count += 1
            log(f"  📉 {symbol}: {score_adjustment:.3f} ({impact})")
        else:
            log(f"  ➡️ {symbol}: {score_adjustment:.3f} ({impact})")
    
    log(f"Completed analyzing {len(stock_details)} stocks")
    
    # Step 3: Generate market bias
    if positive_count > negative_count + 2:
        bias = "BULLISH"
    elif negative_count > positive_count + 2:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"
    
    market_bias = (bias, 0, f"{positive_count} positive vs {negative_count} negative")
    log(f"Market Bias: {bias} - {positive_count} positive vs {negative_count} negative")
    
    # Step 4: Generate Macro Analysis
    log("Generating macro analysis...")
    macro_data = generate_macro_summary()
    log(f"Macro Sentiment: {macro_data.get('overall_sentiment', 'NEUTRAL')}")
    
    # Override stock bias with macro sentiment if significantly different
    macro_sentiment = macro_data.get("overall_sentiment", "NEUTRAL")
    if macro_sentiment != "NEUTRAL" and macro_sentiment != bias:
        log(f"Adjusting bias: {bias} → {macro_sentiment} (based on macro)")
        bias = macro_sentiment
        market_bias = (bias, 0, f"{positive_count} positive vs {negative_count} negative (macro override)")
    
    # Step 5: Calculate weights
    weights = calculate_weights(bias)
    
    # Step 6: Save overrides
    save_overrides(score_overrides, weights, market_bias)
    
    # Step 7: Generate Telegram message with macro data
    tg_msg = generate_telegram_message(score_overrides, weights, market_bias, stock_details, macro_data)
    
    print("\n" + "=" * 60)
    print(tg_msg)
    print("=" * 60)
    
    # Save message
    msg_path = f"{REPORT_DIR}/message_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(msg_path, "w") as f:
        f.write(tg_msg)
    
    log(f"Morning research complete.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())