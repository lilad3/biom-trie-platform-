# biometric-platform

Plateforme biométrique indépendante (empreintes digitales) utilisable par
n'importe quelle application web, quel que soit son langage : un service
central (`biometric-api`, FastAPI) + des SDK clients (Python, JavaScript, PHP,
Java) + un SDK frontend pour la capture dans le navigateur.

## Contenu du dépôt

| Dossier           | Rôle                                                         |
|-------------------|--------------------------------------------------------------|
| `biometric-core/` | Extraction, matching et stockage chiffré des empreintes      |
| `biometric-api/`  | API REST signée HMAC (`/enroll`, `/identify`, `/verify`...)  |
| `client-sdk/`     | SDK serveur pour appeler l'API depuis votre backend          |
| `frontend-sdk/`   | SDK navigateur (lecteur DigitalPersona + appels au backend)  |
| `tests/`          | Tests Python                                                 |
| `docs/`           | Documentation complète                                       |

## Démarrage rapide (Docker)

```bash
cp .env.example .env      # puis remplir SERVICE_AUTH_TOKEN et BIOMETRIC_ENCRYPTION_KEY
docker compose up -d --build
curl http://localhost:8001/health
```

Documentation interactive de l'API : http://localhost:8001/docs

## Documentation

Toute la documentation (installation, intégration, protocole de sécurité,
référence de l'API) est dans **[docs/README.md](docs/README.md)**.

> Le SDK frontend dépend de fichiers DigitalPersona non inclus dans ce dépôt :
> voir [frontend-sdk/vendor/README.md](frontend-sdk/vendor/README.md).

## Licence

[MIT](LICENSE)
