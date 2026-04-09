from pymongo import MongoClient
import os

# MongoDB Connection
MONGO_URL = "mongodb+srv://admin:Mk626425@lootcampainbot.5bzimnz.mongodb.net/?appName=Lootcampainbot"
client = MongoClient(MONGO_URL)
db = client['timesofvedanta_db']
offers_col = db['offers']

def get_all_offers():
    return list(offers_col.find({}))

def save_offer(name, status, expiry, prize, steps, terms, c_link, t_link):
    oid = str(int(time.time())) if 'time' in globals() else str(abs(hash(name)))
    offers_col.update_one(
        {"name": name},
        {"$set": {
            "id": oid,
            "name": name, 
            "status": status, 
            "expiry": expiry,
            "prize": prize,
            "steps": steps, 
            "terms": terms, 
            "claim_link": c_link, 
            "track_link": t_link
        }},
        upsert=True
    )

def get_offer_by_id(oid):
    return offers_col.find_one({"id": str(oid)})

def delete_offer_by_id(oid):
    offers_col.delete_one({"id": str(oid)})
