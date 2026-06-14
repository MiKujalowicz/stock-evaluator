import json
import logging
import re
from typing import Dict, Any, Tuple
from langchain_core.messages import SystemMessage, HumanMessage
from stock_predictor.agent.state import AgentState
from stock_predictor.services.sentiment import analyze_text_sentiment
from stock_predictor.agent.nodes.base import get_llm

logger = logging.getLogger(__name__)

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
