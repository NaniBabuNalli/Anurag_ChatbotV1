import motor.motor_asyncio
import os
from typing import Dict, Any

# MongoDB configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://22eg106b52_db_user:ID1HC1Jt7iSQTZD8@anurag-chatbot.1zycn8n.mongodb.net/")
DATABASE_NAME = "university_db"

async def handle_placement_record(parameters: Dict[str, Any]) -> str:
    """
    Handles Placement_Record_D intent
    """
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        db = client[DATABASE_NAME]
        
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

        await client.close()
        return response_text

    except Exception as e:
        print(f"Error in Placement_Record_D handler: {e}")
        return "I'm having trouble accessing the placement records right now. Please try again later."