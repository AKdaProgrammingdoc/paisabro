import os
import json
import httpx
from groq import Groq
from database import log_expense, get_weekly_summary, get_monthly_summary, get_user_goal, set_user_goal, get_user_language, set_user_language
from datetime import datetime
import random

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

LANGUAGE_PROMPTS = {
    "hinglish": """You are PaisaBro — a brutally honest, funny, savage but caring desi money coach.
You talk like a close desi friend who happens to be a CA. Use Hinglish (Hindi+English) naturally.
Use phrases like "bhai", "yaar", "arre", "kyun bhai", "kya kar raha hai tu".""",

    "tanglish": """You are PaisaBro — a brutally honest, funny, savage but caring desi money coach.
You talk like a close Tamil friend who happens to be a CA. Use Tanglish (Tamil+English) naturally.
Use phrases like "machan", "da", "pa", "aiyo", "seri da", "enna da ithu", "vera level", "enthuku da".
Example: "Aiyo machan, Swiggy-la 500 pochu da! Samayal pannikanum da!".""",

    "english": """You are PaisaBro — a brutally honest, funny, savage but caring money coach.
Talk like a close Indian friend who is a financial advisor. Use casual Indian English.
Use phrases like "bro", "man", "seriously though", "come on now".""",

    "telugu": """You are PaisaBro — a brutally honest, funny, savage but caring desi money coach.
You talk like a close Telugu friend who happens to be a CA. Use Tenglish (Telugu+English) naturally.
Use phrases like "anna", "bro", "enti", "ayyo", "bagunava", "em chesav".""",

    "kannada": """You are PaisaBro — a brutally honest, funny, savage but caring desi money coach.
You talk like a close Kannada friend who happens to be a CA. Use Kanglish (Kannada+English) naturally.
Use phrases like "guru", "yen maado", "haege", "sakkath", "bekilla".""",
}

LANGUAGE_NAMES = {
    "1": ("hinglish", "Hinglish 🇮🇳"),
    "2": ("tanglish", "Tanglish 🌴"),
    "3": ("english", "English 🇬🇧"),
    "4": ("telugu", "Tenglish ⭐"),
    "5": ("kannada", "Kanglish 🏔️"),
}

def get_system_prompt(language: str) -> str:
    base = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS["english"])
    return base + """

Your job:
1. Understand if the user is logging an expense, asking a question, or setting a goal
2. Extract expense details if present (amount, category, description)
3. Reply with personality — funny, honest, caring

Categories: food, transport, shopping, entertainment, bills, health, education, savings, misc

Response rules:
- Keep replies short — max 3-4 lines. This is WhatsApp not an essay
- Add relevant emojis but don't overdo it
- If it's an expense, confirm you logged it + give a quick roast or encouragement
- If they're doing well, praise them genuinely
- If they're overspending, roast them lovingly

You must ALWAYS respond with valid JSON in this exact format:
{
  "is_expense": true/false,
  "amount": 0,
  "category": "food",
  "description": "brief description",
  "reply": "your witty reply here"
}

If it's not an expense, set is_expense to false and amount to 0.
"""

WEEKLY_ROAST_PROMPT = """
You are PaisaBro. Generate a savage but loving weekly spending summary roast.
Speak in {language} style. Keep it under 5 lines. Be funny and end with one actionable tip.
Data: {data}
Reply as plain text, no JSON needed.
"""

