from pymongo import MongoClient
import os

# MongoDB Connection (अपना लिंक यहाँ डालें)
#MONGO_URL = "mongodb+srv://user:password@cluster.mongodb.net/myDatabase?retryWrites=true&w=majority"
MONGO_URL = "mongodb+srv://admin:Mk626425@lootcampainbot.5bzimnz.mongodb.net/?appName=Lootcampainbot"
client = MongoClient(MONGO_URL)
db = client['timesofvedanta_db']

# Collections (Tables)
offers_col = db['offers']
users_col = db['users']

def get_all_offers():
    # यह डेटाबेस से सारे ऑफर्स लाएगा
    return list(offers_col.find({}))

def save_offer(oid, name, status, prize, steps, terms, c_link, t_link):
    # यह एडमिन पैनल से ऑफर सेव करेगा
    offers_col.update_one(
        {"id": str(oid)},
        {"$set": {
            "name": name, "status": status, "prize": prize,
            "steps": steps, "terms": terms, 
            "claim_link": c_link, "track_link": t_link
        }},
        upsert=True
    )

def get_offer_by_id(oid):
    # किसी एक ऑफर की डिटेल के लिए
    return offers_col.find_one({"id": str(oid)})
