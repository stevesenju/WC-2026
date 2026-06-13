from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import psycopg2
import psycopg2.extras
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super_secret_dev_key")

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

# --- PUBLIC ROUTES ---

@app.route("/")
def home():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT nom, description, statut, slug FROM categories ORDER BY id;")
    categories = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return render_template("index.html", categories=categories)

@app.route("/services/<category_slug>")
def styles(category_slug):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT id, nom, description, image_url FROM services WHERE categorie = %s;", (category_slug,))
    services = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT nom FROM categories WHERE slug = %s;", (category_slug,))
    cat_row = cursor.fetchone()
    cat_name = cat_row['nom'] if cat_row else "Services"
    cursor.close()
    conn.close()
    return render_template("styles.html", services=services, category_name=cat_name)

@app.route("/booking/<int:service_id>")
def booking(service_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT id, nom, description, image_url FROM services WHERE id = %s;", (service_id,))
    service = dict(cursor.fetchone()) if cursor.rowcount > 0 else None
    cursor.close()
    conn.close()
    if not service: return "Service non trouvé", 404
    return render_template("booking.html", service=service)

# --- API ROUTES ---

@app.route("/api/available-stylists/<int:service_id>/<date_str>")
def get_available_stylists(service_id, date_str):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    def build_stylist(c_id, alias, pref, prix, date_dispo=None):
        cursor.execute("SELECT image_url FROM portfolio_images WHERE coiffeuse_id = %s AND service_id = %s", (c_id, service_id))
        imgs = [img['image_url'] for img in cursor.fetchall()]
        return {"id": c_id, "alias": alias, "deplacement_pref": pref, "prix": float(prix), "images": imgs, "date_dispo": date_dispo}

    cursor.execute("""
        SELECT DISTINCT c.id, c.alias, c.deplacement_pref, cs.prix 
        FROM coiffeuses c
        JOIN coiffeuse_services cs ON c.id = cs.coiffeuse_id
        JOIN horaires h ON c.id = h.coiffeuse_id
        WHERE cs.service_id = %s AND h.date_jour = %s AND h.statut = 'Libre';
    """, (service_id, date_str))
    exact = [build_stylist(row['id'], row['alias'], row['deplacement_pref'], row['prix']) for row in cursor.fetchall()]
    
    close = []
    if len(exact) <= 1:
        cursor.execute("""
            SELECT DISTINCT c.id, c.alias, c.deplacement_pref, cs.prix, h.date_jour 
            FROM coiffeuses c
            JOIN coiffeuse_services cs ON c.id = cs.coiffeuse_id
            JOIN horaires h ON c.id = h.coiffeuse_id
            WHERE cs.service_id = %s 
              AND h.date_jour BETWEEN %s::date - INTERVAL '3 days' AND %s::date + INTERVAL '3 days'
              AND h.date_jour != %s
              AND h.statut = 'Libre'
            ORDER BY h.date_jour ASC;
        """, (service_id, date_str, date_str, date_str))
        exact_ids = [s['id'] for s in exact]
        for row in cursor.fetchall():
            if row['id'] not in exact_ids:
                close.append(build_stylist(row['id'], row['alias'], row['deplacement_pref'], row['prix'], row['date_jour'].strftime('%Y-%m-%d')))
    
    cursor.close()
    conn.close()
    return jsonify({"exact_matches": exact, "close_matches": close})

@app.route("/api/times/<int:stylist_id>/<date_str>")
def get_times(stylist_id, date_str):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT heure_debut FROM horaires WHERE coiffeuse_id = %s AND date_jour = %s AND statut = 'Libre' ORDER BY heure_debut;", (stylist_id, date_str))
    times = [row['heure_debut'].strftime('%H:%M') for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify({"times": times})

# --- TRANSACTIONAL ROUTE ---

@app.route("/submit-booking", methods=["POST"])
def submit_booking():
    # 1. Capture Form Data
    client_nom = request.form.get("client_nom")
    client_telephone = request.form.get("client_telephone")
    client_email = request.form.get("client_email")
    lieu_service = request.form.get("lieu_service")
    client_adresse = request.form.get("client_adresse", "")
    
    service_id = request.form.get("service_id")
    stylist_id = request.form.get("stylist_id")
    selected_date = request.form.get("selected_date")
    selected_time = request.form.get("selected_time")

    # 2. Map form data to your exact schema
    transport_req = True if lieu_service == "domicile" else False

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Get the exact price
        cursor.execute("SELECT prix FROM coiffeuse_services WHERE coiffeuse_id = %s AND service_id = %s", (stylist_id, service_id))
        prix_total = cursor.fetchone()['prix']

        # Look up the actual horaire_id using the date and time they picked
        cursor.execute("""
            SELECT id FROM horaires 
            WHERE coiffeuse_id = %s AND date_jour = %s AND heure_debut = %s AND statut = 'Libre'
        """, (stylist_id, selected_date, selected_time))
        
        horaire_row = cursor.fetchone()
        if not horaire_row:
            raise Exception("Ce créneau n'est plus disponible.")
        
        horaire_id = horaire_row['id']

        # 3. Insert Booking using YOUR exact columns
        cursor.execute("""
            INSERT INTO rendezvous (
                client_nom, client_email, client_telephone, client_adresse, 
                coiffeuse_id, service_id, horaire_id, transport_req, prix_total, statut
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'En_Attente')
            RETURNING id;
        """, (client_nom, client_email, client_telephone, client_adresse, stylist_id, service_id, horaire_id, transport_req, float(prix_total)))
        
        booking_id = cursor.fetchone()['id']

        # 4. Lock the Slot using the ID
        cursor.execute("UPDATE horaires SET statut = 'Reserve' WHERE id = %s", (horaire_id,))
        
        conn.commit()
        
        # 5. Fetch the combined data to show on the confirmation page
        cursor.execute("""
            SELECT r.id, r.client_nom, r.prix_total as prix_final, 
                   h.date_jour as date_rendezvous, h.heure_debut as heure_rendezvous
            FROM rendezvous r
            JOIN horaires h ON r.horaire_id = h.id
            WHERE r.id = %s
        """, (booking_id,))
        booking_data = dict(cursor.fetchone())
        
        return render_template("confirmation.html", booking=booking_data)
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        flash("Une erreur est survenue lors de la réservation.", "error")
        return redirect(url_for('home'))
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    app.run(debug=True)