async def handle_message(phone: str, message: str, media_url: str = None, media_type: str = None) -> str:
    lower_msg = message.lower().strip()

    # Language selection flow
    user_language = await get_user_language(phone)

    if not user_language:
        if lower_msg in ["1", "2", "3", "4", "5"]:
            lang_code, lang_name = LANGUAGE_NAMES[lower_msg]
            await set_user_language(phone, lang_code)
            return get_welcome_message(lang_code, lang_name)
        else:
            return get_language_selection_message()

    # Language change command
    if lower_msg in ["language", "lang", "change language", "/language"]:
        await set_user_language(phone, None)
        return get_language_selection_message()

    # Standard commands
    if lower_msg in ["hi", "hello", "hey", "start", "/start"]:
        return get_welcome_message(user_language)

    if lower_msg in ["summary", "report", "/summary", "kitna kharch", "evlo achu", "how much"]:
        return await generate_summary(phone, "weekly", user_language)

    if lower_msg in ["monthly", "/monthly", "month"]:
        return await generate_summary(phone, "monthly", user_language)

    if lower_msg.startswith("goal ") or lower_msg.startswith("target "):
        return await handle_goal_setting(phone, message, user_language)

    if lower_msg in ["help", "/help"]:
        return get_help_message(user_language)

    # Handle image (UPI screenshot)
    if media_url and media_type and "image" in media_type:
        return await handle_image_expense(phone, media_url, message, user_language)

    # Handle text expense
    return await handle_text_expense(phone, message, user_language)


def get_language_selection_message() -> str:
    return """👋 *Welcome to PaisaBro!*
Your savage desi money coach 💸

Please choose your language:
*1* → Hinglish 🇮🇳
*2* → Tanglish 🌴
*3* → English 🇬🇧
*4* → Tenglish ⭐
*5* → Kanglish 🏔️

Reply with a number (1-5)"""


def get_welcome_message(language: str, lang_name: str = None) -> str:
    messages = {
        "hinglish": """🤑 *PaisaBro mein welcome hai bhai!*
Main tera desi money coach hoon — honest, funny, aur thoda judgemental 😄

💸 Expense log kar — "200 rupaye Zomato pe"
📸 UPI screenshot bhej
📊 Weekly roast — "summary" likh
🎯 Goal set kar — "goal 5000"

Chal shuru karte hain! 💪""",

        "tanglish": """🤑 *PaisaBro-ku welcome da machan!*
Un desi money coach — honest, funny, konjam judgemental 😄

💸 Expense log pannu — "200 Zomato-la pochu da"
📸 UPI screenshot anuppu
📊 Weekly roast — "summary" sollu
🎯 Goal set pannu — "goal 5000"

Aaaramba da! 💪""",

        "english": """🤑 *Welcome to PaisaBro!*
Your brutally honest money coach — funny, caring, slightly judgemental 😄

💸 Log expense — "spent 200 on Zomato"
📸 Send UPI screenshot
📊 Weekly roast — type "summary"
🎯 Set goal — "goal 5000"

Let's get started! 💪""",

        "telugu": """🤑 *PaisaBro-ki welcome anna!*
Mee desi money coach — honest, funny, konchem judgemental 😄

💸 Expense log cheyu — "200 Zomato ki poindi"
📸 UPI screenshot pampu
📊 Weekly roast — "summary" rayu
🎯 Goal petto — "goal 5000"

Moudham padadam! 💪""",

        "kannada": """🤑 *PaisaBro-ge swagata guru!*
Ninna desi money coach — honest, funny, summane judgemental 😄

💸 Expense log maadu — "200 Zomato-ge hoitu"
📸 UPI screenshot kali
📊 Weekly roast — "summary" bari
🎯 Goal illi — "goal 5000"

Shuru maadona! 💪""",
    }
    return messages.get(language, messages["english"])


async def handle_text_expense(phone: str, message: str, language: str) -> str:
    try:
        monthly = await get_monthly_summary(phone)
        context = f"User has spent Rs.{monthly.get('total', 0)} this month so far." if monthly else ""

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": get_system_prompt(language)},
                {"role": "user", "content": f"{context}\n\nUser message: {message}"}
            ],
            temperature=0.8,
            max_tokens=300
        )

        raw = response.choices[0].message.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        data = json.loads(raw.strip())

        if data.get("is_expense") and data.get("amount", 0) > 0:
            await log_expense(
                phone=phone,
                amount=float(data["amount"]),
                category=data.get("category", "misc"),
                description=data.get("description", message),
            )

        return data.get("reply", "Noted! 💸")

    except json.JSONDecodeError:
        fallbacks = {
            "hinglish": "Bhai kuch samajh nahi aaya 😅 Try: '200 rupaye Zomato pe gaye'",
            "tanglish": "Machan puriyala da 😅 Try: '200 Zomato-la pochu da'",
            "english": "Didn't catch that bro 😅 Try: 'spent 200 on Zomato'",
            "telugu": "Anna artham kaala 😅 Try: '200 Zomato ki poindi'",
            "kannada": "Guru arthaagailla 😅 Try: '200 Zomato-ge hoitu'",
        }
        return fallbacks.get(language, fallbacks["english"])
    except Exception as e:
        return "System is taking a quick nap 🥴 Try again in a sec!"


