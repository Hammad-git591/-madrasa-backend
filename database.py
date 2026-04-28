from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

# MongoDB Connect
client = MongoClient(os.getenv("MONGODB_URL"))
db = client["madrasa_db"]

# Collections (Tables ki jagah)
qari_col        = db["qari"]
admissions_col  = db["admissions"]
appointments_col= db["appointments"]
donations_col   = db["donations"]
campaigns_col   = db["campaigns"]
conversations_col= db["conversations"]
users_col       = db["users"]
settings_col    = db["settings"]

# Sample Qari Data (pehli baar insert ho)
def init_data():
    if qari_col.count_documents({}) == 0:
        qari_col.insert_many([
            {
                "name": "Qari Muhammad Yusuf",
                "since": "2015",
                "specialization": ["Hifz", "Tajweed"],
                "fee": 1500,
                "timings": ["8:00 AM", "4:00 PM", "6:00 PM"],
                "available": True,
                "rating": 4.9,
                "students": [],
                "completed_students": 47
            },
            {
                "name": "Qari Abdul Rehman",
                "since": "2018",
                "specialization": ["Nazra", "Tajweed"],
                "fee": 1200,
                "timings": ["9:00 AM", "11:00 AM", "5:00 PM"],
                "available": True,
                "rating": 4.7,
                "students": [],
                "completed_students": 31
            },
            {
                "name": "Qari Hafiz Bilal",
                "since": "2020",
                "specialization": ["Online Quran"],
                "fee": 1000,
                "timings": ["7:00 AM", "3:00 PM", "7:00 PM"],
                "available": False,
                "rating": 4.8,
                "students": [],
                "completed_students": 12
            },
        ])

    # Default settings (fitrana rate)
    if settings_col.count_documents({}) == 0:
        settings_col.insert_one({
            "fitrana_rate": 320,
            "madrasa_name": "Al-Noor Madrasa"
        })