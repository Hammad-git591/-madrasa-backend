from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langgraph.graph import StateGraph, END
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

load_dotenv()

# ─────────────────────────────────────────
# LLM — Gemini
# ─────────────────────────────────────────
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.7
)

# ─────────────────────────────────────────
# TOOLS — Agent ke haath pair
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
    """Qari ka slot check karo — kaunsa waqt available hai"""
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
    # Double booking check
    clash = appointments_col.find_one({
        "qari_id": qari_id,
        "date": date,
        "time_slot": time_slot,
        "status": "confirmed"
    })
    if clash:
        return {"status": "unavailable",
                "message": "Yeh slot booked hai!"}

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
    import time
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
        "qari_id": qa