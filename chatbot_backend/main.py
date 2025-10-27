from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Dict, Any
import json
from google.cloud.dialogflow_v2.services.sessions import SessionsClient
from google.cloud.dialogflow_v2.types import TextInput, QueryInput
from google.oauth2 import service_account
import os
import re

# Import intent handlers (use package-relative imports)
from .database import get_database, close_database
from .intents.placement_record_d import handle_placement_record
from .intents.iiic_partners_d import handle_iiic_partners
from .intents.merit_scholarship_rank_d import handle_merit_scholarship_rank
from .intents.engineering_course_description_d import handle_engineering_course_description
from .intents.hostel_fee_d import handle_hostel_fee

# Import data service (package-relative)
from .data_service import retrieve_contextual_answer, load_knowledge_base

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

# --- FastAPI Setup ---

app = FastAPI(title="Anurag University Chatbot Fulfillment (Dialogflow ES)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Intent Handler Mapping ---
INTENT_HANDLERS = {
    'Placement_Record_D': handle_placement_record,
    'IIIC_Partners_D': handle_iiic_partners,
    'Merit_Scholarship_Rank_D': handle_merit_scholarship_rank,
    'Engineering_Course_Description_D': handle_engineering_course_description,
    'Hostel_Fee_D': handle_hostel_fee,
}

# --- Pydantic Models ---

class Intent(BaseModel):
    # Dialogflow sends both 'name' (resource path) and 'displayName'.
    # We need 'displayName' for routing to local intent handlers.
    name: str | None = None
    displayName: str | None = None
    
    class Config:
        # Allow both camelCase and snake_case
        populate_by_name = True

class QueryResult(BaseModel):
    queryText: str
    intent: Intent
    languageCode: str
    parameters: Dict[str, Any]
    
    class Config:
        populate_by_name = True

class DialogflowESRequest(BaseModel):
    responseId: str
    queryResult: QueryResult
    
    class Config:
        populate_by_name = True

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
        
        print(f"Dialogflow Response - Intent: {detected_intent}, Confidence: {confidence}, Response: {fulfillment_text[:100] if fulfillment_text else 'None'}...")
        
        # Only use fallback for actual fallback intents, not for low confidence on valid intents
        if (detected_intent == "Default Fallback Intent" or 
            "I didn't get that" in fulfillment_text or
            "Can you say it again" in fulfillment_text):
            print("Dialogflow returned explicit fallback, using local processing...")
            return None, "Local.Fallback"
        
        # Even with lower confidence, if we got a specific intent and response, use it
        if detected_intent and detected_intent != "Default Fallback Intent" and fulfillment_text:
            return fulfillment_text, detected_intent
        else:
            return None, "Local.Fallback"
        
    except Exception as e:
        print(f"Dialogflow API error: {e}")
        return None, "System.Error"

# --- Query Processing Functions ---

def extract_course_from_query(query: str) -> str:
    """Extract course name from query"""
    query_upper = query.upper()
    if 'EEE' in query_upper or 'ELECTRICAL' in query_upper:
        return 'EEE'
    elif 'CSE' in query_upper or 'COMPUTER' in query_upper:
        return 'CSE'
    elif 'AI' in query_upper or 'ARTIFICIAL INTELLIGENCE' in query_upper:
        return 'AI'
    elif 'CIVIL' in query_upper:
        return 'CIVIL'
    elif 'MECH' in query_upper or 'MECHANICAL' in query_upper:
        return 'MECHANICAL'
    elif 'ECE' in query_upper or 'ELECTRONICS' in query_upper:
        return 'ECE'
    elif 'PHARMACY' in query_upper or 'B.PHARM' in query_upper:
        return 'B.PHARMACY'
    return ''

def extract_hostel_params(query: str) -> Dict[str, Any]:
    """Extract hostel parameters from query"""
    params = {}
    query_lower = query.lower()
    
    if 'male' in query_lower or 'boy' in query_lower:
        params['gender'] = 'male'
    elif 'female' in query_lower or 'girl' in query_lower:
        params['gender'] = 'female'
        
    if 'ac' in query_lower:
        params['accommodationtype'] = '4 sharing with AC'
    elif 'attached' in query_lower or 'bath' in query_lower:
        params['accommodationtype'] = '4 sharing attached'
    elif '5' in query_lower or 'five' in query_lower:
        params['accommodationtype'] = '5 sharing'
    elif '4' in query_lower or 'four' in query_lower:
        params['accommodationtype'] = '4 sharing'
        
    return params

def extract_placement_params(query: str) -> Dict[str, Any]:
    """Extract placement parameters from query"""
    params = {}
    # Extract year if mentioned (e.g., "2024 placements")
    year_match = re.search(r'20\d{2}', query)
    if year_match:
        params['year'] = year_match.group()
    return params

def extract_scholarship_params(query: str) -> Dict[str, Any]:
    """Extract scholarship parameters from query"""
    params = {}
    query_upper = query.upper()
    
    if 'EAPCET' in query_upper:
        params['entranceexam'] = 'EAPCET'
    elif 'JEE' in query_upper:
        params['entranceexam'] = 'JEE'
    elif 'ANURAG' in query_upper or 'ANURAGCET' in query_upper:
        params['entranceexam'] = 'ANURAGCET'
    
    # Extract rank if mentioned
    rank_match = re.search(r'rank\s*(\d+)', query, re.IGNORECASE)
    if rank_match:
        params['number'] = rank_match.group(1)
    
    return params

async def process_query_directly(query_text: str) -> str:
    """
    Process query directly through intent handlers without Dialogflow
    """
    try:
        query_lower = query_text.lower()
        query_upper = query_text.upper()
        
        # Engineering Course Description
        if any(keyword in query_upper for keyword in ['EEE', 'CSE', 'AI', 'CIVIL', 'MECHANICAL', 'ECE', 'PHARMACY', 'COURSE', 'PROGRAM', 'DETAILS']):
            course = extract_course_from_query(query_text)
            if course:
                params = {'engineeringcourse': course, 'entranceexam': ''}
                return await handle_engineering_course_description(params)
            else:
                return "Which engineering program are you interested in? Please specify the course name (e.g., EEE, CSE, AI, Civil, Mechanical, ECE, or B.Pharmacy)."
        
        # Hostel Fees
        elif any(keyword in query_lower for keyword in ['hostel', 'accommodation', 'room', 'fee', 'stay']):
            params = extract_hostel_params(query_text)
            return await handle_hostel_fee(params)
        
        # Placement Records
        elif any(keyword in query_lower for keyword in ['placement', 'job', 'recruitment', 'company', 'hire']):
            params = extract_placement_params(query_text)
            return await handle_placement_record(params)
        
        # Scholarship
        elif any(keyword in query_lower for keyword in ['scholarship', 'merit', 'rank', 'concession', 'fee waiver']):
            params = extract_scholarship_params(query_text)
            return await handle_merit_scholarship_rank(params)
        
        # IIIC Partners
        elif any(keyword in query_lower for keyword in ['partner', 'mou', 'industry', 'company', 'collaboration']):
            params = {}
            return await handle_iiic_partners(params)
        
    except Exception as e:
        print(f"Error in direct query processing: {e}")
    
    return None

# --- Webhook Endpoint for Dynamic Intents ---

@app.post("/webhook")
async def dialogflow_webhook(request: Request):
    """
    Handles Dialogflow webhook calls for dynamic intents
    """
    # Parse raw JSON first to debug what Dialogflow sends
    try:
        raw_payload = await request.json()
        print(f"RAW WEBHOOK PAYLOAD: {json.dumps(raw_payload, indent=2)}")
    except Exception as e:
        print(f"Error parsing webhook payload: {e}")
        return {"fulfillmentText": "Error parsing request"}
    
    # Extract fields manually from raw payload
    try:
        query_result = raw_payload.get('queryResult', {})
        intent_data = query_result.get('intent', {})
        
        # Try to get displayName first, then fall back to name
        intent_name = intent_data.get('displayName') or intent_data.get('name', 'UserQuery')
        
        # If we still have a resource path, it means displayName wasn't provided
        if intent_name and intent_name.startswith('projects/'):
            print(f"WARNING: Received intent resource path instead of displayName: {intent_name}")
            intent_name = "UserQuery"
        
        parameters = query_result.get('parameters', {})
        query_text = query_result.get('queryText', '')
        language_code = query_result.get('languageCode', 'en')
        
        # Add query_text to parameters so handlers can use it for fallback parsing
        parameters['query_text'] = query_text
        
        print(f"WEBHOOK: Intent: {intent_name}, Query: '{query_text}', Params: {parameters}")
        
        # Check if we have a handler for this dynamic intent
        if intent_name in INTENT_HANDLERS:
            try:
                # Call the appropriate intent handler
                response_text = await INTENT_HANDLERS[intent_name](parameters)
                
                # Add multilingual support if needed
                if language_code != 'en':
                    multilingual_note = ""
                    if 'hi' in language_code:
                        multilingual_note = "Hello! Important information: " 
                    elif 'te' in language_code:
                        multilingual_note = "Hello! Important information: "
                    response_text = multilingual_note + response_text
                    
            except Exception as e:
                print(f"Error in intent handler {intent_name}: {e}")
                import traceback
                traceback.print_exc()
                response_text = f"I encountered an error while processing your request for {intent_name}. Please try again later."
        else:
            # Use local knowledge base as fallback
            response_text = retrieve_contextual_answer(query_text, intent_name)
            print(f"No specific handler for {intent_name}, using knowledge base")
        
        return {"fulfillmentText": response_text}
        
    except Exception as e:
        print(f"Error processing webhook: {e}")
        import traceback
        traceback.print_exc()
        return {"fulfillmentText": "I encountered an error processing your request. Please try again."}

# --- Endpoints ---

@app.on_event("startup")
async def startup_event():
    """Load the knowledge base data and connect to MongoDB when the FastAPI application starts."""
    print("Executing startup event: Loading knowledge base and connecting to MongoDB...")

    # Test MongoDB connection
    try:
        db = await get_database()
        if db is not None:
            print("✅ MongoDB connection successful!")
        else:
            print("❌ MongoDB connection failed (database is None)")
    except Exception as e:
        print(f"❌ MongoDB connection error: {e}")

    load_knowledge_base()
    print("Intent handlers loaded:", list(INTENT_HANDLERS.keys()))

@app.on_event("shutdown")
async def shutdown_event():
    """Close MongoDB connection on shutdown"""
    await close_database()

@app.get("/")
async def root():
    return {
        "message": "Anurag University Chatbot Fulfillment (ES) is running!", 
        "status": "OK",
        "dynamic_intents": list(INTENT_HANDLERS.keys())
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    test_query = "What is the tuition fee for B.Tech?"
    dialogflow_response, intent = detect_intent_with_fallback(test_query)
    
    return {
        "status": "healthy" if CREDENTIALS else "no_credentials",
        "project_id": DIALOGFLOW_PROJECT_ID,
        "dynamic_intents_loaded": len(INTENT_HANDLERS),
        "dialogflow_test": {
            "query": test_query,
            "response": dialogflow_response[:100] + "..." if dialogflow_response else "None",
            "intent": intent
        }
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_api(request: ChatRequest):
    """
    Smart chat endpoint that prioritizes direct intent processing
    """
    user_query = request.text.strip()
    print(f"CHAT API: Processing query: '{user_query}'")
    
    # Step 1: Try direct intent processing first (fastest)
    direct_response = await process_query_directly(user_query)
    if direct_response:
        print(f"✅ Using direct intent processing")
        return ChatResponse(
            response=direct_response,
            intent="Direct.Processed",
            language="en"
        )
    
    # Step 2: Try Dialogflow for more complex queries
    dialogflow_response, detected_intent = detect_intent_with_fallback(user_query)
    if dialogflow_response and detected_intent not in ["Local.Fallback", "System.Error", "System.AuthError"]:
        print(f"✅ Using Dialogflow response from intent: {detected_intent}")
        return ChatResponse(
            response=dialogflow_response,
            intent=detected_intent,
            language=DIALOGFLOW_LANGUAGE_CODE
        )
    
    # Step 3: Final fallback to local knowledge base
    print("📚 Using local knowledge base for response...")
    local_response = retrieve_contextual_answer(user_query, "UserQuery")
    
    # Enhance the local response with context
    if "could not find a specific answer" in local_response.lower():
        enhanced_response = (
            f"I found some information in our knowledge base:\n\n{local_response}\n\n"
            "You can also visit the official Anurag University website or contact admissions at +91-8181057057 for more specific queries."
        )
    else:
        enhanced_response = local_response
    
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
    print(f"Dynamic Intents Loaded: {len(INTENT_HANDLERS)}")
    print("Server running on: http://127.0.0.1:8000")
    print("\nAvailable endpoints:")
    print("  GET  /health - Check server and Dialogflow status")
    print("  POST /chat   - Main chat endpoint")
    print("  POST /webhook - Dialogflow webhook endpoint")
    print("  GET  /       - Root endpoint")
    
    # When invoked directly, make sure to reference the package module path
    uvicorn.run("chatbot_backend.main:app", host="127.0.0.1", port=8000, reload=True)