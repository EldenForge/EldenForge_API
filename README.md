# Elden Forge API

API REST pour accéder aux données du jeu Elden Ring.

## Installation

```bash
pip install -r requirements.txt
```

## Lancer l'API

```bash
uvicorn main:app --reload
```

## Liens

| Ressource | URL |
|-----------|-----|
| API | http://127.0.0.1:8000 |
| Documentation Swagger | http://127.0.0.1:8000/docs |
| Documentation ReDoc | http://127.0.0.1:8000/redoc |

## Endpoints disponibles

| Endpoint | Description |
|----------|-------------|
| `/ammos` | Munitions (flèches, carreaux) |
| `/armors` | Armures |
| `/ashes` | Cendres de guerre |
| `/bosses` | Boss |
| `/classes` | Classes de personnage |
| `/creatures` | Créatures |
| `/incantations` | Incantations |
| `/items` | Objets |
| `/locations` | Lieux |
| `/npcs` | PNJs |
| `/shields` | Boucliers |
| `/sorceries` | Sorcelleries |
| `/spirits` | Esprits |
| `/talismans` | Talismans |
| `/weapons` | Armes |

## Utilisation

### Récupérer un élément par ID

```
GET /{endpoint}/{id}
```

Exemple :
```
GET /weapons/17f69448ceel0i0a57bokoqz409yb
```

### Lister avec filtres

```
GET /{endpoint}?param1=valeur1&param2=valeur2
```

Exemples :
```
GET /bosses?region=Limgrave
GET /weapons?name=Moonveil
GET /armors?category=Helm
```

## Dataset

Données provenant du dataset [Elden Ring Ultimate Dataset](https://www.kaggle.com/datasets/robikscube/elden-ring-ultimate-dataset) sur Kaggle.

## Base de données

### Pré-requis

- Compte Neon ([neon.tech](https://neon.tech)) avec un projet créé
- Variables d'env : copier `.env.example` en `.env` et y coller la connection string Neon (format asyncpg avec `?ssl=require`)

### Migrations Alembic

~~~bash
alembic upgrade head             # appliquer toutes les migrations
alembic downgrade -1             # revenir d'un cran
alembic revision -m "msg"        # nouvelle migration manuelle
alembic revision --autogenerate -m "msg"   # depuis les modèles
~~~

### Lancer les tests

~~~bash
pytest tests/ -v
~~~

Les tests utilisent la database `eldenforge_test` (créée manuellement dans le projet Neon) et un schéma monté via `Base.metadata.create_all` (pas Alembic) pour rapidité. Chaque test tourne dans une transaction rollback → isolation totale.

## Authentification (PR2a)

Endpoints disponibles :
- `POST /auth/register` — créer un compte (email, pseudo, password) → envoie un email de vérification
- `POST /auth/login` — connexion (email, password) → set cookies httpOnly access+refresh
- `GET /auth/me` — récupère l'utilisateur courant (cookie requis)

Mots de passe hashés via Argon2id. JWT signés HS256 (variable `JWT_SECRET` en .env).

Provider email :
- `EMAIL_PROVIDER=console` (défaut) — emails loggés au stdout, parfait pour dev
- `EMAIL_PROVIDER=resend` — envoie via [Resend](https://resend.com) (nécessite `RESEND_API_KEY`)

### Endpoints PR2b (verify + reset password)

- `GET /auth/verify?token=<raw>` — active le compte d'un user (200 si OK, 404 si token inconnu, 410 si expiré/déjà utilisé)
- `POST /auth/forgot {email}` — déclenche l'envoi d'un email de reset (toujours 202, même si l'email est inconnu — anti enum)
- `POST /auth/reset {token, new_password}` — change le password (200 si OK, 404/410 sur token, 422 si password faible)

### Endpoints PR2c (refresh + logout + protections)

- `POST /auth/refresh` — rotation des cookies access+refresh (200 si OK, 401 si invalid). L'ancien refresh est révoqué en BDD.
- `POST /auth/logout` — 204 + cookies cleared + refresh révoqué en BDD. Idempotent.
- `POST /auth/login` est rate-limité à **10 tentatives/minute par IP** (slowapi) → 429 au-delà.
- Lockout : après **5 échecs consécutifs** sur un compte, le compte est verrouillé **15 min** (423 Locked). Reset à 0 sur login réussi.

## Builds & Profil utilisateur (PR3)

Tous les endpoints ci-dessous nécessitent un cookie d'authentification valide.

### Builds (CRUD)

- `POST /builds` — créer un build (`name`, `description?`, `data` JSONB, `is_public?`)
- `GET /builds?limit=&offset=` — liste paginée de mes builds (limit 1..100, défaut 20)
- `GET /builds/{id}` — récupérer un build (le mien OU public d'un autre user, sinon 404)
- `PUT /builds/{id}` — modifier (PATCH semantics : seuls les champs présents sont updatés)
- `DELETE /builds/{id}` — supprimer

403 si on tente de modifier/supprimer le build d'un autre user.

### Profil

- `GET /users/me` — récupère l'utilisateur courant (alias de `/auth/me`)
- `PATCH /users/me` — changer le pseudo (`{pseudo}`) — 409 si pris
- `POST /users/me/password` — changer le password (`{current_password, new_password}`) — 401 si current faux
