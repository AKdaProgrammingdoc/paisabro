from fastapi import FastAPI, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
import os
from dotenv import load_dotenv
from expense_handler import handle_message

load_dotenv()

app = FastAPI()

@app.post("/webhook")
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
    
    return Response(content=str(resp), media_type="application/xml")

@app.get("/")
def root():
    return {"status": "PaisaBro is alive 💸"}
