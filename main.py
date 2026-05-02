# ADD THIS to your existing main.py in paisabro backend
# This receives auto-detected payments from the Android app

from fastapi import FastAPI, Form, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from twilio.rest import Client as TwilioClient
from twilio.twiml.messaging_response import MessagingResponse
import os
from dotenv import load_dotenv
from expense_handler import handle_message
from database import log_expense, get_user_language
from groq import Groq

load_dotenv()

app = FastAPI()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
twilio_client = TwilioClient(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

@app.post("/webhook", response_class=PlainTextResponse)
async def webhook(
    From: str = Form(...),
    Body: str = Form(...),
    NumMedia: str = Form(default="0"),
    MediaUrl0: str = Form(default=None),
    MediaContentType0: str = Form(default=None),
):
    user_phone = From.replace("whatsapp:", "")
    message_body = Body.strip()
    has_media = int(NumMedia) > 0
    media_url = MediaUrl0 if has_media else None
    media_type = MediaContentType0 if has_media else None

    reply = await handle_message(
        phone=user_phone,
        message=message_body,
        media_url=media_url,
        media_type=media_type
    )

    resp = MessagingResponse()
    resp.message(reply)
    return str(resp)


@app.post("/sms-webhook")
async def sms_webhook(request: Request):
    """Receives auto-detected payments from Android app"""
    try:
        data = await request.json()
        phone = data.get("phone", "")
        amount = float(data.get("amount", 0))
        merchant = data.get("merchant", "Unknown")
        source = data.get("source", "auto_sms")

        if not phone or amount <= 0:
            return JSONResponse({"status": "error", "message": "Invalid data"}, status_code=400)

        # Log the expense
        await log_expense(
            phone=phone,
            amount=amount,
            category="misc",
            description=f"Auto-detected: {merchant}"
        )

        # Get user language
        language = await get_user_language(phone) or "english"

        # Generate roast
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"You are PaisaBro. Reply in {language} style. Max 3 lines. Funny and savage but caring. Plain text only."},
                {"role": "user", "content": f"User just auto-paid Rs.{amount} to {merchant} via UPI. Roast them!"}
            ],
            max_tokens=150
        )
        roast = response.choices[0].message.content.strip()

        # Send WhatsApp message
        message = f"🔔 *Auto-detected payment!*\nRs.{amount} → {merchant} logged ✅\n\n{roast}"

        twilio_client.messages.create(
            from_=f"whatsapp:{os.getenv('TWILIO_WHATSAPP_NUMBER')}",
            to=f"whatsapp:+{phone}",
            body=message
        )

        return JSONResponse({"status": "success"})

    except Exception as e:
        print(f"SMS webhook error: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/")
def root():
    return {"status": "PaisaBro is alive 💸"}
