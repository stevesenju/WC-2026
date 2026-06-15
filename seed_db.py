import psycopg2
import os
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

def reset_and_seed():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    cursor = conn.cursor()

    try:
        print("🧹 Wiping old dummy data...")
        cursor.execute("TRUNCATE TABLE users, rendezvous, horaires, coiffeuse_services, coiffeuses RESTART IDENTITY CASCADE;")

        print("🌱 Injecting real test data...")
        
        # 1. Create the Barber Profile
        cursor.execute("""
            INSERT INTO coiffeuses (alias, telephone, deplacement_pref)
            VALUES ('Alex le Pro', '819-555-0123', 'domicile')
            RETURNING id;
        """)
        alex_id = cursor.fetchone()[0]

        # 2. DYNAMICALLY grab a valid service ID (No more hardcoded '1')
        cursor.execute("SELECT id FROM services LIMIT 1;")
        service_row = cursor.fetchone()
        
        if not service_row:
            raise Exception("Your 'services' table is empty! Please add at least one service/category to your database first.")
            
        valid_service_id = service_row[0]

        # 3. Link Alex to that specific service
        cursor.execute("""
            INSERT INTO coiffeuse_services (coiffeuse_id, service_id, prix)
            VALUES (%s, %s, 45.00);
        """, (alex_id, valid_service_id))

        # 4. Create the Accounts
        admin_pw = generate_password_hash("N3tw0rk541")
        barber_pw = generate_password_hash("alex123")

        cursor.execute("""
            INSERT INTO users (email, password_hash, role, coiffeuse_id)
            VALUES 
            ('ktashastevebrayan@gmail.com', %s, 'SuperAdmin', NULL),
            ('alex@worldconnect.ca', %s, 'Stylist', %s);
        """, (admin_pw, barber_pw, alex_id))

        conn.commit()
        print("✅ Database successfully reset and seeded!")
        print("--------------------------------------------------")
        print("👑 SuperAdmin Login: ktashastevebrayan@gmail.com | PW: N3tw0rk541")
        print("✂️  Stylist Login:    alex@worldconnect.ca  | PW: alex123")
        print("--------------------------------------------------")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error during seeding: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    reset_and_seed()