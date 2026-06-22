import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from stock_predictor.agent.graph import create_agent_graph

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Multi-Agent Stock Prediction Panel")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
HISTORY_FILE = BASE_DIR / "history.json"

# Request model for prediction inputs
class PredictRequest(BaseModel):
    ticker: str
    press_release: str

# Helper to load and save history
def load_history():
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading history file: {e}")
        return []

def save_to_history(record: dict):
    try:
        history = load_history()
        # Add timestamp and ID
        record["id"] = datetime.now().strftime("%Y%m%d%H%M%S")
        record["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Keep list to max 20 entries
        history.insert(0, record)
        history = history[:20]
        
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving to history file: {e}")

def build_conversation_turn(step: str, node_output: dict, order: int) -> Optional[dict]:
    """
    Builds a reviewable conversation turn from a streamed graph node output.
    Returns None for workflow steps that do not produce expert commentary.
    """
    role_map = {
        "bullish_analyst": {
            "role": "bullish",
            "label": "Bullish Analyst",
            "content_key": "bullish_thesis",
        },
        "bearish_analyst": {
            "role": "bearish",
            "label": "Bearish Analyst",
            "content_key": "bearish_thesis",
        },
        "moderator": {
            "role": "moderator",
            "label": "Moderator",
            "content_key": "synthesis_report",
        },
    }
    turn_config = role_map.get(step)
    if not turn_config:
        return None

    content = node_output.get(turn_config["content_key"])
    if not content:
        return None

    return {
        "step": step,
        "role": turn_config["role"],
        "label": turn_config["label"],
        "iteration": node_output.get("iteration", 0),
        "content": content,
        "order": order,
    }

# Routes
@app.get("/api/history")
async def get_history():
    """
    Returns the list of recent prediction records.
    """
    return load_history()

@app.post("/api/predict/stream")
async def predict_stream(request: PredictRequest):
    """
    Executes the multi-agent LangGraph debate flow and streams the step-by-step
    results to the client using Server-Sent Events (SSE).
    """
    ticker = request.ticker.strip().upper()
    press_release = request.press_release.strip()
    
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")
    if not press_release:
        raise HTTPException(status_code=400, detail="Press release/news content is required")
        
    async def event_generator():
        graph = create_agent_graph()
        
        # Initial empty state matching AgentState model
        state = {
            "ticker": ticker,
            "press_release": press_release,
            "logs": ["Initializing prediction workflow..."],
            "current_step": "init",
            "fundamentals": {},
            "market_data": [],
            "bullish_thesis": "",
            "bearish_thesis": "",
            "synthesis_report": "",
            "prediction": {}
        }
        
        # Send initial SSE heartbeat
        yield {
            "event": "update",
            "data": json.dumps({
                "step": "init",
                "logs": state["logs"],
                "current_step": "init"
            })
        }
        
        final_state = {}
        conversation = []
        
        try:
            # Stream the graph step transitions asynchronously
            async for event in graph.astream(state):
                for node_name, node_output in event.items():
                    # Accumulate state outputs
                    for key, val in node_output.items():
                        if val is not None:
                            final_state[key] = val

                    turn = build_conversation_turn(node_name, node_output, len(conversation) + 1)
                    if turn:
                        conversation.append(turn)
                    
                    # Yield incremental update
                    yield {
                        "event": "update",
                        "data": json.dumps({
                            "step": node_name,
                            "logs": node_output.get("logs", []),
                            "fundamentals": node_output.get("fundamentals"),
                            "market_data": node_output.get("market_data"),
                            "bullish_thesis": node_output.get("bullish_thesis"),
                            "bearish_thesis": node_output.get("bearish_thesis"),
                            "synthesis_report": node_output.get("synthesis_report"),
                            "prediction": node_output.get("prediction"),
                            "conversation_turn": turn,
                            "current_step": node_name
                        })
                    }
            
            # Save the final results to history
            if final_state.get("prediction") and final_state.get("fundamentals"):
                history_record = {
                    "ticker": ticker,
                    "company_name": final_state["fundamentals"].get("name", ticker),
                    "price": final_state["fundamentals"].get("price", 0.0),
                    "pe_ratio": final_state["fundamentals"].get("pe_ratio"),
                    "eps": final_state["fundamentals"].get("eps"),
                    "press_release": press_release,
                    "fundamentals": final_state.get("fundamentals", {}),
                    "market_data": final_state.get("market_data", []),
                    "conversation": conversation,
                    "direction": final_state["prediction"].get("direction"),
                    "change_percent": final_state["prediction"].get("change_percent"),
                    "rating": final_state["prediction"].get("rating"),
                    "confidence": final_state["prediction"].get("confidence"),
                    "synthesis_report": final_state.get("synthesis_report")
                }
                save_to_history(history_record)
                
            # Stream absolute final end signal
            yield {
                "event": "done",
                "data": json.dumps({"status": "completed"})
            }
            
        except Exception as e:
            logger.exception("Error during graph streaming:")
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": str(e),
                    "logs": [f"System Error: {str(e)}", "Aborting workflow execution."]
                })
            }
            
    return EventSourceResponse(event_generator())

# Make sure static directory exists
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files to serve the HTML front-end
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Read port from environment (matches compose and run scripts)
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("stock_predictor.main:app", host=host, port=port, reload=True)
