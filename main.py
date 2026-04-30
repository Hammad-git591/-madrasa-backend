from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from database import (
    init_data, qari_col, admissions_col,
    appointments_col, donations_col,
    campaigns_col, settings_col, users_col
)
from bson import ObjectId
from datetime import datetime
import os
import time

load_dotenv()
init_data()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)
# ─────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────
def fix_id(doc):
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc

def fix_ids(docs):
    return [fix_id(d) for d in docs]

# ─────────────────────────────────────────
# ROOT ROUTES
# ─────────────────────────────────────────
@app.get("/")
def home():
    return {"message": "Al-Noor Madrasa API Chal Rahi Hai! 🕌"}

@app.get("/api")
def api_root():
    return {"message": "Al-Noor Madrasa API! 🕌"}

@app.get("/api/")
def api_root_slash():
    return {"message": "Al-Noor Madrasa API! 🕌"}

# ─────────────────────────────────────────
# QARI APIs
# ─────────────────────────────────────────
@app.get("/api/qari")
def get_all_qari():
    return fix_ids(list(qari_col.find()))

@app.get("/api/qari/{qari_id}")
def get_one_qari(qari_id: str):
    qari = qari_col.find_one({"_id": ObjectId(qari_id)})
    if not qari:
        raise HTTPException(404, "Qari nahi mila")
    return fix_id(qari)

@app.post("/api/qari")
def add_qari(data: dict):
    result = qari_col.insert_one(data)
    return {"status": "success", "id": str(result.inserted_id)}

@app.put("/api/qari/{qari_id}")
def update_qari(qari_id: str, data: dict):
    qari_col.update_one(
        {"_id": ObjectId(qari_id)},
        {"$set": data}
    )
    return {"status": "updated"}

@app.delete("/api/qari/{qari_id}")
def delete_qari(qari_id: str):
    qari_col.delete_one({"_id": ObjectId(qari_id)})
    return {"status": "deleted"}

# ─────────────────────────────────────────
# ADMISSION APIs
# ─────────────────────────────────────────
@app.post("/api/admission")
def add_admission(data: dict):
    data["date_added"] = datetime.now().isoformat()
    data["status"] = "active"
    result = admissions_col.insert_one(data)
    if "qari_id" in data:
        qari_col.update_one(
            {"_id": ObjectId(data["qari_id"])},
            {"$push": {"students": str(result.inserted_id)}}
        )
    return {"status": "success", "id": str(result.inserted_id)}

@app.get("/api/admissions")
def get_admissions():
    admissions = list(admissions_col.find())
    for a in admissions:
        a["_id"] = str(a["_id"])
        if "qari_id" in a:
            qari = qari_col.find_one({"_id": ObjectId(a["qari_id"])})
            a["qari_name"] = qari["name"] if qari else "Unknown"
    return admissions

@app.put("/api/admission/{admission_id}")
def update_admission(admission_id: str, data: dict):
    admissions_col.update_one(
        {"_id": ObjectId(admission_id)},
        {"$set": data}
    )
    return {"status": "updated"}

@app.delete("/api/admission/{admission_id}")
def delete_admission(admission_id: str):
    admissions_col.delete_one({"_id": ObjectId(admission_id)})
    return {"status": "deleted"}

