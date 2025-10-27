from ..database import get_database
from typing import Dict, Any

async def handle_merit_scholarship_rank(parameters: Dict[str, Any]) -> str:
    """
    Handles Merit_Scholarship_Rank_D intent
    """
    try:
        db = await get_database()
        
        exam_alias_raw = parameters.get('entranceexam') or parameters.get('EntranceExam')
        rank_band_raw = parameters.get('rankband') or parameters.get('RankBand')
        number_raw = parameters.get('number')
        
        # If we have the raw query text and parameters are missing, try to extract from text
        query_text = parameters.get('query_text', '')
        
        # Extract exam from query if not in parameters
        if not exam_alias_raw and query_text:
            query_upper = query_text.upper()
            if 'EAPCET' in query_upper or 'EAMCET' in query_upper:
                exam_alias_raw = 'EAPCET'
            elif 'JEE' in query_upper:
                exam_alias_raw = 'JEE'
            elif 'ANURAG' in query_upper:
                exam_alias_raw = 'ANURAGCET'
        
        # Extract number/rank from query if not in parameters
        if not number_raw and query_text:
            import re
            # Look for numbers in the query (e.g., "rank 1500", "1500", "rank of 1500")
            number_match = re.search(r'\b(\d{1,6})\b', query_text)
            if number_match:
                number_raw = int(number_match.group(1))

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

        return response_text

    except Exception as e:
        print(f"Error in Merit_Scholarship_Rank_D handler: {e}")
        return "I'm having trouble accessing the scholarship information right now. Please try again later."