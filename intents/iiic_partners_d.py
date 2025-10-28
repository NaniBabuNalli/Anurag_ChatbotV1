import motor.motor_asyncio
import os
from typing import Dict, Any

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://22eg106b52_db_user:ID1HC1Jt7iSQTZD8@anurag-chatbot.1zycn8n.mongodb.net/")
DATABASE_NAME = "university_db"

async def handle_iiic_partners(parameters: Dict[str, Any]) -> str:
    """
    Handles IIIC_Partners_D intent
    """
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        db = client[DATABASE_NAME]
        
        partner_doc = await db.iiic_partners.find_one({"list_name": "MOU_Partners"})
        
        if partner_doc and 'partners' in partner_doc and isinstance(partner_doc['partners'], list):
            # Show first 10 partners to avoid overwhelming response
            partner_names = ", ".join(partner_doc['partners'][:10])
            total_partners = len(partner_doc['partners'])
            response_text = (
                f"Anurag University has signed MOUs with {total_partners} companies, including: "
                f"**{partner_names}** and many more."
            )
        else:
            response_text = "The list of Industry Interaction partners is currently being updated. Please check back later."

        await client.close()
        return response_text

    except Exception as e:
        print(f"Error in IIIC_Partners_D handler: {e}")
        return "I'm having trouble accessing the industry partner information right now."