from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from typing import Dict, Any
from google.cloud.dialogflow_v2.services.sessions import SessionsClient
from google.cloud.dialogflow_v2.types import TextInput, QueryInput
from google.oauth2 import service_account
import os
import json

# --- Authentication and Project Setup ---

DIALOGFLOW_PROJECT_ID = 'anurag-chatbot-project'
DIALOGFLOW_SESSION_ID = 'anurag-chatbot-session' 
DIALOGFLOW_LANGUAGE_CODE = 'en'

KEY_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'auth_key.json')

# Create Credentials object
try:
    CREDENTIALS = service_account.Credentials.from_service_account_file(KEY_FILE_PATH)
    print(f"Service Account: {CREDENTIALS.service_account_email}")
except FileNotFoundError:
    print(f"FATAL ERROR: Authentication key file not found at {KEY_FILE_PATH}")
    CREDENTIALS = None
except Exception as e:
    print(f"FATAL ERROR during credential loading: {e}")
    CREDENTIALS = None

# Import data service
try:
    from data_service import retrieve_contextual_answer, load_knowledge_base 
except ImportError:
    from .data_service import retrieve_contextual_answer, load_knowledge_base

# --- FastAPI Setup ---

app = FastAPI(title="Anurag University Chatbot Fulfillment (Dialogflow ES)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- FastAPI Startup Event ---
@app.on_event("startup")
def startup_event():
    """Load the knowledge base data when the FastAPI application starts."""
    print("Executing startup event: Loading knowledge base...")
    load_knowledge_base()

# --- Pydantic Models ---

class ChatRequest(BaseModel):
    text: str

class ChatResponse(BaseModel):
    response: str
    intent: str
    language: str

# --- Enhanced Dialogflow Helper ---

def detect_intent_with_fallback(text: str):
    """
    Enhanced Dialogflow detection with intelligent fallback to local knowledge base
    """
    if not CREDENTIALS:
        return None, "System.AuthError"
    
    try:
        session_client = SessionsClient(credentials=CREDENTIALS)
        session_path = session_client.session_path(DIALOGFLOW_PROJECT_ID, DIALOGFLOW_SESSION_ID)

        text_input = TextInput(text=text, language_code=DIALOGFLOW_LANGUAGE_CODE)
        query_input = QueryInput(text=text_input)

        response = session_client.detect_intent(
            request={"session": session_path, "query_input": query_input}
        )
        
        fulfillment_text = response.query_result.fulfillment_text
        detected_intent = response.query_result.intent.display_name
        confidence = response.query_result.intent_detection_confidence
        
        print(f"Dialogflow Response - Intent: {detected_intent}, Confidence: {confidence}")
        
        # Check if it's a fallback intent or low confidence
        if (detected_intent == "Default Fallback Intent" or 
            confidence < 0.5 or 
            "I didn't get that" in fulfillment_text or
            "Can you say it again" in fulfillment_text):
            print("Dialogflow returned fallback, using local knowledge base...")
            return None, "Local.Fallback"
        
        return fulfillment_text, detected_intent
        
    except Exception as e:
        print(f"Dialogflow API error: {e}")
        return None, "System.Error"

# --- Endpoints ---

@app.get("/")
async def root():
    return {"message": "Anurag University Chatbot Fulfillment (ES) is running!", "status": "OK"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    test_query = "What is the tuition fee for B.Tech?"
    dialogflow_response, intent = detect_intent_with_fallback(test_query)
    
    return {
        "status": "healthy" if CREDENTIALS else "no_credentials",
        "project_id": DIALOGFLOW_PROJECT_ID,
        "dialogflow_test": {
            "query": test_query,
            "response": dialogflow_response[:100] + "..." if dialogflow_response else "None",
            "intent": intent
        }
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_api(request: ChatRequest):
    """
    Enhanced chat endpoint with smart Dialogflow + local knowledge base fallback
    """
    user_query = request.text.strip()
    print(f"CHAT API: Processing query: '{user_query}'")
    
    # Step 1: Try Dialogflow first
    dialogflow_response, detected_intent = detect_intent_with_fallback(user_query)
    
    # Step 2: If Dialogflow provides a good response, use it
    if dialogflow_response and detected_intent != "Local.Fallback":
        print(f"Using Dialogflow response from intent: {detected_intent}")
        return ChatResponse(
            response=dialogflow_response,
            intent=detected_intent,
            language=DIALOGFLOW_LANGUAGE_CODE
        )
    
    # Step 3: Fallback to local knowledge base
    print("Using local knowledge base for response...")
    local_response = retrieve_contextual_answer(user_query, "UserQuery")
    
    # Enhance the local response with context
    enhanced_response = local_response
    if "could not find a specific answer" in local_response:
        enhanced_response = (
            f"I found some information in our knowledge base:\n\n{local_response}\n\n"
            "You can also visit the official Anurag University website or contact admissions at +91-8181057057 for more specific queries."
        )
    
    return ChatResponse(
        response=enhanced_response,
        intent="Local.KnowledgeBase",
        language="en"
    )

# --- Run the server ---
if __name__ == "__main__":
    print("\nStarting Enhanced FastAPI Server for Anurag University Chatbot")
    print(f"Project: {DIALOGFLOW_PROJECT_ID}")
    print(f"Service Account: {CREDENTIALS.service_account_email if CREDENTIALS else 'None'}")
    print("Server running on: http://127.0.0.1:8000")
    print("\nAvailable endpoints:")
    print("  GET  /health - Check server and Dialogflow status")
    print("  POST /chat   - Main chat endpoint")
    print("  GET  /       - Root endpoint")
    
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)