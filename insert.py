import os
import psycopg2
from werkzeug.security import generate_password_hash

def reset_passwords():
    print("Connecting to database...")
    
    # Hardcoded IPv4 Pooler URL to bypass the Windows IPv6 DNS error
    database_url = "postgresql://postgres.vglivtbmjtxgsfswxvpd:Kar1ee$9rey541@aws-1-ca-central-1.pooler.supabase.com:5432/postgres"
    
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    try:
        # Generate REAL cryptographic hashes for the passwords
        admin_hash = generate_password_hash('Admin123!')
        stylist_hash = generate_password_hash('Stylist123!')

        # Update the Super Admin
        cursor.execute("""
            UPDATE users 
            SET password_hash = %s 
            WHERE email = 'Tashastevepay@gmail.com'
        """, (admin_hash,))
        
        # Update the Stylists
        cursor.execute("""
            UPDATE users 
            SET password_hash = %s 
            WHERE email IN ('amina@coiffconnect.com', 'sarah@coiffconnect.com', 'celine@coiffconnect.com')
        """, (stylist_hash,))

        conn.commit()
        print("✅ Passwords successfully updated with valid hashes!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    reset_passwords()