@app.get("/api/admissions/monthly")
def monthly_admissions():
    pipeline = [
        {
            "$group": {
                "_id": {"$substr": ["$date_added", 0, 7]},
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    return list(admissions_col.aggregate(pipeline))

# ─────────────────────────────────────────
# APPOINTMENT APIs
# ─────────────────────────────────────────
@app.post("/api/appointment")
def book_appointment(data: dict):
    clash = appointments_col.find_one({
        "qari_id": data["qari_id"],
        "date": data["date"],
        "time_slot": data["time_slot"],
        "status": "confirmed"
    })
    if clash:
        return {
            "status": "unavailable",
            "message": "Yeh slot already booked hai!"
        }
    data["date_added"] = datetime.now().isoformat()
    data["status"] = "confirmed"
    result = appointments_col.insert_one(data)
    return {"status": "success", "id": str(result.inserted_id)}

@app.get("/api/appointments")
def get_appointments():
    appointments = list(appointments_col.find())
    for a in appointments:
        a["_id"] = str(a["_id"])
        if "qari_id" in a:
            qari = qari_col.find_one({"_id": ObjectId(a["qari_id"])})
            a["qari_name"] = qari["name"] if qari else "Unknown"
    return appointments

@app.get("/api/appointments/slots/{qari_id}/{date}")
def get_booked_slots(qari_id: str, date: str):
    booked = list(appointments_col.find({
        "qari_id": qari_id,
        "date": date,
        "status": "confirmed"
    }))
    slots = [b["time_slot"] for b in booked]
    return {"booked_slots": slots}

@app.put("/api/appointment/{appointment_id}")
def update_appointment(appointment_id: str, data: dict):
    appointments_col.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": data}
    )
    return {"status": "updated"}

@app.delete("/api/appointment/{appointment_id}")
def cancel_appointment(appointment_id: str):
    appointments_col.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": {"status": "cancelled"}}
    )
    return {"status": "cancelled"}

# ─────────────────────────────────────────
# DONATION APIs
# ─────────────────────────────────────────
@app.post("/api/donation")
def add_donation(data: dict):
    data["date_added"] = datetime.now().isoformat()
    data["receipt_no"] = f"DN-{int(time.time())}"
    result = donations_col.insert_one(data)
    if "campaign_id" in data and data["campaign_id"]:
        campaigns_col.update_one(
            {"_id": ObjectId(data["campaign_id"])},
            {"$inc": {"collected": data["amount"]}}
        )
    return {
        "status": "success",
        "receipt_no": data["receipt_no"],
        "id": str(result.inserted_id)
    }

@app.get("/api/donations")
def get_donations():
    return fix_ids(list(donations_col.find().sort("date_added", -1)))

@app.get("/api/donations/summary")
def donation_summary():
    total_result = list(donations_col.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]))
    total = total_result[0]["total"] if total_result else 0
    by_type = list(donations_col.aggregate([
        {"$group": {"_id": "$type", "amount": {"$sum": "$amount"}}}
    ]))
    top_donors = list(donations_col.aggregate([
        {"$group": {
            "_id": "$donor_name",
            "total": {"$sum": "$amount"}
        }},
        {"$sort": {"total": -1}},
        {"$limit": 5}
    ]))
    return {
        "total": total,
        "by_type": by_type,
        "top_donors": top_donors
    }

@app.get("/api/campaigns")
def get_campaigns():
    campaigns = list(campaigns_col.find())
    for c in campaigns:
        c["_id"] = str(c["_id"])
        if c.get("target", 0) > 0:
            c["progress"] = round(
                (c.get("collected", 0) / c["target"]) * 100, 1
            )
    return campaigns

@app.post("/api/campaign")
def add_campaign(data: dict):
    data["collected"] = 0
    data["date_added"] = datetime.now().isoformat()
    data["status"] = "active"
    result = campaigns_col.insert_one(data)
    return {"status": "success", "id": str(result.inserted_id)}

# ─────────────────────────────────────────
# ADMIN APIs
# ─────────────────────────────────────────
@app.post("/api/admin/login")
def admin_login(data: dict):
    email = data.get("email")
    password = data.get("password")
    if email == "admin@madrasa.com" and password == "admin123":
        return {
            "status": "success",
            "token": "admin-token-madrasa",
            "role": "admin"
        }
    raise HTTPException(401, "Email ya password galat hai")

@app.get("/api/settings")
def get_settings():
    settings = settings_col.find_one()
    return fix_id(settings)

@app.put("/api/settings")
def update_settings(data: dict):
    settings_col.update_one(
        {},
        {"$set": data}
    )
    return {"status": "updated"}

@app.get("/api/admin/stats")
def admin_stats():
    total_students = admissions_col.count_documents({"status": "active"})
    total_qari = qari_col.count_documents({})
    active_qari = qari_col.count_documents({"available": True})
    upcoming_appointments = appointments_col.count_documents({
        "status": "confirmed",
        "date": {"$gte": datetime.now().strftime("%Y-%m-%d")}
    })
    total_donations = list(donations_col.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]))
    return {
        "total_students": total_students,
        "total_qari": total_qari,
        "active_qari": active_qari,
        "upcoming_appointments": upcoming_appointments,
        "total_donations": total_donations[0]["total"] if total_donations else 0
    }

# ─────────────────────────────────────────
# CHAT API
# ─────────────────────────────────────────
@app.post("/api/chat")
def chat(data: dict):
    from agent import run_agent
    message = data.get("message", "")
    session_id = data.get("session_id", "default")
    reply = run_agent(message, session_id)
    return {"reply": reply}

@app.get("/api/history/{session_id}")
def get_chat_history(session_id: str):
    from database import conversations_col
    doc = conversations_col.find_one({"session_id": session_id})
    if doc:
        return {"messages": doc.get("messages", [])}
    return {"messages": []}