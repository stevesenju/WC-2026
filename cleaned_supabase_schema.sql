-- Cleaned PostgreSQL database dump for Supabase

CREATE TABLE public.categories (
    id integer NOT NULL,
    nom character varying(100) NOT NULL,
    description text,
    statut character varying(20) DEFAULT 'Locked'::character varying,
    slug character varying(50)
);

CREATE SEQUENCE public.categories_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.categories_id_seq OWNED BY public.categories.id;

CREATE TABLE public.coiffeuse_services (
    coiffeuse_id integer NOT NULL,
    service_id integer NOT NULL,
    prix numeric(10,2)
);

CREATE TABLE public.coiffeuses (
    id integer NOT NULL,
    alias character varying(50) NOT NULL,
    telephone character varying(20) NOT NULL,
    deplacement_pref character varying(20) DEFAULT 'Both'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    adresse_studio character varying(255),
    email character varying(255)
);

CREATE SEQUENCE public.coiffeuses_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.coiffeuses_id_seq OWNED BY public.coiffeuses.id;

CREATE TABLE public.horaires (
    id integer NOT NULL,
    coiffeuse_id integer,
    date_jour date NOT NULL,
    heure_debut time without time zone NOT NULL,
    heure_fin time without time zone NOT NULL,
    statut character varying(20) DEFAULT 'Libre'::character varying
);

CREATE SEQUENCE public.horaires_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.horaires_id_seq OWNED BY public.horaires.id;

CREATE TABLE public.portfolio_images (
    id integer NOT NULL,
    coiffeuse_id integer,
    service_id integer,
    image_url character varying(255) NOT NULL,
    uploaded_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE SEQUENCE public.portfolio_images_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.portfolio_images_id_seq OWNED BY public.portfolio_images.id;

CREATE TABLE public.rendezvous (
    id integer NOT NULL,
    client_nom character varying(100) NOT NULL,
    client_email character varying(120) NOT NULL,
    client_telephone character varying(20) NOT NULL,
    client_adresse text,
    coiffeuse_id integer,
    service_id integer,
    horaire_id integer,
    transport_req boolean DEFAULT false,
    prix_total numeric(10,2) NOT NULL,
    statut character varying(20) DEFAULT 'En_Attente'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    adresse_client text,
    code_interac character varying(15)
);

CREATE SEQUENCE public.rendezvous_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.rendezvous_id_seq OWNED BY public.rendezvous.id;

CREATE TABLE public.services (
    id integer NOT NULL,
    nom character varying(100) NOT NULL,
    categorie character varying(50),
    duree_est_minutes integer DEFAULT 60,
    image_url character varying(255),
    description text
);

CREATE SEQUENCE public.services_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.services_id_seq OWNED BY public.services.id;

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(120) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(50) NOT NULL,
    coiffeuse_id integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE SEQUENCE public.users_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;

CREATE TABLE public.utilisateurs (
    id integer NOT NULL,
    username character varying(50) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(20) DEFAULT 'Agent'::character varying
);

CREATE SEQUENCE public.utilisateurs_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.utilisateurs_id_seq OWNED BY public.utilisateurs.id;


-- Assign Default Values from Sequences
ALTER TABLE ONLY public.categories ALTER COLUMN id SET DEFAULT nextval('public.categories_id_seq'::regclass);
ALTER TABLE ONLY public.coiffeuses ALTER COLUMN id SET DEFAULT nextval('public.coiffeuses_id_seq'::regclass);
ALTER TABLE ONLY public.horaires ALTER COLUMN id SET DEFAULT nextval('public.horaires_id_seq'::regclass);
ALTER TABLE ONLY public.portfolio_images ALTER COLUMN id SET DEFAULT nextval('public.portfolio_images_id_seq'::regclass);
ALTER TABLE ONLY public.rendezvous ALTER COLUMN id SET DEFAULT nextval('public.rendezvous_id_seq'::regclass);
ALTER TABLE ONLY public.services ALTER COLUMN id SET DEFAULT nextval('public.services_id_seq'::regclass);
ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);
ALTER TABLE ONLY public.utilisateurs ALTER COLUMN id SET DEFAULT nextval('public.utilisateurs_id_seq'::regclass);


-- Create Primary Keys and Unique Constraints
ALTER TABLE ONLY public.categories ADD CONSTRAINT categories_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.coiffeuse_services ADD CONSTRAINT coiffeuse_services_pkey PRIMARY KEY (coiffeuse_id, service_id);
ALTER TABLE ONLY public.coiffeuses ADD CONSTRAINT coiffeuses_alias_key UNIQUE (alias);
ALTER TABLE ONLY public.coiffeuses ADD CONSTRAINT coiffeuses_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.horaires ADD CONSTRAINT horaires_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.portfolio_images ADD CONSTRAINT portfolio_images_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.rendezvous ADD CONSTRAINT rendezvous_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.services ADD CONSTRAINT services_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.coiffeuse_services ADD CONSTRAINT unique_coiffeuse_service UNIQUE (coiffeuse_id, service_id);
ALTER TABLE ONLY public.users ADD CONSTRAINT users_email_key UNIQUE (email);
ALTER TABLE ONLY public.users ADD CONSTRAINT users_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.utilisateurs ADD CONSTRAINT utilisateurs_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.utilisateurs ADD CONSTRAINT utilisateurs_username_key UNIQUE (username);

-- Create Foreign Keys
ALTER TABLE ONLY public.coiffeuse_services ADD CONSTRAINT coiffeuse_services_coiffeuse_id_fkey FOREIGN KEY (coiffeuse_id) REFERENCES public.coiffeuses(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.coiffeuse_services ADD CONSTRAINT coiffeuse_services_service_id_fkey FOREIGN KEY (service_id) REFERENCES public.services(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.horaires ADD CONSTRAINT horaires_coiffeuse_id_fkey FOREIGN KEY (coiffeuse_id) REFERENCES public.coiffeuses(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.portfolio_images ADD CONSTRAINT portfolio_images_coiffeuse_id_fkey FOREIGN KEY (coiffeuse_id) REFERENCES public.coiffeuses(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.portfolio_images ADD CONSTRAINT portfolio_images_service_id_fkey FOREIGN KEY (service_id) REFERENCES public.services(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.rendezvous ADD CONSTRAINT rendezvous_coiffeuse_id_fkey FOREIGN KEY (coiffeuse_id) REFERENCES public.coiffeuses(id);
ALTER TABLE ONLY public.rendezvous ADD CONSTRAINT rendezvous_horaire_id_fkey FOREIGN KEY (horaire_id) REFERENCES public.horaires(id);
ALTER TABLE ONLY public.rendezvous ADD CONSTRAINT rendezvous_service_id_fkey FOREIGN KEY (service_id) REFERENCES public.services(id);
ALTER TABLE ONLY public.users ADD CONSTRAINT users_coiffeuse_id_fkey FOREIGN KEY (coiffeuse_id) REFERENCES public.coiffeuses(id) ON DELETE SET NULL;