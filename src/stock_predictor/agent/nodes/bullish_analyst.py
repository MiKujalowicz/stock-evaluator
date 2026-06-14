import json
import logging
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from stock_predictor.agent.state import AgentState
from stock_predictor.services.sentiment import analyze_text_sentiment
from stock_predictor.agent.nodes.base import get_llm

logger = logging.getLogger(__name__)

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

def bullish_analyst_node(state: AgentState) -> Dict[str, Any]:
    ticker = state["ticker"]
    fundamentals = state["fundamentals"]
    press_release = state["press_release"]
    iteration = state.get("iteration", 0)
    bearish_thesis = state.get("bearish_thesis", "")
    logs = state.get("logs", [])
    
    logs.append(f"Bullish Analyst (Advocate) is constructing thesis (Iteration {iteration + 1})...")
    
    llm = get_llm()
    if llm:
        # LLM Mode
        prompt = f"""You are a Senior Bullish Equity Research Analyst (the Advocate). 
Your job is to build the strongest possible bullish case for {ticker} ({fundamentals.get('name')}) based on the fundamentals and news.

Stock Fundamentals:
{json.dumps(fundamentals, indent=2)}

User Provided News/Press Release:
\"\"\"{press_release}\"\"\"
"""
        if iteration > 0 and bearish_thesis:
            prompt += f"""
Previous Bearish Counter-Thesis from your opponent:
\"\"\"{bearish_thesis}\"\"\"

Instructions:
1. Address the concerns raised by the Challenger in their previous counter-thesis.
2. Defend and strengthen the bullish case based on the fundamentals and news.
3. Be professional, analytical, and persuasive. Format your response in 2-3 clean markdown paragraphs.
"""
        else:
            prompt += """
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
