import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import pytz
import random
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    return psycopg2.connect(database_url)

def seed_database():
    print("🔄 Connexion à la base de données...")
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        # 1. NETTOYAGE COMPLET DE LA BASE DE DONNÉES
        print("🧹 Effacement des anciennes données...")
        cursor.execute("""
            TRUNCATE TABLE rendezvous, horaires, coiffeuse_services, service_variations, 
                           services, portfolio_images, users, coiffeuses, categories 
            RESTART IDENTITY CASCADE;
        """)

        # 1.5. RÉPARATION DE LA STRUCTURE (Au cas où des colonnes ont été supprimées accidentellement)
        print("🔧 Vérification et réparation de la structure de la base...")
        cursor.execute("""
            ALTER TABLE public.coiffeuse_services 
            ADD COLUMN IF NOT EXISTS service_id INTEGER REFERENCES public.services(id) ON DELETE CASCADE;
        """)

        # 2. CRÉATION DU SUPER ADMIN
        print("👑 Création du compte SuperAdmin...")
        admin_email = "Tashastevepay@gmail.com" # Changez si nécessaire
        admin_pass = generate_password_hash("Admin123!")
        
        cursor.execute("""
            INSERT INTO users (email, password_hash, role)
            VALUES (%s, %s, 'SuperAdmin')
        """, (admin_email, admin_pass))

        # 3. CRÉATION DES CATÉGORIES
        print("📂 Création des catégories...")
        cursor.execute("INSERT INTO categories (nom, description, statut, slug) VALUES (%s, %s, %s, %s) RETURNING slug", 
                       ("Coiffure Femme", "Styles élégants pour femmes.", "Active", "coiffure-femme"))

        # 4. CRÉATION DES SERVICES ET VARIATIONS
        print("✂️ Création des services et de leurs variations...")
        
        # Service 1: Tresses (Avec variations)
        cursor.execute("INSERT INTO services (nom, categorie, description) VALUES (%s, %s, %s) RETURNING id", 
                       ("Tresses Africaines (Knotless)", "coiffure-femme", "Tresses protectrices sans nœuds."))
        tresses_id = cursor.fetchone()['id']
        
        cursor.execute("INSERT INTO service_variations (service_id, nom) VALUES (%s, %s) RETURNING id", (tresses_id, "Courtes (Épaules)"))
        var_tresses_courtes = cursor.fetchone()['id']
        cursor.execute("INSERT INTO service_variations (service_id, nom) VALUES (%s, %s) RETURNING id", (tresses_id, "Moyennes (Dos)"))
        var_tresses_moyennes = cursor.fetchone()['id']
        cursor.execute("INSERT INTO service_variations (service_id, nom) VALUES (%s, %s) RETURNING id", (tresses_id, "Longues (Taille)"))
        var_tresses_longues = cursor.fetchone()['id']

        # Service 2: Soin Afro (Prix Fixe / Standard)
        cursor.execute("INSERT INTO services (nom, categorie, description) VALUES (%s, %s, %s) RETURNING id", 
                       ("Soin Cheveux Naturels", "coiffure-femme", "Lavage, hydratation et twist out."))
        soin_id = cursor.fetchone()['id']
        cursor.execute("INSERT INTO service_variations (service_id, nom) VALUES (%s, %s) RETURNING id", (soin_id, "Standard"))
        var_soin = cursor.fetchone()['id']

        # 5. CRÉATION DES COIFFEUSES ET COMPTES DE CONNEXION
        print("👩‍🎨 Création des barbiers/coiffeuses...")
        barbers = [
            ("Amina Beauty", "514-555-0101", "amina@coiffconnect.com", "Both", "123 Rue Principale, Montréal"),
            ("Sarah Styles", "514-555-0202", "sarah@coiffconnect.com", "Domicile", "")
        ]
        
        barber_pw = generate_password_hash("Coiffure123!")
        coiffeuses_ids = {}

        for alias, tel, email, pref, studio in barbers:
            cursor.execute("""
                INSERT INTO coiffeuses (alias, telephone, email, deplacement_pref, adresse_studio)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (alias, tel, email, pref, studio))
            c_id = cursor.fetchone()['id']
            coiffeuses_ids[alias] = c_id
            
            cursor.execute("INSERT INTO users (email, password_hash, role, coiffeuse_id) VALUES (%s, %s, 'Agent', %s)", 
                           (email, barber_pw, c_id))

        # 6. ASSIGNATION DES PRIX PAR VARIATION
        print("💰 Assignation des prix spécifiques...")
        amina_id = coiffeuses_ids["Amina Beauty"]
        sarah_id = coiffeuses_ids["Sarah Styles"]

        # Amina Prices
        cursor.execute("INSERT INTO coiffeuse_services (coiffeuse_id, service_id, variation_id, prix) VALUES (%s, %s, %s, %s)", (amina_id, tresses_id, var_tresses_courtes, 100.00))
        cursor.execute("INSERT INTO coiffeuse_services (coiffeuse_id, service_id, variation_id, prix) VALUES (%s, %s, %s, %s)", (amina_id, tresses_id, var_tresses_moyennes, 130.00))
        cursor.execute("INSERT INTO coiffeuse_services (coiffeuse_id, service_id, variation_id, prix) VALUES (%s, %s, %s, %s)", (amina_id, tresses_id, var_tresses_longues, 160.00))
        cursor.execute("INSERT INTO coiffeuse_services (coiffeuse_id, service_id, variation_id, prix) VALUES (%s, %s, %s, %s)", (amina_id, soin_id, var_soin, 60.00))

        # Sarah Prices (Sarah is more expensive for braids!)
        cursor.execute("INSERT INTO coiffeuse_services (coiffeuse_id, service_id, variation_id, prix) VALUES (%s, %s, %s, %s)", (sarah_id, tresses_id, var_tresses_courtes, 110.00))
        cursor.execute("INSERT INTO coiffeuse_services (coiffeuse_id, service_id, variation_id, prix) VALUES (%s, %s, %s, %s)", (sarah_id, tresses_id, var_tresses_moyennes, 145.00))
        cursor.execute("INSERT INTO coiffeuse_services (coiffeuse_id, service_id, variation_id, prix) VALUES (%s, %s, %s, %s)", (sarah_id, tresses_id, var_tresses_longues, 180.00))

        # 7. GÉNÉRATION DES DISPONIBILITÉS (PROCHAINS 14 JOURS)
        print("📅 Génération des horaires pour les deux prochaines semaines...")
        tz = pytz.timezone('America/Toronto')
        today = datetime.now(tz).date()
        
        slots_created = 0
        for i in range(14):
            current_date = today + timedelta(days=i)
            # Skip Sundays (day 6)
            if current_date.weekday() == 6:
                continue
                
            for c_id in coiffeuses_ids.values():
                # Create 3 slots per day: 9am, 12pm, 3pm
                times = [("09:00", "11:00"), ("12:00", "14:00"), ("15:00", "17:00")]
                
                for start_str, end_str in times:
                    # Randomly make some slots "Reserve" to test the UI
                    statut = 'Reserve' if random.random() < 0.2 else 'Libre'
                    
                    cursor.execute("""
                        INSERT INTO horaires (coiffeuse_id, date_jour, heure_debut, heure_fin, statut)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (c_id, current_date, start_str, end_str, statut))
                    slots_created += 1

        conn.commit()
        print(f"✅ SUCCÈS ! La base de données a été réinitialisée et remplie avec {slots_created} créneaux horaires.")
        print("\n--- IDENTIFIANTS DE TEST ---")
        print(f"SuperAdmin : {admin_email} / Admin123!")
        print("Coiffeuses : amina@coiffconnect.com OU sarah@coiffconnect.com / Coiffure123!")

    except Exception as e:
        conn.rollback()
        print(f"❌ ERREUR LORS DU SEEDING : {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    seed_database()