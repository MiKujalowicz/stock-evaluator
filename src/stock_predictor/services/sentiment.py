import logging
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Fallback positive/negative keywords for rule-based sentiment when vader is not available
BULLISH_WORDS = {
    "growth", "growth-stage", "innovative", "expansion", "profit", "profitable", "revenue", "surge",
    "undervalued", "buy", "bullish", "record-breaking", "success", "successful", "beats", "earnings",
    "dividend", "upside", "outperform", "opportunity", "partnership", "acquire", "merger", "breakthrough",
    "leader", "strong", "positive", "gain", "gains", "demand", "upgrade", "unveil", "launches"
}

BEARISH_WORDS = {
    "risk", "risky", "loss", "decline", "debt", "lawsuit", "investigation", "bearish", "sell", "overvalued",
    "downside", "miss", "missed", "drop", "plunge", "concern", "concerns", "inflation", "recession",
    "headwind", "headwinds", "weak", "warns", "warning", "competition", "compete", "supply-chain",
    "regulatory", "investigate", "lawsuit", "layoff", "layoffs", "restructuring"
}

class SimpleSentimentAnalyzer:
    """
    A simple dictionary-based sentiment analyzer as a fallback.
    """
    def polarity_scores(self, text: str) -> Dict[str, float]:
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        if not words:
            return {"pos": 0.0, "neg": 0.0, "neu": 1.0, "compound": 0.0}
            
        pos_count = sum(1 for w in words if w in BULLISH_WORDS)
        neg_count = sum(1 for w in words if w in BEARISH_WORDS)
        
        total = pos_count + neg_count + 1e-9
        
        # Simple compound mapping between -1.0 and +1.0
        compound = (pos_count - neg_count) / total
        
        pos_frac = pos_count / len(words)
        neg_frac = neg_count / len(words)
        neu_frac = 1.0 - (pos_frac + neg_frac)
        
        return {
            "pos": round(pos_frac, 3),
            "neg": round(neg_frac, 3),
            "neu": round(max(0.0, neu_frac), 3),
            "compound": round(compound, 3)
        }

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_ANALYZER = SentimentIntensityAnalyzer()
    HAS_VADER = True
    logger.info("Successfully loaded VADER SentimentIntensityAnalyzer.")
except ImportError:
    VADER_ANALYZER = SimpleSentimentAnalyzer()
    HAS_VADER = False
    logger.warning("VADER sentiment library not installed. Using simple fallback sentiment analyzer.")

def analyze_text_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyzes the sentiment of a text block and returns positive, negative, neutral,
    and compound sentiment scores.
    """
    if not text or not text.strip():
        return {
            "pos": 0.0,
            "neg": 0.0,
            "neu": 1.0,
            "compound": 0.0,
            "label": "NEUTRAL"
        }
        
    scores = VADER_ANALYZER.polarity_scores(text)
    
    # Label mapping based on compound score
    compound = scores.get("compound", 0.0)
    if compound >= 0.05:
        label = "BULLISH"
    elif compound <= -0.05:
        label = "BEARISH"
    else:
        label = "NEUTRAL"
        
    return {
        "pos": scores.get("pos", 0.0),
        "neg": scores.get("neg", 0.0),
        "neu": scores.get("neu", 1.0),
        "compound": compound,
        "label": label
    }
