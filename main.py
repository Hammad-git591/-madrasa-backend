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
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────
def fix_id(doc):
    """MongoDB _id ko string banao"""
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc

def fix_ids(docs):
    """List ke sab _id fix karo"""
    return [fix_id(d) for d in docs]


# ─────────────────────────────────────────
# TEST
# ─────────────────────────────────────────
@app.get("/")
def home():
    return {"message": "Al-Noor Madrasa API Chal Rahi Hai! 🕌"}


# ─────────────────────────────────────────
# QARI APIs
# ─────────────────────────────────────────

# Saare Qari lao
@app.get("/api/qari")
def get_all_qari():
    return fix_ids(list(qari_col.find()))

# Ek Qari lao
@app.get("/api/qari/{qari_id}")
def get_one_qari(qari_id: str):
    qari = qari_col.find_one({"_id": ObjectId(qari_id)})
    if not qari:
        raise HTTPException(404, "Qari nahi mila")
    return fix_id(qari)

# Naya Qari add karo
@app.post("/api/qari")
def add_qari(data: dict):
    result = qari_col.insert_one(data)
    return {"status": "success", "id": str(result.inserted_id)}

# Qari update karo
@app.put("/api/qari/{qari_id}")
def update_qari(qari_id: str, data: dict):
    qari_col.update_one(
        {"_id": ObjectId(qari_id)},
        {"$set": data}
    )
    return {"status": "updated"}

# Qari delete karo
@app.delete("/api/qari/{qari_id}")
def delete_qari(qari_id: str):
    qari_col.delete_one({"_id": ObjectId(qari_id)})
    return {"status": "deleted"}


# ─────────────────────────────────────────
# ADMISSION APIs
# ─────────────────────────────────────────

# Naya admission
@app.post("/api/admission")
def add_admission(data: dict):
    data["date_added"] = datetime.now().isoformat()
    data["status"] = "active"
    result = admissions_col.insert_one(data)

    # Qari ke students mein add karo
    if "qari_id" in data:
        qari_col.update_one(
            {"_id": ObjectId(data["qari_id"])},
            {"$push": {"students": str(result.inserted_id)}}
        )
    return {"status": "success", "id": str(result.inserted_id)}

# Saare admissions
@app.get("/api/admissions")
def get_admissions():
    admissions = list(admissions_col.find())
    for a in admissions:
        a["_id"] = str(a["_id"])
        if "qari_id" in a:
            qari = qari_col.find_one({"_id": ObjectId(a["qari_id"])})
            a["qari_name"] = qari["name"] if qari else "Unknown"
    return admissions

# Admission update
@app.put("/api/admission/{admission_id}")
def update_admission(admission_id: str, data: dict):
    admissions_col.update_one(
        {"_id": ObjectId(admission_id)},
        {"$set": data}
    )
    return {"status": "updated"}

# Admission delete
@app.delete("/api/admission/{admission_id}")
def delete_admission(admission_id: str):
    admissions_col.delete_one({"_id": ObjectId(admission_id)})
    return {"status": "deleted"}

# Monthly count (Admin)
@app.get("/api/admissions/monthly")
def monthly_admissions():
    pipeline = [
        {
            "$group": {
                "_id": {"$substr": ["$date_added", 0, 7]},
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}]