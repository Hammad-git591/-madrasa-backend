from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from database import (
    qari_col, admissions_col,
    appointments_col, donations_col,
    settings_col, conversations_col
)
from bson import ObjectId
from datetime import datetime
import os
import time

load_dotenv()

# ─────────────────────────────────────────
# LLM — Gemini
# ─────────────────────────────────────────
llm = ChatGoogleGenerativeAI(
    model="gemini-flash-latest",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.7
)

# ─────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────
@tool
def get_qari_list() -> list:
    """Saare available Qari ki list lao"""
    qaris = list(qari_col.find({"available": True}))
    for q in qaris:
        q["_id"] = str(q["_id"])
    return qaris

@tool
def check_slot_availability(qari_id: str, date: str) -> dict:
    """Qari ka slot check karo"""
    qari = qari_col.find_one({"_id": ObjectId(qari_id)})
    if not qari:
        return {"error": "Qari nahi mila"}
    booked = list(appointments_col.find({
        "qari_id": qari_id,
        "date": date,
        "status": "confirmed"
    }))
    booked_slots = [b["time_slot"] for b in booked]
    all_slots = qari.get("timings", [])
    available = [s for s in all_slots if s not in booked_slots]
    return {
        "qari_name": qari["name"],
        "date": date,
        "available_slots": available,
        "booked_slots": booked_slots
    }

@tool
def book_appointment_tool(
    name: str,
    phone: str,
    qari_id: str,
    date: str,
    time_slot: str
) -> dict:
    """Appointment book karo"""
    clash = appointments_col.find_one({
        "qari_id": qari_id,
        "date": date,
        "time_slot": time_slot,
        "status": "confirmed"
    })
    if clash:
        return {
            "status": "unavailable",
            "message": "Yeh slot booked hai!"
        }
    result = appointments_col.insert_one({
        "name": name,
        "phone": phone,
        "qari_id": qari_id,
        "date": date,
        "time_slot": time_slot,
        "status": "confirmed",
        "date_added": datetime.now().isoformat()
    })
    return {
        "status": "success",
        "message": f"Appointment confirm! {date} ko {time_slot}",
        "id": str(result.inserted_id)
    }

@tool
def get_fitrana_rate() -> dict:
    """Current Fitrana rate lao"""
    settings = settings_col.find_one()
    return {"fitrana_rate": settings.get("fitrana_rate", 320)}

@tool
def record_donation_tool(
    donor_name: str,
    phone: str,
    amount: float,
    donation_type: str
) -> dict:
    """Donation record karo"""
    receipt_no = f"DN-{int(time.time())}"
    donations_col.insert_one({
        "donor_name": donor_name,
        "phone": phone,
        "amount": amount,
        "type": donation_type,
        "receipt_no": receipt_no,
        "date_added": datetime.now().isoformat()
    })
    return {
        "status": "success",
        "receipt_no": receipt_no,
        "message": f"JazakAllah! Receipt: {receipt_no}"
    }

@tool
def save_admission_tool(
    child_name: str,
    father_name: str,
    age: str,
    phone: str,
    qari_id: str,
    time_slot: str
) -> dict:
    """Naya admission save karo"""
    result = admissions_col.insert_one({
        "child_name": child_name,
        "father_name": father_name,
        "age": age,
        "phone": phone,
        "qari_id": qari_id,
        "time_slot": time_slot,
        "status": "active",
        "date_added": datetime.now().isoformat()
    })
    return {
        "status": "success",
        "message": f"Masha'Allah! {child_name} ka daakhla ho gaya!",
        "id": str(result.inserted_id)
    }

# ─────────────────────────────────────────
# MEMORY
# ─────────────────────────────────────────
def get_history(session_id: str) -> list:
    """MongoDB se chat history lao"""
    doc = conversations_col.find_one({"session_id": session_id})
    if doc:
        return doc.get("messages", [])
    return []

def save_message(session_id: str, role: str, content: str):
    """Message MongoDB mein save karo"""
    conversations_col.update_one(
        {"session_id": session_id},
        {
            "$push": {
                "messages": {
                    "role": role,
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                }
            },
            "$set": {"updated_at": datetime.now().isoformat()}
        },
        upsert=True
    )

# ─────────────────────────────────────────
# AGENT
# ─────────────────────────────────────────
tools = [
    get_qari_list,
    check_slot_availability,
    book_appointment_tool,
    get_fitrana_rate,
    record_donation_tool,
    save_admission_tool
]

llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = """
Aap Al-Noor Madrasa ke AI Assistant hain.
Urdu aur English dono mein jawab dein.

Aap yeh kaam kar sakte hain:
1. Quran Khani appointment book karna
2. Admission karwana
3. Donation record karna
4. General maloomat dena

Hamesha short aur clear jawab dein (3-4 lines).
Respectful tone rakhein.
"""

def run_agent(user_message: str, session_id: str) -> str:
    try:
        # History load karo
        history = get_history(session_id)

        # Messages banao
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        for h in history[-10:]:
            messages.append({
                "role": h["role"],
                "content": h["content"]
            })
        
        messages.append({
            "role": "user",
            "content": user_message
        })

        # Gemini call karo
        response = llm_with_tools.invoke(messages)
        reply = response.content

        # History save karo
        save_message(session_id, "user", user_message)
        save_message(session_id, "assistant", reply)

        return reply

    except Exception as e:
        print(f"Agent Error: {e}")
        return f"Maafi, kuch masla aa gaya: {str(e)}"