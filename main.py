import os
import requests
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Sennovate AI Security Platform")

@app.post("/api/v1/secure-chat")
def secure_chat_endpoint(prompt: str):
    """
    Sennovate backend layer forcing Zero Data Retention (ZDR)
    via enterprise paths (Azure OpenAI / Amazon Bedrock).
    """
    api_url = "https://openrouter.ai/api/v1/chat/completions"
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "openai/gpt-4o", 
        "messages": [{"role": "user", "content": prompt}],
        "provider": {
            "order": ["Azure", "Bedrock"], # Nishanth's UI screenshot paths
            "data_collection": "deny"      # Hard block on training data
        },
        "zdr": True,        # Enforces platform Zero Data Retention
        "max_tokens": 4096  # Completely clears the 30-token limit constraint
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))