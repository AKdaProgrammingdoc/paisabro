import os
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from twilio.rest import Client as TwilioClient
from database import get_weekly_summary
from supabase import create_client
from groq import Groq
import json

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
twilio_client = TwilioClient(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

scheduler = AsyncIOScheduler()

async def send_weekly_roasts():
    """Send weekly summary to all active users every Sunday 9AM"""
    print("Running weekly roast job...")
    
    try:
        # Get all unique users who logged expenses this week
        result = supabase.table("expenses")\
            .select("phone")\
            .execute()
        
        phones = list(set(row["phone"] for row in result.data))
        
        for phone in phones:
            summary = await get_weekly_summary(phone)
            if summary.get("total", 0) == 0:
                continue
            
            # Generate roast
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are PaisaBro. Weekly Sunday roast in Hinglish. Savage but caring. Max 5 lines. Plain text."},
                    {"role": "user", "content": f"Weekly spending data: {json.dumps(summary)}"}
                ],
                max_tokens=200
            )
            
            roast = response.choices[0].message.content.strip()
            categories = summary.get("by_category", {})
            cat_breakdown = "\n".join([f"  • {k.title()}: ₹{v}" for k, v in categories.items()])
            
            message = f"📊 *Sunday Damage Report* 🔥\n\n"
            message += f"Total this week: ₹{summary['total']}\n"
            message += f"Transactions: {summary['count']}\n\n"
            if cat_breakdown:
                message += f"Breakdown:\n{cat_breakdown}\n\n"
            message += f"PaisaBro says:\n{roast}"
            
            # Send via Twilio
            twilio_client.messages.create(
                from_=f"whatsapp:{os.getenv('TWILIO_WHATSAPP_NUMBER')}",
                to=f"whatsapp:+{phone}",
                body=message
            )
            
            await asyncio.sleep(1)  # Rate limit
            
    except Exception as e:
        print(f"Weekly roast error: {e}")

def start_scheduler():
    # Every Sunday at 9:00 AM
    scheduler.add_job(send_weekly_roasts, 'cron', day_of_week='sun', hour=9, minute=0)
    scheduler.start()
    print("Scheduler started ✅")
