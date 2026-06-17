--
-- PostgreSQL database dump
--

\restrict hPOTFLchMRPfQSDoF4vXw0BWCaVDEHGLyMgdGD7G0m6isVe3sEiIA26mLNSO0m3

-- Dumped from database version 18.4 (Ubuntu 18.4-0ubuntu0.26.04.1)
-- Dumped by pg_dump version 18.4 (Ubuntu 18.4-0ubuntu0.26.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: categories; Type: TABLE; Schema: public; Owner: ubuntu
--

CREATE TABLE public.categories (
    id integer NOT NULL,
    nom character varying(100) NOT NULL,
    description text,
    statut character varying(20) DEFAULT 'Locked'::character varying,
    slug character varying(50)
);


ALTER TABLE public.categories OWNER TO ubuntu;

--
-- Name: categories_id_seq; Type: SEQUENCE; Schema: public; Owner: ubuntu
--

CREATE SEQUENCE public.categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.categories_id_seq OWNER TO ubuntu;

--
-- Name: categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ubuntu
--

ALTER SEQUENCE public.categories_id_seq OWNED BY public.categories.id;


--
-- Name: coiffeuse_services; Type: TABLE; Schema: public; Owner: ubuntu
--

CREATE TABLE public.coiffeuse_services (
    coiffeuse_id integer NOT NULL,
    service_id integer NOT NULL,
    prix numeric(10,2)
);


ALTER TABLE public.coiffeuse_services OWNER TO ubuntu;

--
-- Name: coiffeuses; Type: TABLE; Schema: public; Owner: ubuntu
--

CREATE TABLE public.coiffeuses (
    id integer NOT NULL,
    alias character varying(50) NOT NULL,
    telephone character varying(20) NOT NULL,
    deplacement_pref character varying(20) DEFAULT 'Both'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    adresse_studio character varying(255),
    email character varying(255)
);


ALTER TABLE public.coiffeuses OWNER TO ubuntu;

--
-- Name: coiffeuses_id_seq; Type: SEQUENCE; Schema: public; Owner: ubuntu
--

CREATE SEQUENCE public.coiffeuses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.coiffeuses_id_seq OWNER TO ubuntu;

--
-- Name: coiffeuses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ubuntu
--

ALTER SEQUENCE public.coiffeuses_id_seq OWNED BY public.coiffeuses.id;


--
-- Name: horaires; Type: TABLE; Schema: public; Owner: ubuntu
--

CREATE TABLE public.horaires (
    id integer NOT NULL,
    coiffeuse_id integer,
    date_jour date NOT NULL,
    heure_debut time without time zone NOT NULL,
    heure_fin time without time zone NOT NULL,
    statut character varying(20) DEFAULT 'Libre'::character varying
);


ALTER TABLE public.horaires OWNER TO ubuntu;

--
-- Name: horaires_id_seq; Type: SEQUENCE; Schema: public; Owner: ubuntu
--

CREATE SEQUENCE public.horaires_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.horaires_id_seq OWNER TO ubuntu;

--
-- Name: horaires_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ubuntu
--

ALTER SEQUENCE public.horaires_id_seq OWNED BY public.horaires.id;


--
-- Name: portfolio_images; Type: TABLE; Schema: public; Owner: ubuntu
--

CREATE TABLE public.portfolio_images (
    id integer NOT NULL,
    coiffeuse_id integer,
    service_id integer,
    image_url character varying(255) NOT NULL,
    uploaded_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.portfolio_images OWNER TO ubuntu;

--
-- Name: portfolio_images_id_seq; Type: SEQUENCE; Schema: public; Owner: ubuntu
--

CREATE SEQUENCE public.portfolio_images_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.portfolio_images_id_seq OWNER TO ubuntu;

--
-- Name: portfolio_images_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ubuntu
--

ALTER SEQUENCE public.portfolio_images_id_seq OWNED BY public.portfolio_images.id;


--
-- Name: rendezvous; Type: TABLE; Schema: public; Owner: ubuntu
--

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


ALTER TABLE public.rendezvous OWNER TO ubuntu;

--
-- Name: rendezvous_id_seq; Type: SEQUENCE; Schema: public; Owner: ubuntu
--

CREATE SEQUENCE public.rendezvous_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.rendezvous_id_seq OWNER TO ubuntu;

--
-- Name: rendezvous_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ubuntu
--

ALTER SEQUENCE public.rendezvous_id_seq OWNED BY public.rendezvous.id;


--
-- Name: services; Type: TABLE; Schema: public; Owner: ubuntu
--

CREATE TABLE public.services (
    id integer NOT NULL,
    nom character varying(100) NOT NULL,
    categorie character varying(50),
    duree_est_minutes integer DEFAULT 60,
    image_url character varying(255),
    description text
);


ALTER TABLE public.services OWNER TO ubuntu;

--
-- Name: services_id_seq; Type: SEQUENCE; Schema: public; Owner: ubuntu
--

CREATE SEQUENCE public.services_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.services_id_seq OWNER TO ubuntu;

--
-- Name: services_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ubuntu
--

ALTER SEQUENCE public.services_id_seq OWNED BY public.services.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: ubuntu
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(120) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(50) NOT NULL,
    coiffeuse_id integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.users OWNER TO ubuntu;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: ubuntu
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO ubuntu;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ubuntu
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: utilisateurs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.utilisateurs (
    id integer NOT NULL,
    username character varying(50) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(20) DEFAULT 'Agent'::character varying
);


ALTER TABLE public.utilisateurs OWNER TO postgres;

--
-- Name: utilisateurs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.utilisateurs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.utilisateurs_id_seq OWNER TO postgres;

--
-- Name: utilisateurs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.utilisateurs_id_seq OWNED BY public.utilisateurs.id;


--
-- Name: categories id; Type: DEFAULT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.categories ALTER COLUMN id SET DEFAULT nextval('public.categories_id_seq'::regclass);


--
-- Name: coiffeuses id; Type: DEFAULT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.coiffeuses ALTER COLUMN id SET DEFAULT nextval('public.coiffeuses_id_seq'::regclass);


--
-- Name: horaires id; Type: DEFAULT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.horaires ALTER COLUMN id SET DEFAULT nextval('public.horaires_id_seq'::regclass);


--
-- Name: portfolio_images id; Type: DEFAULT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.portfolio_images ALTER COLUMN id SET DEFAULT nextval('public.portfolio_images_id_seq'::regclass);


--
-- Name: rendezvous id; Type: DEFAULT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.rendezvous ALTER COLUMN id SET DEFAULT nextval('public.rendezvous_id_seq'::regclass);


--
-- Name: services id; Type: DEFAULT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.services ALTER COLUMN id SET DEFAULT nextval('public.services_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: utilisateurs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.utilisateurs ALTER COLUMN id SET DEFAULT nextval('public.utilisateurs_id_seq'::regclass);


--
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);


--
-- Name: coiffeuse_services coiffeuse_services_pkey; Type: CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.coiffeuse_services
    ADD CONSTRAINT coiffeuse_services_pkey PRIMARY KEY (coiffeuse_id, service_id);


--
-- Name: coiffeuses coiffeuses_alias_key; Type: CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.coiffeuses
    ADD CONSTRAINT coiffeuses_alias_key UNIQUE (alias);


--
-- Name: coiffeuses coiffeuses_pkey; Type: CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.coiffeuses
    ADD CONSTRAINT coiffeuses_pkey PRIMARY KEY (id);


--
-- Name: horaires horaires_pkey; Type: CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.horaires
    ADD CONSTRAINT horaires_pkey PRIMARY KEY (id);


--
-- Name: portfolio_images portfolio_images_pkey; Type: CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.portfolio_images
    ADD CONSTRAINT portfolio_images_pkey PRIMARY KEY (id);


--
-- Name: rendezvous rendezvous_pkey; Type: CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.rendezvous
    ADD CONSTRAINT rendezvous_pkey PRIMARY KEY (id);


--
-- Name: services services_pkey; Type: CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.services
    ADD CONSTRAINT services_pkey PRIMARY KEY (id);


--
-- Name: coiffeuse_services unique_coiffeuse_service; Type: CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.coiffeuse_services
    ADD CONSTRAINT unique_coiffeuse_service UNIQUE (coiffeuse_id, service_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: utilisateurs utilisateurs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.utilisateurs
    ADD CONSTRAINT utilisateurs_pkey PRIMARY KEY (id);


--
-- Name: utilisateurs utilisateurs_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.utilisateurs
    ADD CONSTRAINT utilisateurs_username_key UNIQUE (username);


--
-- Name: coiffeuse_services coiffeuse_services_coiffeuse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.coiffeuse_services
    ADD CONSTRAINT coiffeuse_services_coiffeuse_id_fkey FOREIGN KEY (coiffeuse_id) REFERENCES public.coiffeuses(id) ON DELETE CASCADE;


--
-- Name: coiffeuse_services coiffeuse_services_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.coiffeuse_services
    ADD CONSTRAINT coiffeuse_services_service_id_fkey FOREIGN KEY (service_id) REFERENCES public.services(id) ON DELETE CASCADE;


--
-- Name: horaires horaires_coiffeuse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.horaires
    ADD CONSTRAINT horaires_coiffeuse_id_fkey FOREIGN KEY (coiffeuse_id) REFERENCES public.coiffeuses(id) ON DELETE CASCADE;


--
-- Name: portfolio_images portfolio_images_coiffeuse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.portfolio_images
    ADD CONSTRAINT portfolio_images_coiffeuse_id_fkey FOREIGN KEY (coiffeuse_id) REFERENCES public.coiffeuses(id) ON DELETE CASCADE;


--
-- Name: portfolio_images portfolio_images_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.portfolio_images
    ADD CONSTRAINT portfolio_images_service_id_fkey FOREIGN KEY (service_id) REFERENCES public.services(id) ON DELETE CASCADE;


--
-- Name: rendezvous rendezvous_coiffeuse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.rendezvous
    ADD CONSTRAINT rendezvous_coiffeuse_id_fkey FOREIGN KEY (coiffeuse_id) REFERENCES public.coiffeuses(id);


--
-- Name: rendezvous rendezvous_horaire_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.rendezvous
    ADD CONSTRAINT rendezvous_horaire_id_fkey FOREIGN KEY (horaire_id) REFERENCES public.horaires(id);


--
-- Name: rendezvous rendezvous_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.rendezvous
    ADD CONSTRAINT rendezvous_service_id_fkey FOREIGN KEY (service_id) REFERENCES public.services(id);


--
-- Name: users users_coiffeuse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_coiffeuse_id_fkey FOREIGN KEY (coiffeuse_id) REFERENCES public.coiffeuses(id) ON DELETE SET NULL;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO ubuntu;


--
-- Name: TABLE utilisateurs; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.utilisateurs TO ubuntu;


--
-- Name: SEQUENCE utilisateurs_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.utilisateurs_id_seq TO ubuntu;


--
-- PostgreSQL database dump complete
--

\unrestrict hPOTFLchMRPfQSDoF4vXw0BWCaVDEHGLyMgdGD7G0m6isVe3sEiIA26mLNSO0m3

