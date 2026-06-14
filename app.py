from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import psycopg2
import psycopg2.extras
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import random
import string


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super_secret_dev_key")

UPLOAD_FOLDER = os.path.join('static', 'uploads', 'styles')
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # This auto-creates the folder so it doesn't crash
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


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

    # 2. Map form data & Generate Interac Code
    transport_req = True if lieu_service == "domicile" else False
    
    # NEW: Generate a random 6-character code (e.g., A7X9P2)
    code_interac = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

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

        # 3. Insert Booking with the NEW code_interac
        cursor.execute("""
            INSERT INTO rendezvous (
                client_nom, client_email, client_telephone, client_adresse, 
                coiffeuse_id, service_id, horaire_id, transport_req, prix_total, statut, code_interac
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'En_Attente', %s)
            RETURNING id;
        """, (client_nom, client_email, client_telephone, client_adresse, stylist_id, service_id, horaire_id, transport_req, float(prix_total), code_interac))
        
        booking_id = cursor.fetchone()['id']

        # 4. Lock the Slot using the ID
        cursor.execute("UPDATE horaires SET statut = 'Reserve' WHERE id = %s", (horaire_id,))
        
        conn.commit()
        
        # 5. Fetch the combined data to show on the confirmation page (now including code_interac)
        cursor.execute("""
            SELECT r.id, r.client_nom, r.prix_total as prix_final, r.code_interac, r.transport_req, r.client_adresse,
                   h.date_jour as date_rendezvous, h.heure_debut as heure_rendezvous,
                   c.adresse_studio
            FROM rendezvous r
            JOIN horaires h ON r.horaire_id = h.id
            JOIN coiffeuses c ON r.coiffeuse_id = c.id
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

# -------------------------------------------------------------------
# ADMIN & SECURITY ROUTES
# -------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    # If they are already logged in, send them straight to the dashboard
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard'))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            # Verify user exists and password matches
            if user and check_password_hash(user['password_hash'], password):
                # Lock in the secure session variables
                session['user_id'] = user['id']
                session['role'] = user['role']
                session['coiffeuse_id'] = user['coiffeuse_id']
                
                flash(f"Bienvenue, accès {user['role']} accordé.", "success")
                return redirect(url_for('admin_dashboard'))
            else:
                flash("Identifiants incorrects. Veuillez réessayer.", "error")
                
        except Exception as e:
            print(f"Login Error: {e}")
            flash("Erreur système.", "error")
        finally:
            cursor.close()
            conn.close()
            
    return render_template("admin/login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Vous avez été déconnecté en toute sécurité.", "success")
    return redirect(url_for('admin_login'))

@app.route("/admin/dashboard")
def admin_dashboard():
    # Security Check
    if 'user_id' not in session:
        flash("Veuillez vous connecter pour accéder au portail.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    role = session.get('role')
    coiffeuse_id = session.get('coiffeuse_id')

    try:
        # 1. ADMIN VIEW: See everything (UPDATED with code_interac & client_adresse)
        if role in ['SuperAdmin', 'Admin', 'Financial']:
            cursor.execute("""
                SELECT r.id, r.client_nom, r.client_telephone, r.transport_req, r.client_adresse, r.prix_total, r.statut, r.code_interac,
                       h.date_jour, h.heure_debut, c.alias as stylist_name, s.nom as service_name
                FROM rendezvous r
                JOIN horaires h ON r.horaire_id = h.id
                JOIN coiffeuses c ON r.coiffeuse_id = c.id
                JOIN services s ON r.service_id = s.id
                ORDER BY h.date_jour ASC, h.heure_debut ASC;
            """)
            
        # 2. STYLIST VIEW: See only their own (UPDATED with code_interac & client_adresse)
        else:
            cursor.execute("""
                SELECT r.id, r.client_nom, r.client_telephone, r.transport_req, r.client_adresse, r.prix_total, r.statut, r.code_interac,
                       h.date_jour, h.heure_debut, s.nom as service_name
                FROM rendezvous r
                JOIN horaires h ON r.horaire_id = h.id
                JOIN services s ON r.service_id = s.id
                WHERE r.coiffeuse_id = %s
                ORDER BY h.date_jour ASC, h.heure_debut ASC;
            """, (coiffeuse_id,))
            
        appointments = cursor.fetchall()
        
    except Exception as e:
        print(f"Dashboard Error: {e}")
        appointments = []
        flash("Erreur lors du chargement des données.", "error")
    finally:
        cursor.close()
        conn.close()

    return render_template("admin/dashboard.html", appointments=appointments, role=role)

# --- NEW ROUTE: CANCELLATION ---
@app.route("/admin/cancel/<int:appt_id>", methods=["POST"])
def cancel_appointment(appt_id):
    # Security Check
    if session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Accès refusé.", "error")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Find the horaire_id attached to this appointment so we can free it
        cursor.execute("SELECT horaire_id FROM rendezvous WHERE id = %s;", (appt_id,))
        row = cursor.fetchone()
        
        if row:
            horaire_id = row[0]
            # 2. Free up the time slot on the calendar!
            cursor.execute("UPDATE horaires SET statut = 'Libre' WHERE id = %s;", (horaire_id,))
            
            # 3. Mark the appointment as Cancelled
            cursor.execute("UPDATE rendezvous SET statut = 'Annule' WHERE id = %s;", (appt_id,))
            conn.commit()
            flash("Rendez-vous annulé. La plage horaire est de nouveau disponible pour les autres clients.", "success")
        
    except Exception as e:
        conn.rollback()
        print(f"Cancel Error: {e}")
        flash("Erreur lors de l'annulation.", "error")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/confirm/<int:appt_id>", methods=["POST"])
def confirm_appointment(appt_id):
    # Security Check: Only high-level operators can confirm money deposits
    if session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Accès refusé. Vous n'avez pas l'autorisation de confirmer des dépôts.", "error")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Flip the status in the database
        cursor.execute("UPDATE rendezvous SET statut = 'Confirme' WHERE id = %s;", (appt_id,))
        conn.commit()
        
        # [Future Email Automation Block Will Go Here]
        
        flash("Rendez-vous confirmé avec succès ! Le statut a été mis à jour.", "success")
        
    except Exception as e:
        conn.rollback()
        print(f"Confirmation Error: {e}")
        flash("Erreur lors de la confirmation du rendez-vous.", "error")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('admin_dashboard'))


@app.route("/admin/manage", methods=["GET", "POST"])
def admin_manage():
    # Security Check: Only Admins can manage the roster
    if session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Accès refusé. Vous n'avez pas l'autorisation de gérer le personnel.", "error")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # If the admin submits the form to add a new barber
    if request.method == "POST":
        alias = request.form.get("alias")
        telephone = request.form.get("telephone")
        pref = request.form.get("deplacement_pref")
        adresse_studio = request.form.get("adresse_studio", "") # NEW

        try:
            cursor.execute("""
                INSERT INTO coiffeuses (alias, telephone, deplacement_pref, adresse_studio)
                VALUES (%s, %s, %s, %s)
            """, (alias, telephone, pref, adresse_studio))
            conn.commit()
            flash(f"L'opérateur {alias} a été ajouté avec succès !", "success")
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash("Ce nom d'affichage (alias) existe déjà. Veuillez en choisir un autre.", "error")
        except Exception as e:
            conn.rollback()
            print(f"Error adding stylist: {e}")
            flash("Erreur système lors de l'ajout.", "error")
            
        return redirect(url_for('admin_manage'))

    # GET request: Fetch the current roster to display
    try:
        # UPDATED: Added adresse_studio to the SELECT query
        cursor.execute("SELECT id, alias, telephone, deplacement_pref, adresse_studio, created_at FROM coiffeuses ORDER BY id;")
        stylists = cursor.fetchall()
    except Exception as e:
        print(f"Fetch Error: {e}")
        stylists = []
    finally:
        cursor.close()
        conn.close()

    return render_template("admin/manage.html", stylists=stylists)


@app.route("/admin/manage/edit/<int:stylist_id>", methods=["POST"])
def edit_stylist(stylist_id):
    # Security Check
    if session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Accès refusé. Vous n'avez pas l'autorisation de modifier le personnel.", "error")
        return redirect(url_for('admin_dashboard'))

    alias = request.form.get("alias")
    telephone = request.form.get("telephone")
    pref = request.form.get("deplacement_pref")
    adresse_studio = request.form.get("adresse_studio", "") # NEW

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE coiffeuses 
            SET alias = %s, telephone = %s, deplacement_pref = %s, adresse_studio = %s
            WHERE id = %s
        """, (alias, telephone, pref, adresse_studio, stylist_id))
        conn.commit()
        flash("Le profil a été mis à jour avec succès !", "success")
        
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash("Erreur: Ce nom d'affichage est déjà pris par un autre opérateur.", "error")
    except Exception as e:
        conn.rollback()
        print(f"Update Error: {e}")
        flash("Erreur lors de la mise à jour du profil.", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_manage'))

@app.route("/admin/schedule", methods=["GET", "POST"])
def admin_schedule():
    # Security Check
    if session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Accès refusé. Autorisation requise.", "error")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == "POST":
        coiffeuse_id = request.form.get("coiffeuse_id")
        date_jour = request.form.get("date_jour")
        heure_debut = request.form.get("heure_debut")
        heure_fin = request.form.get("heure_fin")
        duree_minutes = int(request.form.get("duree_minutes", 60)) # New: grabs duration

        try:
            start_dt = datetime.strptime(f"{date_jour} {heure_debut}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{date_jour} {heure_fin}", "%Y-%m-%d %H:%M")
            
            # Dynamic slot duration based on what you picked in the dropdown
            slot_duration = timedelta(minutes=duree_minutes)
            current_time = start_dt
            
            slots_created = 0
            
            # The loop chops the shift into blocks of your chosen size
            while current_time + slot_duration <= end_dt:
                slot_end = current_time + slot_duration
                
                h_deb_str = current_time.strftime("%H:%M:%S")
                h_fin_str = slot_end.strftime("%H:%M:%S")
                
                cursor.execute("""
                    SELECT id FROM horaires 
                    WHERE coiffeuse_id = %s AND date_jour = %s AND heure_debut = %s
                """, (coiffeuse_id, date_jour, h_deb_str))
                
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO horaires (coiffeuse_id, date_jour, heure_debut, heure_fin, statut)
                        VALUES (%s, %s, %s, %s, 'Libre')
                    """, (coiffeuse_id, date_jour, h_deb_str, h_fin_str))
                    slots_created += 1
                
                current_time += slot_duration
                
            conn.commit()
            flash(f"Succès ! {slots_created} créneaux de {duree_minutes} minutes ont été générés.", "success")

        except Exception as e:
            conn.rollback()
            print(f"Schedule Generator Error: {e}")
            flash("Erreur lors de la génération de l'horaire.", "error")
            
        return redirect(url_for('admin_schedule'))

    # GET request logic stays exactly the same
   # UPDATE THIS BLOCK INSIDE admin_schedule:
    try:
        cursor.execute("SELECT id, alias FROM coiffeuses ORDER BY alias;")
        stylists = cursor.fetchall()
        
    
        cursor.execute("""
            SELECT h.id, c.id as coiffeuse_id, c.alias, h.date_jour, h.heure_debut, h.heure_fin, h.statut 
            FROM horaires h
            JOIN coiffeuses c ON h.coiffeuse_id = c.id
            WHERE h.date_jour >= CURRENT_DATE AND h.statut != 'Supprime'
            ORDER BY h.date_jour ASC, h.heure_debut ASC;
        """)
        upcoming_slots = cursor.fetchall()
    except Exception as e:
    
        print(f"Fetch Error: {e}")
        stylists = []
        upcoming_slots = []
    finally:
        cursor.close()
        conn.close()

    return render_template("admin/schedule.html", stylists=stylists, slots=upcoming_slots)

@app.route("/admin/schedule/delete/<int:slot_id>", methods=["POST"])
def admin_delete_slot(slot_id):
    if session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Accès refusé.", "error")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT statut FROM horaires WHERE id = %s", (slot_id,))
        row = cursor.fetchone()
        
        if row and row[0] == 'Libre':
            # THE FIX: Soft Delete instead of hard delete
            cursor.execute("UPDATE horaires SET statut = 'Supprime' WHERE id = %s", (slot_id,))
            conn.commit()
            flash("Le créneau a été retiré de l'horaire.", "success")
        else:
            flash("Impossible de supprimer un créneau réservé. Annulez le rendez-vous d'abord.", "error")
    except Exception as e:
        conn.rollback()
        print(f"Delete Slot Error: {e}")
        flash("Erreur lors de la suppression.", "error")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('admin_schedule'))


@app.route("/admin/catalog", methods=["GET", "POST"])
def admin_catalog():
    # Security Check
    if session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Accès refusé. Autorisation requise.", "error")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == "POST":
        nom = request.form.get("nom")
        categorie_slug = request.form.get("categorie")
        description = request.form.get("description")
        
        # Handle the file upload
        image_url = ""
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename != '':
                # Clean the filename of any weird characters or spaces
                filename = secure_filename(file.filename)
                # Create the exact save path
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                # Save the physical image to your server
                file.save(filepath)
                # Format the path with a forward slash so HTML can read it
                image_url = f"/{filepath}".replace("\\", "/")

        try:
            cursor.execute("""
                    INSERT INTO services (nom, description, categorie, image_url)
                    VALUES (%s, %s, %s, %s)
                """, (nom, description, categorie_slug, image_url))
            conn.commit()
            flash(f"Le service '{nom}' a été ajouté au catalogue avec succès !", "success")
        except Exception as e:
            conn.rollback()
            print(f"Catalog Insertion Error: {e}")
            flash("Erreur lors de l'ajout du service.", "error")
            
        return redirect(url_for('admin_catalog'))

    # GET request stays exactly the same
    try:
        cursor.execute("SELECT nom, slug FROM categories ORDER BY id;")
        categories = cursor.fetchall()

        cursor.execute("""
            SELECT id, nom, categorie, description, image_url 
            FROM services 
            ORDER BY categorie, nom;
        """)
        services = cursor.fetchall()
    except Exception as e:
        print(f"Fetch Error: {e}")
        categories = []
        services = []
    finally:
        cursor.close()
        conn.close()

    return render_template("admin/catalog.html", categories=categories, services=services)

@app.route("/admin/assign-skills", methods=["GET", "POST"])
def admin_assign_skills():
    if session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Accès refusé.", "error")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == "POST":
        coiffeuse_id = request.form.get("coiffeuse_id")
        service_id = request.form.get("service_id")
        prix = request.form.get("prix")

        try:
            # We use UPSERT (ON CONFLICT) so you can update prices if they change
            cursor.execute("""
                INSERT INTO coiffeuse_services (coiffeuse_id, service_id, prix)
                VALUES (%s, %s, %s)
                ON CONFLICT (coiffeuse_id, service_id) 
                DO UPDATE SET prix = EXCLUDED.prix;
            """, (coiffeuse_id, service_id, prix))
            conn.commit()
            flash("Tarif et compétence mis à jour avec succès !", "success")
        except Exception as e:
            conn.rollback()
            print(f"Assign Error: {e}")
            flash("Erreur lors de la mise à jour.", "error")
            
        return redirect(url_for('admin_assign_skills'))

    # Fetch data for the dropdowns and the list view
    cursor.execute("SELECT id, alias FROM coiffeuses ORDER BY alias;")
    stylists = cursor.fetchall()
    
    cursor.execute("SELECT id, nom FROM services ORDER BY nom;")
    services = cursor.fetchall()

    cursor.execute("""
        SELECT c.alias, s.nom, cs.prix 
        FROM coiffeuse_services cs
        JOIN coiffeuses c ON cs.coiffeuse_id = c.id
        JOIN services s ON cs.service_id = s.id
        ORDER BY c.alias;
    """)
    current_assignments = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("admin/assign.html", stylists=stylists, services=services, assignments=current_assignments)

if __name__ == "__main__":
    app.run(debug=True)