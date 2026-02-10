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
