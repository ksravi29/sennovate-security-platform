import os
import re
import requests
from fastapi import FastAPI, HTTPException, Body

app = FastAPI(title="Sennovate AI Security Platform")

def inspect_and_redact_payload(text: str):
    SECRET_PATTERN = r'(?:key|secret|password|passwd|token)(?: *= *| *\: *)(?:["\'\w\-]{16,})'
    EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    SSN_PATTERN = r'\b\d{3}-\d{2}-\d{4}\b'
    
    violations = []
    
    if re.search(SECRET_PATTERN, text, re.IGNORECASE):
        violations.append("Internal Credentials/API Key")
        
    redacted_text = text
    if re.search(EMAIL_PATTERN, text):
        violations.append("Email Address PII")
        redacted_text = re.sub(EMAIL_PATTERN, "[REDACTED_EMAIL]", redacted_text)
        
    if re.search(SSN_PATTERN, text):
        violations.append("Social Security Number PII")
        redacted_text = re.sub(SSN_PATTERN, "[REDACTED_SSN]", redacted_text)
        
    classification = "CONFIDENTIAL" if violations else "GENERAL_BUSINESS"
    
    return {
        "is_safe": len(violations) == 0,
        "violations": violations,
        "redacted_text": redacted_text,
        "classification": classification
    }

@app.post("/api/v1/secure-chat")
def secure_chat_endpoint(prompt: str = Body(..., embed=True)):
    audit = inspect_and_redact_payload(prompt)
    
    if "Internal Credentials/API Key" in audit["violations"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Security Policy Violation: Upload blocked. Detected: {audit['violations']}"
        )
    
    safe_prompt = audit["redacted_text"]
    api_url = "https://openrouter.ai/api/v1/chat/completions"
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "openai/gpt-4o", 
        "messages": [{"role": "user", "content": safe_prompt}],
        "provider": {
            "order": ["Azure", "Bedrock"],
            "data_collection": "deny"
        },
        "zdr": True,
        "max_tokens": 4096
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        res_json = response.json()
        
        res_json["sennovate_governance"] = {
            "data_classification": audit["classification"],
            "local_pii_scrubbed": len(audit["violations"]) > 0,
            "detected_signatures": audit["violations"]
        }
        return res_json
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))