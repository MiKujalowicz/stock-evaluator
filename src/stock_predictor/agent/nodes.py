import os
import json
import logging
import re
from typing import Dict, Any, Tuple
from stock_predictor.agent.state import AgentState
from stock_predictor.services.data_fetcher import fetch_fundamentals, fetch_chart_data
from stock_predictor.services.sentiment import analyze_text_sentiment

# LangChain imports
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

def get_llm():
    """
    Initializes and returns the configured LLM based on environment variables.
    Returns None if no API keys are present, triggering the rules-based fallback.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key.strip():
            logger.info("Initializing OpenAI ChatOpenAI model.")
            return ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=api_key)
            
    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and api_key.strip():
            logger.info("Initializing Gemini ChatGoogleGenerativeAI model.")
            return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3, api_key=api_key)
            
    logger.info("No LLM API keys found or incorrect configuration. Operating in rules-based Fallback Mode.")
    return None


# =====================================================================
# NODE 1: Fetch Data Node
# =====================================================================
def fetch_data_node(state: AgentState) -> Dict[str, Any]:
    ticker = state.get("ticker", "AAPL").upper()
    logs = state.get("logs", [])
    
    logs.append(f"Starting analysis for ticker: {ticker}")
    logs.append(f"Fetching market data and fundamentals from yfinance...")
    
    fundamentals = fetch_fundamentals(ticker)
    market_data = fetch_chart_data(ticker)
    
    pe = fundamentals.get("pe_ratio", "N/A")
    eps = fundamentals.get("eps", "N/A")
    price = fundamentals.get("price", 0.0)
    
    logs.append(f"Fetched {fundamentals.get('name')}. Price: ${price}, P/E: {pe}, EPS: {eps}")
    
    return {
        "fundamentals": fundamentals,
        "market_data": market_data,
        "logs": logs,
        "current_step": "fetch_data"
    }


# =====================================================================
# NODE 2: Bullish Analyst Node
# =====================================================================
def bullish_analyst_node(state: AgentState) -> Dict[str, Any]:
    ticker = state["ticker"]
    fundamentals = state["fundamentals"]
    press_release = state["press_release"]
    logs = state.get("logs", [])
    
    logs.append("Bullish Analyst (Advocate) is reviewing fundamentals and press release...")
    
    llm = get_llm()
    if llm:
        # LLM Mode
        prompt = f"""You are a Senior Bullish Equity Research Analyst (the Advocate). 
Your job is to build the strongest possible bullish case for {ticker} ({fundamentals.get('name')}) based on the fundamentals and news.

Stock Fundamentals:
{json.dumps(fundamentals, indent=2)}

User Provided News/Press Release:
\"\"\"{press_release}\"\"\"

Instructions:
1. Focus on the positive angles of the news/press release and how it can drive future growth or operational efficiency.
2. Analyze fundamental metrics:
   - Comment on the P/E ratio: if it's low, argue it's undervalued. If it's high, justify it by the company's strong growth trajectory, dominant market position, or technology moat.
   - Comment on EPS, PEG ratio, and market position.
3. Be professional, analytical, and persuasive. Format your response in 2-3 clean markdown paragraphs.
"""
        try:
            response = llm.invoke([
                SystemMessage(content="You are a Wall Street bullish equity research analyst."),
                HumanMessage(content=prompt)
            ])
            bullish_thesis = response.content
        except Exception as e:
            logger.error(f"Error invoking LLM in bullish analyst: {e}")
            bullish_thesis = generate_fallback_bullish_thesis(ticker, fundamentals, press_release)
    else:
        # Fallback Mode
        bullish_thesis = generate_fallback_bullish_thesis(ticker, fundamentals, press_release)
        
    logs.append("Bullish Analyst completed thesis construction.")
    
    return {
        "bullish_thesis": bullish_thesis,
        "logs": logs,
        "current_step": "bullish_analyst"
    }


# =====================================================================
# NODE 3: Bearish Analyst Node
# =====================================================================
def bearish_analyst_node(state: AgentState) -> Dict[str, Any]:
    ticker = state["ticker"]
    fundamentals = state["fundamentals"]
    press_release = state["press_release"]
    bullish_thesis = state["bullish_thesis"]
    logs = state.get("logs", [])
    
    logs.append("Bearish Analyst (Challenger) is reviewing the bullish case and fundamentals...")
    
    llm = get_llm()
    if llm:
        # LLM Mode
        prompt = f"""You are a Senior Bearish Equity Research Analyst (the Challenger). 
