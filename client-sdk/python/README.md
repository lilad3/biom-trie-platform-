# biometric-client (Python)

SDK officiel Python pour `biometric-api`. Le développeur n'écrit jamais de
`requests.post()` manuel, ne calcule jamais de signature HMAC, ne construit
jamais d'URL : il utilise directement les méthodes du client.

## Installation

```bash
pip install -e ./client-sdk/python
```

## Usage

```python
from biometric_client import BiometricClient

client = BiometricClient(
    base_url="http://localhost:8001",
    service_auth_token="le-meme-token-que-SERVICE_AUTH_TOKEN-cote-biometric-api",
)

# Enrôlement
result = client.enroll("EMP001", "right_index", image_base64)
print(result.success, result.message)

# Identification 1:N
result = client.identify(image_base64)
if result.success:
    print(f"Employé identifié : {result.employee_id} (score={result.score})")

# Vérification 1:1
result = client.verify("EMP001", image_base64)
print(result.match)

# Suppression
result = client.delete("EMP001")
```

Utilisable aussi comme context manager pour fermer proprement la session HTTP :

```python
with BiometricClient(base_url=..., service_auth_token=...) as client:
    result = client.identify(image_base64)
```

## Gestion des erreurs

Toutes les erreurs sont traduites en exceptions du SDK, jamais en exceptions
`requests` brutes :

```python
from biometric_client import BiometricClient, NetworkError, ServerError, TimeoutError_

try:
    result = client.identify(image_base64)
except TimeoutError_:
    ...  # le serveur biométrique n'a pas répondu à temps
except NetworkError:
    ...  # impossible de contacter le serveur
except ServerError as exc:
    ...  # le serveur a répondu une erreur HTTP (exc.status_code, exc.message)
```

## ⚠️ Sécurité

Ce client porte `service_auth_token`, un secret serveur. Il est fait pour
être utilisé **côté serveur** (dans une vue Django, une route Flask, un
worker...), jamais dans du code exécuté côté navigateur. Pour le frontend,
voir `frontend-sdk/` (`BiometricScanner` + `BiometricClient` JavaScript),
qui parle à un endpoint proxy de votre application, pas directement à
`biometric-api`.

## Tests

```bash
pip install -e ".[test]"
pytest
```
