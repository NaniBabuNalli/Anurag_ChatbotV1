

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware # CORS Import
import motor.motor_asyncio
import os
from typing import Dict, Any, Union
import json
import uuid # For generating session IDs
from dotenv import load_dotenv

# Install this library: pip install google-cloud-dialogflow
from google.cloud import dialogflow


# 1. Configuration & Setup
# =================================================================

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://22eg106b52_db_user:ID1HC1Jt7iSQTZD8@anurag-chatbot.1zycn8n.mongodb.net/") 
DATABASE_NAME = "university_db" # CONFIRMED DB NAME

app = FastAPI(title="Anurag Chatbot Webhook")

# CORS CONFIGURATION: Allows the frontend (index.html) to call the FastAPI server
origins = ["*"]  # Allow all origins for local development. RESTRICT THIS IN PRODUCTION!

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for database connection
client: motor.motor_asyncio.AsyncIOMotorClient = None
db: motor.motor_asyncio.AsyncIOMotorDatabase = None

# 2. Connection Handlers (Startup/Shutdown)
# =================================================================

@app.on_event("startup")
async def startup_db_client():
    """Connect to MongoDB on FastAPI startup."""
    global client, db
    print("Attempting to connect to MongoDB...")
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        client.server_info()
        db = client[DATABASE_NAME]
        print(f"Successfully connected to MongoDB Atlas! Database: {DATABASE_NAME}")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        
@app.on_event("shutdown")
async def shutdown_db_client():
    """Close MongoDB connection on FastAPI shutdown."""
    global client
    if client:
        client.close()
        print("MongoDB connection closed.")

# 3. Helper Functions (Optimized for Dialogflow ES)
# =================================================================

def format_dialogflow_response(response_text: str) -> JSONResponse:
    """Formats a text string into a Dialogflow ES-compliant JSON response for the Webhook."""
    return JSONResponse(content={
        "fulfillmentText": response_text
    })

def get_intent_name(payload: Dict[str, Any]) -> Union[str, None]:
    """Extracts the intent display name from the Dialogflow ES payload."""
    return payload.get('queryResult', {}).get('intent', {}).get('displayName')

