import motor.motor_asyncio
import os
from typing import Dict, Any

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://22eg106b52_db_user:ID1HC1Jt7iSQTZD8@anurag-chatbot.1zycn8n.mongodb.net/")
DATABASE_NAME = "university_db"

async def handle_hostel_fee(parameters: Dict[str, Any]) -> str:
    """
    Handles Hostel_Fee_D intent
    """
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        db = client[DATABASE_NAME]
        
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

        await client.close()
        return response_text

    except Exception as e:
        print(f"Error in Hostel_Fee_D handler: {e}")
        return "I'm having trouble accessing the hostel fee information right now."