Your job is to challenge the bullish case for {ticker} ({fundamentals.get('name')}) and highlight all the key risks and reasons why the stock might be overvalued or face headwinds.

Stock Fundamentals:
{json.dumps(fundamentals, indent=2)}

User Provided News/Press Release:
\"\"\"{press_release}\"\"\"

Bullish Case proposed by your colleague:
\"\"\"{bullish_thesis}\"\"\"

Instructions:
1. Explicitly challenge the assumptions in the bullish thesis.
2. Analyze fundamental risks:
   - Comment on the P/E ratio: if it's high, argue the stock is priced for perfection and highly vulnerable. If it's low, argue it's a value trap due to structural issues.
   - Point out debt levels, sector headwinds, competitor advancements, or operational bottlenecks.
3. Critically analyze the user-provided news/press release (e.g., is it just marketing hype? Will it actually improve the bottom line?).
4. Be professional, critical, and objective. Format your response in 2-3 clean markdown paragraphs.
"""
        try:
            response = llm.invoke([
                SystemMessage(content="You are a Wall Street bearish equity research analyst and risk manager."),
                HumanMessage(content=prompt)
            ])
            bearish_thesis = response.content
        except Exception as e:
            logger.error(f"Error invoking LLM in bearish analyst: {e}")
            bearish_thesis = generate_fallback_bearish_thesis(ticker, fundamentals, press_release, bullish_thesis)
    else:
        # Fallback Mode
        bearish_thesis = generate_fallback_bearish_thesis(ticker, fundamentals, press_release, bullish_thesis)
        
    logs.append("Bearish Analyst completed counter-thesis construction.")
    
    return {
        "bearish_thesis": bearish_thesis,
        "logs": logs,
        "current_step": "bearish_analyst"
    }


# =====================================================================
# NODE 4: Moderator / Synthesizer Node
# =====================================================================
def moderator_node(state: AgentState) -> Dict[str, Any]:
    ticker = state["ticker"]
    fundamentals = state["fundamentals"]
    press_release = state["press_release"]
    bullish_thesis = state["bullish_thesis"]
    bearish_thesis = state["bearish_thesis"]
    logs = state.get("logs", [])
    
    logs.append("Moderator is synthesizing the debate to formulate a final rating and price direction...")
    
    llm = get_llm()
    if llm:
        # LLM Mode
        prompt = f"""You are the Investment Committee Moderator. Your role is to synthesize the debate between the Bullish Analyst and the Bearish Analyst regarding the stock ticker {ticker} ({fundamentals.get('name')}).

Stock Fundamentals:
{json.dumps(fundamentals, indent=2)}

User Provided News/Press Release:
\"\"\"{press_release}\"\"\"

Bullish Thesis:
\"\"\"{bullish_thesis}\"\"\"

Bearish Thesis:
\"\"\"{bearish_thesis}\"\"\"

Instructions:
1. Weigh both arguments and resolve the conflicts using the company's fundamentals (such as P/E, EPS, market trend) and the validity of the press release.
2. Provide a 2-3 paragraph synthesis report summarizing the core takeaways.
3. Output the final prediction parameters in the requested JSON structure.

You MUST return your response in this EXACT format:
REPORT:
[Your synthesis report paragraphs here]