def get_parameters(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts parameters (entities) from the Dialogflow ES payload."""
    return payload.get('queryResult', {}).get('parameters', {})


def detect_intent_texts(project_id, session_id, texts, language_code):
    """Returns the result of detect intent with text as input."""
    
    # 1. Create a session client
    # Use the correct V2 session client
    session_client = dialogflow.SessionsClient()
    
    # 2. Define the session path
    # Use the session_path method from the client
    session_path = session_client.session_path(project_id, session_id)
    
    # 3. Process the text input
    # Use the classes directly from the imported dialogflow package
    text_input = dialogflow.TextInput(text=texts, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)

    try:
        # 4. Send the query to the Dialogflow API
        response = session_client.detect_intent(session=session_path, query_input=query_input)
        
        return {
            "fulfillment_text": response.query_result.fulfillment_text,
            "intent_name": response.query_result.intent.display_name,
            "confidence": response.query_result.intent_detection_confidence
        }
    except Exception as e:
        print(f"Dialogflow API Error: {e}")
        return None


# 4. WEBHOOK ENDPOINT (Called BY Dialogflow)
# =================================================================

@app.post("/webhook")
async def dialogflow_webhook(request: Request):
    """Main entry point for all Dialogflow webhook calls."""
    if db is None:
        return format_dialogflow_response(
            "I'm experiencing connectivity issues right now. Please try again later."
        )
        
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        print("Error decoding JSON payload.")
        return JSONResponse(content={"error": "Invalid JSON payload"}, status_code=status.HTTP_400_BAD_REQUEST)

    intent_name = get_intent_name(payload)
    parameters = get_parameters(payload)

    print(f"Received intent: {intent_name} with parameters: {parameters}")
    
    # --- Dynamic Intent Logic ---
    
    # Intent: Placement_Record_D
    if intent_name == 'Placement_Record_D':
        target_year_raw = parameters.get('Year') or parameters.get('year')
        target_year = str(target_year_raw).strip() if target_year_raw else None
        
        if target_year:
            record = await db.placement_records.find_one({"year": target_year})
            
            if record:
                response_text = f"The number of placements for the academic year {target_year} was **{record['number']}**."
            else:
                response_text = f"The year '{target_year}' was recognized, but no specific data was found in the records. Please ensure the year format matches the database exactly (e.g., 'YYYY-YYYY')."
        else:
            latest_record = await db.placement_records.find_one(sort=[('sort_order', 1)])
            
            if latest_record:
                response_text = (
                    f"Anurag University has a strong placement record, with the latest figures showing "
                    f"**{latest_record['number']}** placements in the **{latest_record['year']}** academic year."
                )
            else:
                response_text = "I could not retrieve the latest placement summary at this moment."

        return format_dialogflow_response(response_text)

    # Intent: IIIC_Partners_D
    elif intent_name == 'IIIC_Partners_D':
        partner_doc = await db.iiic_partners.find_one({"list_name": "MOU_Partners"})
        
        if partner_doc and 'partners' in partner_doc and isinstance(partner_doc['partners'], list):
            partner_names = ", ".join(partner_doc['partners'])
            response_text = (
                f"Anurag University has signed MOUs with many companies, including: "
                f"**{partner_names}**."
            )
        else:
            response_text = "The list of Industry Interaction partners is currently being updated. Please check back later."

        return format_dialogflow_response(response_text)
    
    # Intent: Merit_Scholarship_Rank_D
    elif intent_name == 'Merit_Scholarship_Rank_D':
        # Handles both rank bands and potential stray numbers
        exam_alias_raw = parameters.get('entranceexam') or parameters.get('EntranceExam')
        rank_band_raw = parameters.get('rankband') or parameters.get('RankBand')
        number_raw = parameters.get('number')

        exam_alias = str(exam_alias_raw).strip() if exam_alias_raw else None
        rank_band = str(rank_band_raw).strip() if rank_band_raw else None
        
        # CONVERT STRAY NUMBER TO RANK BAND
        if not rank_band and number_raw is not None and exam_alias and exam_alias.upper() in ['EAPCET', 'JEE']:
            try:
                rank = int(number_raw)
                if rank <= 2000:
                    rank_band = '1-2000'
                elif rank <= 10000:
                    rank_band = '2001-10000'
                elif rank <= 15000:
                    rank_band = '10001-15000'
                elif rank <= 25000:
                    rank_band = '15001-25000'
            except (ValueError, TypeError):
                pass
        
        response_text = "Please specify both the entrance exam (e.g., ANURAGCET, EAPCET, or JEE) and your rank band."
        
        if exam_alias and rank_band:
            exam_key = exam_alias.upper()
            exam_doc = await db.scholarship_ranks.find_one({"exam": {"$regex": exam_key, "$options": "i"}})
            
            if exam_doc:
                rank_details = None
                if exam_key == 'ANURAGCET':
                    rank_details = next((r for r in exam_doc['ranks'] if r['band'] == rank_band), None)
                else: 
                    rank_details = next((r for r in exam_doc['ranks'] if r.get('eapcet_band') == rank_band or r.get('jee_band') == rank_band), None)
                
                if rank_details:
                    if exam_key != 'ANURAGCET':
                        rank_display = f"EAPCET Rank: {rank_details['eapcet_band']} (or JEE Rank: {rank_details['jee_band']})"
                    else:
                        rank_display = f"Rank: {rank_details['band']}"
                        
                    response_text = (
                        f"Based on your **{exam_key}** rank ({rank_display}), you receive a "
                        f"**{rank_details['concession']}** concession, valued at **Rs. {rank_details['value']}**."
                    )
                else:
                    response_text = f"The rank band **{rank_band}** does not qualify for a merit scholarship under the **{exam_key}** policy, or the rank is outside the scholarship range."
            else:
                response_text = f"Sorry, I couldn't find the scholarship policy details for the **{exam_alias}** exam."

        return format_dialogflow_response(response_text)
    
    # Intent: Social_Scholarship_Criteria_D (for completeness)
    elif intent_name == 'Social_Scholarship_Criteria_D':
        category = parameters.get('socialcategory') or parameters.get('SocialCategory')
        
        if category:
            if category in ['SC', 'ST']:
                lookup_cat = 'SC & ST'
            elif category in ['BC', 'EBC', 'MINORITY']:
                lookup_cat = 'BC, EBC & Minority'
            else:
                lookup_cat = None
            
            if lookup_cat:
                policy_doc = await db.social_scholarships.find_one({"category": lookup_cat})
                
                if policy_doc:
                    response_text = (
                        f"For **{policy_doc['category']}** students, the scholarship is awarded if the "
                        f"parental income is less than **{policy_doc['income_limit']}**. "
                        f"Students must also maintain a minimum of **{policy_doc['attendance']}%** attendance."
                    )
                else:
                    response_text = "I'm having trouble retrieving the specific policy from the database."
            else:
                 response_text = f"The scholarship guidelines for the category '{category}' are not currently available."
        else:
            response_text = (
                "Please specify the category. General guidelines: SC/ST income < **Rs. 2 lakhs**; "
                "BC/EBC/Minority income < **Rs. 1 lakh**. All require **75% attendance**."
            )

        return format_dialogflow_response(response_text)


    # Intent: Engineering_Course_Description_D (now UG_Program_Description_D)
    elif intent_name == 'Engineering_Course_Description_D':
        course_alias = parameters.get('engineeringcourse') or parameters.get('EngineeringCourse')
        
        if course_alias:
            course_data = await db.engineering_courses.find_one({"alias": course_alias})
            
            if course_data:
                # Add conditional check for rich pharmacy data
                pharmacy_info = f"{f'**Accreditation/Rank:** {course_data.get('accreditation', '')} ({course_data.get('nirf_rank', '')})' if course_data.get('type') == 'Pharmacy' else ''}"
                
                response_text = (
                    f"**{course_data['name']}**:\n"
                    f"**Overview:** {course_data['description']}\n"
                    f"**Key Focus:** {course_data['focus']}\n"
                    f"{pharmacy_info}"
                )
            else:
                response_text = f"I couldn't find a detailed description for the program: {course_alias}. Please ensure you use the full program name."
        else:
            response_text = "Which program are you interested in? (e.g., AI, Civil, or B Pharmacy)"

        return format_dialogflow_response(response_text)
    
    # Intent: Hostel_Fee_D
    elif intent_name == 'Hostel_Fee_D':
        gender_alias = parameters.get('gender') or parameters.get('Gender')
        accommodation_alias = parameters.get('accommodationtype') or parameters.get('AccommodationType')
        
        if gender_alias and accommodation_alias:
            gender_key = gender_alias.upper()
            fee_doc = await db.hostel_fees.find_one({"gender": gender_key})

            if fee_doc and 'fees' in fee_doc:
                fee_details = next((f for f in fee_doc['fees'] if f['alias'] == accommodation_alias), None)

                if fee_details:
                    note = fee_details.get('note', '')
                    response_text = (
                        f"The fee for a **{gender_alias.capitalize()}** student in a "
                        f"**{fee_details['type']}** room is:\n"
                        f"**Annual Hostel Fee:** Rs. {fee_details['annual_fee']}\n"
                        f"**Annual Facilities Fee:** Rs. {fee_details['facilities_fee']}\n"
                        f"{note}"
                    )
                else:
                    response_text = f"I found the fees for {gender_alias.capitalize()} students, but not the specific room type: {accommodation_alias}. Please specify 5 sharing, 4 sharing attached, or 4 sharing with AC."
            else:
                response_text = "I am unable to retrieve the fee structure from the database at this moment."
        else:
            response_text = "Please specify both the student's gender (male/female) and the accommodation type (e.g., 4 sharing with AC)."

        return format_dialogflow_response(response_text)
    
    # Intent: Sports_Team_Contact_D
    elif intent_name == 'Sports_Team_Contact_D':
        member_alias = parameters.get('sportsteammember') or parameters.get('SportsTeamMember')
        
        if member_alias:
            member_data = await db.sports_team.find_one({"alias": member_alias})
            
            if member_data:
                response_text = (
                    f"You can contact **{member_data['name']}** at the following email:\n"
                    f"**Email:** {member_data['email']}"
                )
            else:
                response_text = f"I couldn't find contact details for a team member with the alias: {member_alias}. Please try the full name."
        else:
            general_contact = await db.sports_team.find_one({"alias": "TARA_SINGH"})
            
            if general_contact:
                 response_text = (
                    f"Which sports team member would you like to contact? "
                    f"For general inquiries, you can reach **{general_contact['name']}** at {general_contact['email']}."
                )
            else:
                response_text = "Please specify the team member's name."

        return format_dialogflow_response(response_text)


    # --- Default Webhook Response ---
    
    return format_dialogflow_response(
        f"I received the intent '{intent_name}', but I don't have a specific dynamic handler for it yet. "
        "Please check the static response in Dialogflow or contact support."
    )

# 5. API ENDPOINT (Called BY Front-end UI)
# =================================================================
@app.post("/query")
async def chat_query(request: Request):
    
    # ⚠️ REPLACE WITH YOUR PROJECT ID ⚠️
    DIALOGFLOW_PROJECT_ID = "YOUR_DIALOGFLOW_PROJECT_ID" 
    
    try:
        data = await request.json()
        user_text = data.get('text')
        language_code = data.get('language')
    except json.JSONDecodeError:
        return JSONResponse({"response": "Invalid request format."}, status_code=status.HTTP_400_BAD_REQUEST)

    if not user_text or not DIALOGFLOW_PROJECT_ID:
        return JSONResponse({"response": "Chat service initialization error. Check project ID and input text."}, status_code=status.HTTP_400_BAD_REQUEST)
    
    # Generate a unique session ID for the user
    session_id = str(uuid.uuid4()) 
    
    try:
        dialogflow_result = detect_intent_texts(
            project_id=DIALOGFLOW_PROJECT_ID,
            session_id=session_id,
            texts=user_text,
            language_code=language_code
        )
        
        if dialogflow_result:
            return JSONResponse({
                "response": dialogflow_result['fulfillment_text'],
                "intent": dialogflow_result['intent_name'],
                "confidence": dialogflow_result['confidence']
            })
        else:
            return JSONResponse({"response": "Sorry, I couldn't connect to the AI service (Dialogflow API failed)."}, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    except Exception as e:
        print(f"Query processing failed: {e}")
        return JSONResponse({"response": "An internal server error occurred during the query. Check backend console logs."}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)