async def handle_image_expense(phone: str, media_url: str, caption: str, language: str) -> str:
    try:
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")

        async with httpx.AsyncClient() as client:
            response = await client.get(media_url, auth=(twilio_sid, twilio_token))
            image_data = response.content

        import base64
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        response = groq_client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                        {"type": "text", "text": """Extract expense from this UPI/payment screenshot.
                        Reply ONLY in JSON: {"amount": 0, "merchant": "name"}
                        If not a payment screenshot, set amount to 0."""}
                    ]
                }
            ],
            max_tokens=200
        )

        raw = response.choices[0].message.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        img_data = json.loads(raw.strip())
        amount = float(img_data.get("amount", 0))
        merchant = img_data.get("merchant", "unknown")

        if amount > 0:
            await log_expense(phone=phone, amount=amount, category="misc", description=f"UPI to {merchant}")

            roast_response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": f"You are PaisaBro. Reply in {language} style, max 3 lines, funny and savage. Plain text only."},
                    {"role": "user", "content": f"I just paid Rs.{amount} to {merchant}"}
                ],
                max_tokens=150
            )
            roast = roast_response.choices[0].message.content.strip()
            return f"📸 Screenshot caught!\nRs.{amount} to {merchant} logged ✅\n\n{roast}"
        else:
            fallbacks = {
                "hinglish": "Bhai yeh payment screenshot nahi lagta 🤔 Clear screenshot bhej!",
                "tanglish": "Machan ithu payment screenshot illa da 🤔 Clear-a anuppu!",
                "english": "That doesn't look like a payment screenshot bro 🤔 Send a clearer one!",
                "telugu": "Anna idi payment screenshot kaadu 🤔 Clear ga pampu!",
                "kannada": "Guru idu payment screenshot alla 🤔 Clear agi kali!",
            }
            return fallbacks.get(language, "Not a payment screenshot 🤔 Send a clearer one!")

    except Exception as e:
        return "Screenshot unclear 😅 Type it manually: '500 Swiggy'"


async def generate_summary(phone: str, period: str, language: str) -> str:
    try:
        data = await get_weekly_summary(phone) if period == "weekly" else await get_monthly_summary(phone)

        if not data or data.get("total", 0) == 0:
            fallbacks = {
                "hinglish": "Abhi tak kuch log nahi kiya bhai! Pehle kharch kar 😄",
                "tanglish": "Ippo varai onnume log panala da machan! 😄",
                "english": "Nothing logged yet bro! Start tracking! 😄",
                "telugu": "Inka emi log cheyyaledu anna! 😄",
                "kannada": "Inka enu log maadilla guru! 😄",
            }
            return fallbacks.get(language, "Nothing logged yet! Start tracking 😄")

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"You are PaisaBro. Spending summary roast in {language} style. Max 5 lines. Funny and caring. Plain text."},
                {"role": "user", "content": WEEKLY_ROAST_PROMPT.format(language=language, data=json.dumps(data))}
            ],
            max_tokens=250
        )

        roast = response.choices[0].message.content.strip()
        categories = data.get("by_category", {})
        cat_breakdown = "\n".join([f"  • {k.title()}: Rs.{v}" for k, v in categories.items()])
        period_label = "This Week" if period == "weekly" else "This Month"

        summary = f"📊 *{period_label}'s Damage Report*\n"
        summary += f"Total: Rs.{data['total']}\n"
        summary += f"Transactions: {data['count']}\n\n"
        if cat_breakdown:
            summary += f"Breakdown:\n{cat_breakdown}\n\n"
        summary += f"🔥 PaisaBro says:\n{roast}"

        return summary

    except Exception as e:
        return "Summary unavailable right now 😅 Try again!"


