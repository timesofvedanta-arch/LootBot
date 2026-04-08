import sqlite3
from datetime import datetime, timedelta

def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS offers 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, status TEXT DEFAULT 'active', 
        expiry_date DATETIME, icon_url TEXT, details TEXT, claim_link TEXT, 
        track_link TEXT, price TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS submissions 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, user_name TEXT, 
        offer_id INTEGER, offer_name TEXT, upi_id TEXT, amount TEXT, 
        status TEXT DEFAULT 'pending', proof_photo TEXT)''')
    conn.commit()
    conn.close()

def add_offer_db(data):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    expiry = datetime.now() + timedelta(days=int(data.get('days', 0)))
    cursor.execute('''INSERT INTO offers (name, expiry_date, icon_url, details, price, claim_link, track_link) 
                      VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                   (data['name'], expiry, data.get('icon', 'N/A'), data.get('details', 'N/A'), 
                    data.get('price', '0'), data.get('claim', '#'), data.get('track', '#')))
    conn.commit()
    conn.close()

def get_all_offers():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM offers WHERE status = 'active'")
    rows = cursor.fetchall()
    conn.close()
    return rows
