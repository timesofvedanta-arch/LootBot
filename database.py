from pymongo import MongoClient
import os

# आपका MongoDB URL
MONGO_URL = "mongodb+srv://admin:Mk626425@lootcampainbot.5bzimnz.mongodb.net/?appName=Lootcampainbot"

client = MongoClient(MONGO_URL)
db = client['timesofvedanta_db']
offers_col = db['offers']

def get_all_offers():
    # MongoDB से सभी ऑफर्स लाना
    return list(offers_col.find({}))

def save_offer(oid, name, status, expiry, prize, steps, terms, c_link, t_link):
    # ऑफर को MongoDB में डालना या अपडेट करना
    offers_col.update_one(
        {"id": str(oid)},
        {"$set": {
            "id": str(oid), 
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
    # आईडी से ऑफर ढूंढना
    return offers_col.find_one({"id": str(oid)})

def delete_offer_by_id(oid):
    # ऑफर डिलीट करना
    offers_col.delete_one({"id": str(oid)})
