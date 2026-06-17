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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super_secret_dev_key")

UPLOAD_FOLDER = os.path.join('static', 'uploads', 'styles')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    return psycopg2.connect(database_url)

def send_automated_email(to_email, subject, body_html, cc_admin=False):
    sender_email = os.getenv("SMTP_USER")
    sender_password = os.getenv("SMTP_PASSWORD")
    admin_email = os.getenv("ADMIN_EMAIL")
    
    msg = MIMEMultipart()
    msg['From'] = f"Coiff'Connect <{sender_email}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    
    receivers = [to_email]
    if cc_admin and admin_email:
        receivers.append(admin_email)
        
    msg.attach(MIMEText(body_html, 'html'))
    
    try:
        print("Attempting to connect to SMTP server...")
        server = smtplib.SMTP(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", 587)), timeout=5)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receivers, msg.as_string())
        server.quit()
        print("Email sent successfully!")
        return True
    except Exception as e:
        print(f"CRITICAL EMAIL ERROR (Ignored to prevent crash): {e}")
        return False

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
    client_nom = request.form.get("client_nom")
    client_telephone = request.form.get("client_telephone")
    client_email = request.form.get("client_email")
    lieu_service = request.form.get("lieu_service")
    client_adresse = request.form.get("client_adresse", "")
    
    service_id = request.form.get("service_id")
    stylist_id = request.form.get("stylist_id")
    selected_date = request.form.get("selected_date")
    selected_time = request.form.get("selected_time")

    transport_req = True if lieu_service == "domicile" else False
    code_interac = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cursor.execute("SELECT prix FROM coiffeuse_services WHERE coiffeuse_id = %s AND service_id = %s", (stylist_id, service_id))
        prix_total = cursor.fetchone()['prix']

        cursor.execute("""
            SELECT id FROM horaires 
            WHERE coiffeuse_id = %s AND date_jour = %s AND heure_debut = %s AND statut = 'Libre'
        """, (stylist_id, selected_date, selected_time))
        
        horaire_row = cursor.fetchone()
        if not horaire_row:
            raise Exception("Ce créneau n'est plus disponible.")
        
        horaire_id = horaire_row['id']

        cursor.execute("""
            INSERT INTO rendezvous (
                client_nom, client_email, client_telephone, client_adresse, 
                coiffeuse_id, service_id, horaire_id, transport_req, prix_total, statut, code_interac
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'En_Attente', %s)
            RETURNING id;
        """, (client_nom, client_email, client_telephone, client_adresse, stylist_id, service_id, horaire_id, transport_req, float(prix_total), code_interac))
        
        booking_id = cursor.fetchone()['id']

        cursor.execute("UPDATE horaires SET statut = 'Reserve' WHERE id = %s", (horaire_id,))
        conn.commit()
        
        receipt_html = f"""
        <h2>Demande reçue, {client_nom} !</h2>
        <p>Votre demande de rendez-vous est enregistrée mais <strong>nécessite un dépôt de 5$</strong> pour être confirmée.</p>
        <p>Veuillez envoyer le virement Interac à <strong>paiement@coiffconnect.com</strong>.</p>
        <p>⚠️ <strong>IMPORTANT :</strong> Mettez ce code exact dans le message du virement : <strong style="font-size: 1.5rem; color: #c5a059;">{code_interac}</strong></p>
        <p>Nous confirmerons votre rendez-vous dès réception du dépôt.</p>
        """
        send_automated_email(client_email, "Action Requise : Votre dépôt Coiff'Connect", receipt_html, cc_admin=False)

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
    if 'user_id' in session:
        # Redirect based on role
        if session.get('role') == 'Agent':
            return redirect(url_for('stylist_dashboard'))
        return redirect(url_for('admin_dashboard'))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['role'] = user['role']
                session['coiffeuse_id'] = user['coiffeuse_id']
                
                flash(f"Bienvenue, accès {user['role']} accordé.", "success")
                
                # Split traffic here
                if user['role'] == 'Agent':
                    return redirect(url_for('stylist_dashboard'))
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

# --- STYLIST DASHBOARD (Independent) ---
@app.route("/stylist/dashboard")
def stylist_dashboard():
    if 'user_id' not in session or session.get('role') != 'Agent':
        flash("Accès refusé. Réservé aux opérateurs.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    coiffeuse_id = session.get('coiffeuse_id')

    try:
        # Get Stylist Name
        cursor.execute("SELECT alias FROM coiffeuses WHERE id = %s", (coiffeuse_id,))
        stylist_row = cursor.fetchone()
        stylist_name = stylist_row['alias'] if stylist_row else "Mon Profil"

        # Fetch ONLY confirmed, cancelled, or completed appointments (hides pending deposits)
        cursor.execute("""
            SELECT r.id, r.client_nom, r.client_telephone, r.transport_req, r.client_adresse, r.prix_total, r.statut,
                   h.date_jour, h.heure_debut, s.nom as service_name
            FROM rendezvous r
            JOIN horaires h ON r.horaire_id = h.id
            JOIN services s ON r.service_id = s.id
            WHERE r.coiffeuse_id = %s AND r.statut != 'En_Attente'
            ORDER BY h.date_jour ASC, h.heure_debut ASC;
        """, (coiffeuse_id,))
        appointments = cursor.fetchall()
        
    except Exception as e:
        print(f"Stylist Dashboard Error: {e}")
        appointments = []
        stylist_name = "Dashboard"
        flash("Erreur lors du chargement des rendez-vous.", "error")
    finally:
        cursor.close()
        conn.close()

    return render_template("stylist_dashboard.html", appointments=appointments, stylist_name=stylist_name)

# --- MASTER DASHBOARD ---
@app.route("/admin/dashboard")
def admin_dashboard():
    if 'user_id' not in session or session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Accès refusé. Privilèges administratifs requis.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    role = session.get('role')

    try:
        cursor.execute("""
            SELECT r.id, r.client_nom, r.client_telephone, r.transport_req, r.client_adresse, r.prix_total, r.statut, r.code_interac,
                   h.date_jour, h.heure_debut, c.alias as stylist_name, s.nom as service_name
            FROM rendezvous r
            JOIN horaires h ON r.horaire_id = h.id
            JOIN coiffeuses c ON r.coiffeuse_id = c.id
            JOIN services s ON r.service_id = s.id
            ORDER BY h.date_jour ASC, h.heure_debut ASC;
        """)
        appointments = cursor.fetchall()
        
    except Exception as e:
        print(f"Dashboard Error: {e}")
        appointments = []
        flash("Erreur lors du chargement des données.", "error")
    finally:
        cursor.close()
        conn.close()

    return render_template("admin/dashboard.html", appointments=appointments, role=role)

# --- CANCELLATION ROUTE ---
@app.route("/admin/cancel/<int:appt_id>", methods=["POST"])
def cancel_appointment(appt_id):
    if session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Accès refusé.", "error")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT r.horaire_id, r.client_nom, r.client_email, h.date_jour, h.heure_debut, c.alias, c.email as barber_email
            FROM rendezvous r
            JOIN horaires h ON r.horaire_id = h.id
            JOIN coiffeuses c ON r.coiffeuse_id = c.id
            WHERE r.id = %s;
        """, (appt_id,))
        details = cursor.fetchone()
        
        if details:
            horaire_id = details[0]
            cursor.execute("UPDATE horaires SET statut = 'Libre' WHERE id = %s;", (horaire_id,))
            cursor.execute("UPDATE rendezvous SET statut = 'Annule' WHERE id = %s;", (appt_id,))
            conn.commit()
            
            date_str = details[3].strftime('%d/%m/%Y')
            client_cancel = f"<h2>Rendez-vous Annulé</h2><p>Bonjour {details[1]}, votre rendez-vous du {date_str} a été annulé par l'administration. Si un dépôt a été payé, il vous sera remboursé sous peu.</p>"
            send_automated_email(details[2], "❌ Rendez-vous Annulé - Coiff'Connect", client_cancel, cc_admin=True)
            
            if details[6]:
                barber_cancel = f"<h2>Annulation de Rendez-vous</h2><p>Attention {details[5]}, le rendez-vous du {date_str} avec {details[1]} a été annulé. La plage horaire est de nouveau libre.</p>"
                send_automated_email(details[6], "Annulation de RDV - Coiff'Connect", barber_cancel, cc_admin=False)
            
            flash("Rendez-vous annulé. La plage horaire est de nouveau disponible.", "success")
        
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
    if session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Accès refusé. Vous n'avez pas l'autorisation.", "error")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE rendezvous SET statut = 'Confirme' WHERE id = %s;", (appt_id,))
        conn.commit()
        
        cursor.execute("""
            SELECT r.client_nom, r.client_email, h.date_jour, h.heure_debut, c.alias, c.email as barber_email
            FROM rendezvous r
            JOIN horaires h ON r.horaire_id = h.id
            JOIN coiffeuses c ON r.coiffeuse_id = c.id
            WHERE r.id = %s
        """, (appt_id,))
        details = cursor.fetchone()

        if details:
            date_str = details[2].strftime('%d/%m/%Y')
            time_str = details[3].strftime('%H:%M')
            
            client_html = f"<h2>Rendez-vous Confirmé !</h2><p>Bonjour {details[0]}, votre dépôt a été reçu.</p><p>Votre rendez-vous avec {details[4]} est confirmé pour le <strong>{date_str} à {time_str}</strong>.</p><p><em>Pour annuler, veuillez nous contacter au moins 24h à l'avance.</em></p>"
            send_automated_email(details[1], "✅ Rendez-vous Confirmé - Coiff'Connect", client_html, cc_admin=True)
            
            if details[5]:
                barber_html = f"<h2>Nouveau Rendez-vous !</h2><p>Le client {details[0]} a confirmé son rendez-vous avec vous pour le <strong>{date_str} à {time_str}</strong>.</p><p>Connectez-vous au portail pour voir les détails complets.</p>"
                send_automated_email(details[5], f"Nouveau RDV le {date_str} - Coiff'Connect", barber_html, cc_admin=False)
        
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
    if session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Accès refusé.", "error")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == "POST":
        alias = request.form.get("alias")
        telephone = request.form.get("telephone")
        email = request.form.get("email")
        pref = request.form.get("deplacement_pref")
        adresse_studio = request.form.get("adresse_studio", "")

        try:
            cursor.execute("""
                INSERT INTO coiffeuses (alias, telephone, email, deplacement_pref, adresse_studio)
                VALUES (%s, %s, %s, %s, %s)
            """, (alias, telephone, email, pref, adresse_studio))
            conn.commit()
            flash(f"L'opérateur {alias} a été ajouté avec succès !", "success")
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash("Ce nom d'affichage existe déjà.", "error")
        except Exception as e:
            conn.rollback()
            print(f"Error adding stylist: {e}")
            flash("Erreur système lors de l'ajout.", "error")
            
        return redirect(url_for('admin_manage'))

    try:
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
    if session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Accès refusé.", "error")
        return redirect(url_for('admin_dashboard'))

    alias = request.form.get("alias")
    telephone = request.form.get("telephone")
    email = request.form.get("email")
    pref = request.form.get("deplacement_pref")
    adresse_studio = request.form.get("adresse_studio", "")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE coiffeuses 
            SET alias = %s, telephone = %s, email = %s, deplacement_pref = %s, adresse_studio = %s
            WHERE id = %s
        """, (alias, telephone, email, pref, adresse_studio, stylist_id))
        conn.commit()
        flash("Le profil a été mis à jour avec succès !", "success")
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash("Erreur: Ce nom est déjà pris.", "error")
    except Exception as e:
        conn.rollback()
        print(f"Update Error: {e}")
        flash("Erreur lors de la mise à jour.", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_manage'))

@app.route("/admin/schedule", methods=["GET", "POST"])
def admin_schedule():
    if session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Accès refusé.", "error")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == "POST":
        coiffeuse_id = request.form.get("coiffeuse_id")
        date_jour = request.form.get("date_jour")
        heure_debut = request.form.get("heure_debut")
        heure_fin = request.form.get("heure_fin")
        duree_minutes = int(request.form.get("duree_minutes", 60))

        try:
            start_dt = datetime.strptime(f"{date_jour} {heure_debut}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{date_jour} {heure_fin}", "%Y-%m-%d %H:%M")
            
            slot_duration = timedelta(minutes=duree_minutes)
            current_time = start_dt
            slots_created = 0
            
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
            flash(f"Succès ! {slots_created} créneaux générés.", "success")

        except Exception as e:
            conn.rollback()
            print(f"Schedule Error: {e}")
            flash("Erreur lors de la génération.", "error")
            
        return redirect(url_for('admin_schedule'))

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
            cursor.execute("UPDATE horaires SET statut = 'Supprime' WHERE id = %s", (slot_id,))
            conn.commit()
            flash("Le créneau a été retiré.", "success")
        else:
            flash("Impossible de supprimer un créneau réservé.", "error")
    except Exception as e:
        conn.rollback()
        print(f"Delete Error: {e}")
        flash("Erreur lors de la suppression.", "error")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('admin_schedule'))

@app.route("/admin/catalog", methods=["GET", "POST"])
def admin_catalog():
    if session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Accès refusé.", "error")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == "POST":
        nom = request.form.get("nom")
        categorie_slug = request.form.get("categorie")
        description = request.form.get("description")
        
        image_url = ""
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_url = f"/{filepath}".replace("\\", "/")

        try:
            cursor.execute("""
                    INSERT INTO services (nom, description, categorie, image_url)
                    VALUES (%s, %s, %s, %s)
                """, (nom, description, categorie_slug, image_url))
            conn.commit()
            flash(f"Le service a été ajouté !", "success")
        except Exception as e:
            conn.rollback()
            print(f"Catalog Error: {e}")
            flash("Erreur lors de l'ajout.", "error")
            
        return redirect(url_for('admin_catalog'))

    try:
        cursor.execute("SELECT nom, slug FROM categories ORDER BY id;")
        categories = cursor.fetchall()
        cursor.execute("SELECT id, nom, categorie, description, image_url FROM services ORDER BY categorie, nom;")
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
            cursor.execute("""
                INSERT INTO coiffeuse_services (coiffeuse_id, service_id, prix)
                VALUES (%s, %s, %s)
                ON CONFLICT (coiffeuse_id, service_id) 
                DO UPDATE SET prix = EXCLUDED.prix;
            """, (coiffeuse_id, service_id, prix))
            conn.commit()
            flash("Compétence mise à jour !", "success")
        except Exception as e:
            conn.rollback()
            print(f"Assign Error: {e}")
            flash("Erreur lors de la mise à jour.", "error")
            
        return redirect(url_for('admin_assign_skills'))

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