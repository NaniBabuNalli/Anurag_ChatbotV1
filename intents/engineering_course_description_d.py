import motor.motor_asyncio
import os
from typing import Dict, Any

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://22eg106b52_db_user:ID1HC1Jt7iSQTZD8@anurag-chatbot.1zycn8n.mongodb.net/")
DATABASE_NAME = "university_db"

async def handle_engineering_course_description(parameters: Dict[str, Any]) -> str:
    """
    Handles Engineering_Course_Description_D intent
    """
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        db = client[DATABASE_NAME]
        
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

        await client.close()
        return response_text

    except Exception as e:
        print(f"Error in Engineering_Course_Description_D handler: {e}")
        return "I'm having trouble accessing the course information right now."