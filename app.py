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
    # 1. Capture Form Data (Added client_email)
    client_nom = request.form.get("client_nom")
    client_tel = request.form.get("client_telephone")
    client_email = request.form.get("client_email")
    lieu = request.form.get("lieu_service")
    adresse = request.form.get("client_adresse", "")
    serv_id = request.form.get("service_id")
    stylist_id = request.form.get("stylist_id")
    date = request.form.get("selected_date")
    time = request.form.get("selected_time")

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Validate Price
        cursor.execute("SELECT prix FROM coiffeuse_services WHERE coiffeuse_id = %s AND service_id = %s", (stylist_id, serv_id))
        prix = cursor.fetchone()['prix']

        # Insert Booking (Including email)
        cursor.execute("""
            INSERT INTO rendezvous (client_nom, client_telephone, client_email, lieu_service, adresse, date_rendezvous, heure_rendezvous, statut, prix_final, coiffeuse_id, service_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'En attente', %s, %s, %s)
            RETURNING id;
        """, (client_nom, client_tel, client_email, lieu, adresse, date, time, float(prix), stylist_id, serv_id))
        
        booking_id = cursor.fetchone()['id']

        # Lock Slot
        cursor.execute("""
            UPDATE horaires SET statut = 'Reserve' 
            WHERE coiffeuse_id = %s AND date_jour = %s AND heure_debut = %s
        """, (stylist_id, date, time))
        
        conn.commit()
        
        # Fetch the record to show confirmation details
        cursor.execute("SELECT * FROM rendezvous WHERE id = %s", (booking_id,))
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