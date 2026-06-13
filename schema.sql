-- 1. Table des Administrateurs (Your team of 5)
CREATE TABLE utilisateurs (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'Agent' -- 'SuperAdmin' ou 'Agent'
);

-- 2. Table des Services (The Hairstyles)
CREATE TABLE services (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    categorie VARCHAR(50),
    prix_base DECIMAL(10, 2) NOT NULL,
    duree_est_minutes INTEGER DEFAULT 60,
    image_url VARCHAR(255) -- Image de couverture pour la page d'accueil
);

-- 3. Table des Coiffeuses (Internal Profiles - Hidden from public)
CREATE TABLE coiffeuses (
    id SERIAL PRIMARY KEY,
    alias VARCHAR(50) UNIQUE NOT NULL, -- ex: "Styliste A", "Pro 12"
    telephone VARCHAR(20) NOT NULL,
    deplacement_pref VARCHAR(20) DEFAULT 'Both', -- 'Domicile', 'Studio', 'Both'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Table de Mapping (Who can do what)
CREATE TABLE coiffeuse_services (
    coiffeuse_id INTEGER REFERENCES coiffeuses(id) ON DELETE CASCADE,
    service_id INTEGER REFERENCES services(id) ON DELETE CASCADE,
    PRIMARY KEY (coiffeuse_id, service_id)
);

-- 5. Table des Portfolios (Dynamic Image Carousels)
CREATE TABLE portfolio_images (
    id SERIAL PRIMARY KEY,
    coiffeuse_id INTEGER REFERENCES coiffeuses(id) ON DELETE CASCADE,
    service_id INTEGER REFERENCES services(id) ON DELETE CASCADE,
    image_url VARCHAR(255) NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Table des Horaires (The Engine for the Dynamic Calendar)
CREATE TABLE horaires (
    id SERIAL PRIMARY KEY,
    coiffeuse_id INTEGER REFERENCES coiffeuses(id) ON DELETE CASCADE,
    date_jour DATE NOT NULL,
    heure_debut TIME NOT NULL,
    heure_fin TIME NOT NULL,
    statut VARCHAR(20) DEFAULT 'Libre' -- 'Libre', 'Reserve'
);

-- 7. Table des Rendez-vous (The Core Transactions)
CREATE TABLE rendezvous (
    id SERIAL PRIMARY KEY,
    client_nom VARCHAR(100) NOT NULL,
    client_email VARCHAR(120) NOT NULL,
    client_telephone VARCHAR(20) NOT NULL,
    client_adresse TEXT, -- Null si au studio
    coiffeuse_id INTEGER REFERENCES coiffeuses(id),
    service_id INTEGER REFERENCES services(id),
    horaire_id INTEGER REFERENCES horaires(id),
    transport_req BOOLEAN DEFAULT FALSE,
    prix_total DECIMAL(10, 2) NOT NULL,
    statut VARCHAR(20) DEFAULT 'En_Attente', -- 'En_Attente', 'Confirme', 'Annule'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- Crucial for the 1-hour auto-cancel!
);