JSON:
{{
  "direction": "UP" or "DOWN" or "STABLE",
  "change_percent": [Float, estimated percentage stock price change over next 30 days, e.g., 4.5],
  "confidence": [Float, confidence level between 0.0 and 1.0, e.g., 0.75],
  "rating": "STRONG BUY" or "BUY" or "HOLD" or "SELL" or "STRONG SELL"
}}
"""
        try:
            response = llm.invoke([
                SystemMessage(content="You are the Head of Research and Moderator of a stock investment committee."),
                HumanMessage(content=prompt)
            ])
            content = response.content
            report, prediction = parse_moderator_output(content)
        except Exception as e:
            logger.error(f"Error invoking LLM in moderator: {e}")
            report, prediction = generate_fallback_synthesis(ticker, fundamentals, press_release, bullish_thesis, bearish_thesis)
    else:
        # Fallback Mode
        report, prediction = generate_fallback_synthesis(ticker, fundamentals, press_release, bullish_thesis, bearish_thesis)
        
    logs.append(f"Moderator compiled final report. Recommendation: {prediction.get('rating')} (Direction: {prediction.get('direction')})")
    logs.append("Analysis workflow completed successfully.")
    
    return {
        "synthesis_report": report,
        "prediction": prediction,
        "logs": logs,
        "current_step": "moderator"
    }


# =====================================================================
# HELPER FUNCTIONS & FALLBACK GENERATORS (P/E & SENTIMENT BASED)
# =====================================================================

def parse_moderator_output(content: str) -> Tuple[str, Dict[str, Any]]:
    """
    Parses the structured output of the moderator LLM.
    Splits into the Markdown report and the JSON prediction object.
    """
    report = ""
    prediction = {
        "direction": "STABLE",
        "change_percent": 0.0,
        "confidence": 0.5,
        "rating": "HOLD"
    }
    
    try:
        # Extract report
        report_match = re.search(r'REPORT:\s*(.*?)(?=JSON:|$)', content, re.DOTALL | re.IGNORECASE)
        if report_match:
            report = report_match.group(1).strip()
        else:
            # Fallback split
            if "JSON:" in content:
                report = content.split("JSON:")[0].replace("REPORT:", "").strip()
            else:
                report = content
                
        # Extract JSON
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            pred_data = json.loads(json_match.group(0))
            # Validate keys
            if "direction" in pred_data: prediction["direction"] = str(pred_data["direction"]).upper()
            if "change_percent" in pred_data: prediction["change_percent"] = round(float(pred_data["change_percent"]), 2)
            if "confidence" in pred_data: prediction["confidence"] = round(float(pred_data["confidence"]), 2)
            if "rating" in pred_data: prediction["rating"] = str(pred_data["rating"]).upper()
            
    except Exception as e:
        logger.warning(f"Error parsing moderator output: {e}. Returning raw content as report and default prediction.")
        report = content if report == "" else report
        
    return report, prediction


def generate_fallback_bullish_thesis(ticker: str, fundamentals: Dict[str, Any], press_release: str) -> str:
    """
    Generates a highly realistic, fundamentals-driven bullish thesis.
    """
    name = fundamentals.get("name", ticker)
    pe = fundamentals.get("pe_ratio")
    eps = fundamentals.get("eps", 0.0)
    sentiment = analyze_text_sentiment(press_release)
    
    p1 = f"**Bullish Thesis for {ticker} ({name}):**\n"
    
    if pe is not None:
        if pe < 20:
            p1 += f"At a trailing Price-to-Earnings (P/E) ratio of **{pe}**, {ticker} represents a compelling value play. Compared to general sector averages, this multiple indicates the stock is currently undervalued relative to its earnings power of **${eps:.2f} per share**."
        else:
            p1 += f"While a trailing P/E ratio of **{pe}** reflects a premium multiple, this valuation is fully justified by the company's leading market share, technological advantages, and strong return on equity. Investors are paying for a compounding machine that consistently delivers earnings."
    else:
        p1 += f"Although the trailing P/E is not currently reported, the stock's operational footprint and market capitalisation of **${fundamentals.get('market_cap', 0):,}** support a long-term bullish outlook as its market reach expands."

    p2 = ""
    if sentiment["label"] == "BULLISH":
        p2 = f"The recent press information highlights positive catalysts. Specifically, indicators of {sentiment['compound']:.2f} sentiment suggest strong product demand, strategic partnerships, or operational efficiencies. This announcement serves as a growth driver that will expand margins and boost top-line revenue."
    else:
        p2 = f"Despite neutral or mixed near-term news sentiment, {name} maintains a robust product pipeline and stable cash flows. Any temporary market flatlining presents a prime buying opportunity for long-term investors before the next product cycle accelerates."
        
    p3 = f"In conclusion, the combination of healthy financials (EPS of ${eps:.2f}) and positive core assets provides a high-conviction setup. We believe the intrinsic value of {ticker} lies significantly above current market price levels."
    
    return f"{p1}\n\n{p2}\n\n{p3}"


def generate_fallback_bearish_thesis(ticker: str, fundamentals: Dict[str, Any], press_release: str, bullish_thesis: str) -> str:
    """
    Generates a highly realistic, fundamentals-driven bearish thesis challenging the bull.
    """
    name = fundamentals.get("name", ticker)
    pe = fundamentals.get("pe_ratio")
    eps = fundamentals.get("eps", 0.0)
    sentiment = analyze_text_sentiment(press_release)
    
    p1 = f"**Bearish Counter-Thesis for {ticker} ({name}):**\n"
    p1 += "The bullish advocate's perspective overlooks critical micro and macro risks. "
    
    if pe is not None:
        if pe > 25:
            p1 += f"Specifically, a P/E multiple of **{pe}** is heavily bloated. The stock is priced for perfection, leaving zero margin for error. If the company fails to maintain explosive double-digit growth, a sharp multiple contraction is inevitable."
        else:
            p1 += f"Although the trailing P/E is apparently low at **{pe}**, this is a classic value trap. Low multiples often reflect declining market share, shrinking margins, or structural industry decline that will suppress future EPS (currently at **${eps:.2f}**)."
    else:
        p1 += f"The absence of standard PE multiples indicates earnings instability or negative cash flows, which introduces considerable speculative risk for retail investors."

    p2 = ""
    if sentiment["label"] == "BULLISH":
        p2 = f"Furthermore, the bullish analyst is overly optimistic about the recent press announcement. In reality, statements regarding new initiatives are largely public relations exercises. Translating these announcements into actual bottom-line net income will take quarters, if not years, and involves massive execution risks."
    else:
        p2 = f"The downbeat news sentiment confirms that the company is facing stiff headwinds. Supply chain bottlenecks, inflation, and growing competitor pressure are eroding its core business, and management has not shown a clear roadmap to reverse this trend."
        
    p3 = f"To summarize, buying {ticker} at these levels ignores valuation realities and key execution risks. We recommend a cautious stance, as macro headwinds are likely to drag the stock price down in the coming months."
    
    return f"{p1}\n\n{p2}\n\n{p3}"


def generate_fallback_synthesis(ticker: str, fundamentals: Dict[str, Any], press_release: str, bullish_thesis: str, bearish_thesis: str) -> Tuple[str, Dict[str, Any]]:
    """
    Synthesizes the bullish and bearish theses based on fundamentals.
    """
    name = fundamentals.get("name", ticker)
    pe = fundamentals.get("pe_ratio")
    eps = fundamentals.get("eps", 0.0)
    sentiment = analyze_text_sentiment(press_release)
    
    # Calculate a dynamic direction and score
    # Bull score starts with sentiment compound (-1 to +1)
    score = sentiment["compound"] * 1.5
    
    # Adjust based on P/E ratio
    if pe is not None:
        if pe < 15:
            score += 0.5  # undervalued, positive influence
        elif pe > 40:
            score -= 0.5  # overvalued, negative influence
            
    # Decide direction and rating
    if score >= 0.4:
        direction = "UP"
        rating = "BUY" if score < 1.0 else "STRONG BUY"
        change_percent = round(2.0 + score * 5.0, 2)
        confidence = round(0.6 + (score * 0.1), 2)
    elif score <= -0.4:
        direction = "DOWN"
        rating = "SELL" if score > -1.0 else "STRONG SELL"
        change_percent = round(-2.0 + score * 5.0, 2)
        confidence = round(0.6 - (score * 0.1), 2)
    else:
        direction = "STABLE"
        rating = "HOLD"
        change_percent = round(score * 2.0, 2)
        confidence = 0.70
        
    confidence = min(0.95, max(0.3, confidence))
    
    p1 = f"**Investment Committee Synthesis for {ticker} ({name}):**\n"
    p1 += f"The committee has evaluated the debate between the Bullish Advocate and the Bearish Challenger. The core question hinges on whether the recent press release provides a strong enough catalyst to outweigh {name}'s valuation metrics."
    
    p2 = ""
    if direction == "UP" or direction == "STRONG BUY":
        p2 = f"On balance, the bullish analyst's argument is more persuasive. The positive sentiment in the press release represents a material upgrade to future cash flows. At the same time, the stock's fundamental structure (EPS of **${eps:.2f}**) provides a solid safety margin. While the bearish concerns about valuation multiples are noted, the company's growth runway justifies the premium."
    elif direction == "DOWN" or direction == "STRONG SELL":
        p2 = f"On balance, the bearish analyst's cautionary stance is vindicated. The company's high valuation (P/E ratio of **{pe}**) is unsupported by the news release, which contains mostly cosmetic updates rather than concrete revenue catalysts. With macro headwinds persisting, we expect downward pressure on the stock."
    else:
        p2 = f"The debate reveals that the stock is currently fairly valued. The positive catalysts highlighted by the bullish advocate are offset by the structural and valuation risks raised by the bearish challenger (specifically the P/E of **{pe}** and potential EPS compression). We believe the stock will trade sideways in the near term."
        
    p3 = f"**Conclusion**: We issue a **{rating}** rating on {ticker} with a price direction outlook of **{direction}** ({change_percent:+.2f}% expected movement over the next 30 days) and a confidence score of **{confidence * 100:.0f}%**."
    
    report = f"{p1}\n\n{p2}\n\n{p3}"
    
    prediction = {
        "direction": direction,
        "change_percent": change_percent,
        "confidence": confidence,
        "rating": rating
    }
    
    return report, prediction