async def handle_goal_setting(phone: str, message: str, language: str) -> str:
    try:
        words = message.lower().replace("goal", "").replace("target", "").replace("rupaye", "").replace("rs", "").replace("save", "").strip()
        amount = None
        for word in words.split():
            try:
                amount = float(word.replace(",", ""))
                break
            except:
                continue

        if not amount:
            fallbacks = {
                "hinglish": "Bhai amount samajh nahi aaya 😅 Try: 'goal 5000'",
                "tanglish": "Machan amount puriyala 😅 Try: 'goal 5000'",
                "english": "Didn't catch the amount bro 😅 Try: 'goal 5000'",
                "telugu": "Anna amount artham kaala 😅 Try: 'goal 5000'",
                "kannada": "Guru amount arthaagailla 😅 Try: 'goal 5000'",
            }
            return fallbacks.get(language, "Try: 'goal 5000'")

        await set_user_goal(phone, amount)

        responses = {
            "hinglish": [
                f"Goal set bhai! Rs.{amount:,.0f} bachana hai is mahine 💪 Nazar rakhta hoon 👀",
                f"Rs.{amount:,.0f} ka target? Challenge accepted 😤",
            ],
            "tanglish": [
                f"Goal set da machan! Rs.{amount:,.0f} machikaNum 💪 Paathukareen 👀",
                f"Rs.{amount:,.0f} target-a? Seri da, pakkalaam 😤",
            ],
            "english": [
                f"Goal set bro! Save Rs.{amount:,.0f} this month 💪 I'm watching you 👀",
                f"Rs.{amount:,.0f} target? Challenge accepted 😤",
            ],
            "telugu": [
                f"Goal pettam anna! Rs.{amount:,.0f} save cheyyali 💪 Chustunnanu 👀",
                f"Rs.{amount:,.0f} target-a? Sare anna, chooddam 😤",
            ],
            "kannada": [
                f"Goal ittini guru! Rs.{amount:,.0f} ulisabeku 💪 Nodtini 👀",
                f"Rs.{amount:,.0f} target-a? Sari guru, noodona 😤",
            ],
        }

        choices = responses.get(language, responses["english"])
        return random.choice(choices)

    except Exception as e:
        return "Try: 'goal 5000'"


def get_help_message(language: str) -> str:
    messages = {
        "hinglish": """*PaisaBro Commands* 🤑
💬 Expense: "200 chai pe gaye"
📸 UPI screenshot bhej
📊 "summary" → weekly report
📅 "monthly" → monthly report
🎯 "goal 5000" → saving target
🌐 "language" → change language""",

        "tanglish": """*PaisaBro Commands* 🤑
💬 Expense: "200 chai-la pochu"
📸 UPI screenshot anuppu
📊 "summary" → weekly report
📅 "monthly" → monthly report
🎯 "goal 5000" → saving target
🌐 "language" → moli maathu""",

        "english": """*PaisaBro Commands* 🤑
💬 Expense: "spent 200 on chai"
📸 Send UPI screenshot
📊 "summary" → weekly report
📅 "monthly" → monthly report
🎯 "goal 5000" → saving target
🌐 "language" → change language""",

        "telugu": """*PaisaBro Commands* 🤑
💬 Expense: "200 chai ki poindi"
📸 UPI screenshot pampu
📊 "summary" → weekly report
📅 "monthly" → monthly report
🎯 "goal 5000" → saving target
🌐 "language" → bhasha maarchu""",

        "kannada": """*PaisaBro Commands* 🤑
💬 Expense: "200 chai-ge hoitu"
📸 UPI screenshot kali
📊 "summary" → weekly report
📅 "monthly" → monthly report
🎯 "goal 5000" → saving target
🌐 "language" → bhasha badlisu""",
    }
    return messages.get(language, messages["english"])
