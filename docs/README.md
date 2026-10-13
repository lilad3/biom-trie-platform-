# biometric-platform — Documentation complète

Plateforme biométrique indépendante (empreintes digitales) utilisable par
**n'importe quelle application web**, quel que soit son langage ou son
framework — comparable dans son principe à Stripe (paiement) ou Auth0
(authentification) : un service central + des SDK clients + un SDK
frontend, le tout communiquant en HTTP/JSON.

---

## Table des matières

1. [Comment ça marche (vue d'ensemble)](#1-comment-ça-marche-vue-densemble)
2. [Les briques de la plateforme](#2-les-briques-de-la-plateforme)
3. [Démarrer le serveur biométrique](#3-démarrer-le-serveur-biométrique)
4. [Intégrer la plateforme dans votre application (n'importe quel langage)](#4-intégrer-la-plateforme-dans-votre-application-nimporte-quel-langage)
5. [Intégrer le frontend (capture d'empreinte dans le navigateur)](#5-intégrer-le-frontend-capture-dempreinte-dans-le-navigateur)
6. [Le protocole de sécurité en détail](#6-le-protocole-de-sécurité-en-détail)
7. [Référence de l'API REST](#7-référence-de-lapi-rest)
8. [Bonnes pratiques et erreurs à éviter](#8-bonnes-pratiques-et-erreurs-à-éviter)
9. [Où trouver quoi dans le dépôt](#9-où-trouver-quoi-dans-le-dépôt)

---

## 1. Comment ça marche (vue d'ensemble)

La plateforme sépare strictement trois responsabilités :

```
┌──────────────────────┐        ┌───────────────────────┐        ┌─────────────────────┐
│   Votre application   │        │   biometric-api        │        │   biometric-core     │
│  (Django, Laravel,    │  HTTP  │   (FastAPI)             │  appel │   (Python pur)       │
│   Node, Spring...)    │ signé  │                         │ direct │                      │
│                        │──────▶│  /enroll  /identify     │───────▶│  Extraction SIFT      │
│  - Utilisateurs, JWT   │  HMAC │  /verify  /delete        │        │  Matching FLANN       │
│  - Rôles, permissions  │        │  /health                │        │  Chiffrement AES-GCM  │
│  - Pointages, RH       │        │                         │        │  Stockage chiffré     │
│  - Rapports, logs      │        │  Audit log (qui/quand)   │        │                      │
└──────────────────────┘        └───────────────────────┘        └─────────────────────┘
        ▲
        │ HTTP (proxy)
        │
┌──────────────────────┐
│   Navigateur           │
│  frontend-sdk          │
│  - BiometricScanner     │  ← parle au lecteur USB (DigitalPersona)
│  - BiometricClient      │  ← parle à VOTRE application, jamais à biometric-api
└──────────────────────┘
```

**Le principe clé : `biometric-api` ne sait rien de votre métier.** Il ne
connaît ni utilisateurs, ni rôles, ni JWT, ni pointages. Il fait une seule
chose : recevoir une image d'empreinte, l'identifier ou la vérifier, et
répondre. Toute la logique métier (qui a le droit de faire quoi, qu'est-ce
qu'on fait du résultat) reste dans **votre** application.

Cette séparation permet à `biometric-api` d'être branché sur Django,
Laravel, Express, Spring Boot, ASP.NET ou n'importe quel autre framework
sans jamais avoir à changer une ligne de son propre code.

---

## 2. Les briques de la plateforme

| Brique | Rôle | Où |
|---|---|---|
| **biometric-core** | Cœur biométrique pur (extraction, matching, chiffrement, stockage). Aucune dépendance HTTP. | `biometric-core/` |
| **biometric-api** | API REST FastAPI qui expose biometric-core en HTTP. C'est LE serveur central de la plateforme. | `biometric-api/` |
| **frontend-sdk** | SDK JavaScript navigateur : capture l'empreinte sur le lecteur USB, l'envoie à votre backend. | `frontend-sdk/` |
| **client-sdk/python** | SDK serveur Python pour appeler biometric-api depuis Django/Flask/FastAPI. | `client-sdk/python/` |
| **client-sdk/javascript** | SDK serveur Node.js pour appeler biometric-api depuis Express/NestJS. | `client-sdk/javascript/` |
| **client-sdk/php** | SDK serveur PHP pour appeler biometric-api depuis Laravel/Symfony. | `client-sdk/php/` |
| **client-sdk/java** | SDK serveur Java pour appeler biometric-api depuis Spring Boot. | `client-sdk/java/` |

Vous n'installez que ce dont vous avez besoin : le serveur `biometric-api`
(toujours nécessaire) + le SDK correspondant au langage de votre backend +
le `frontend-sdk` si vous capturez des empreintes dans un navigateur.

---

## 3. Démarrer le serveur biométrique

`biometric-api` est le seul composant qui doit tourner en permanence,
généralement comme un service interne (pas exposé directement à Internet).

```bash
# 1. Installer le cœur biométrique
pip install -e ./biometric-core

# 2. Installer l'API
pip install -r biometric-api/requirements.txt

# 3. Configurer
cp biometric-api/.env.example .env
# Éditer .env : générer BIOMETRIC_ENCRYPTION_KEY et SERVICE_AUTH_TOKEN
# (les commandes à lancer sont indiquées en commentaire dans le fichier)

# 4. Lancer
uvicorn app.main:app --app-dir biometric-api --host 0.0.0.0 --port 8001
```

Vérifiez que ça tourne :

```bash
curl http://localhost:8001/health
# {"status":"ok","enrolled_employees":0,"service":"biometric-api"}
```

La documentation interactive Swagger est disponible sur `http://localhost:8001/docs`.

---

## 4. Intégrer la plateforme dans votre application (n'importe quel langage)

Peu importe le framework de votre application, le principe est **toujours
le même en 3 étapes**.

### Étape 1 — Votre backend appelle biometric-api via le SDK de son langage

Exemple en Python (Django, Flask...) :

```python
from biometric_client import BiometricClient

client = BiometricClient(
    base_url="http://localhost:8001",
    service_auth_token=os.environ["BIOMETRIC_SERVICE_TOKEN"],
)

result = client.identify(image_base64)
if result.success:
    employee = Employee.objects.get(id=result.employee_id)
```

Exemple en Node.js (Express, NestJS...) :

```js
const { BiometricClient } = require("biometric-client");

const client = new BiometricClient({
  baseUrl: "http://localhost:8001",
  serviceAuthToken: process.env.BIOMETRIC_SERVICE_TOKEN,
});

const result = await client.identify(imageBase64);
if (result.success) {
  const employee = await Employee.findById(result.employeeId);
}
```

Exemple en PHP (Laravel, Symfony...) :

```php
use BiometricClient\BiometricClient;

$client = new BiometricClient('http://localhost:8001', getenv('BIOMETRIC_SERVICE_TOKEN'));

$result = $client->identify($imageBase64);
if ($result['success']) {
    $employee = Employee::find($result['employeeId']);
}
```

Exemple en Java (Spring Boot...) :

```java
BiometricClient client = new BiometricClient(
    "http://localhost:8001",
    System.getenv("BIOMETRIC_SERVICE_TOKEN")
);

Results.IdentifyResult result = client.identify(imageBase64);
if (result.success()) {
    Employee employee = employeeRepository.findById(result.employeeId());
}
```

**Chaque SDK calcule automatiquement la signature HMAC requise** — vous
n'avez jamais à le faire vous-même.

Pas de SDK pour votre langage ? Le protocole est un simple HTTP+JSON signé
HMAC (voir [section 6](#6-le-protocole-de-sécurité-en-détail)) : vous
pouvez appeler `biometric-api` avec n'importe quel client HTTP en
recalculant la signature vous-même.

### Étape 2 — Votre backend applique VOTRE logique métier

`biometric-api` ne fait qu'identifier une empreinte : c'est votre
application qui décide ce que ça signifie (badger un pointage, autoriser un
accès, refuser si l'employé est suspendu, etc.).

```python
result = client.identify(image_base64)

if not result.success:
    return JsonResponse({"error": "Empreinte non reconnue"}, status=401)

employee = Employee.objects.get(id=result.employee_id)
if not employee.is_active:
    return JsonResponse({"error": "Employé inactif"}, status=403)

Pointage.objects.create(employee=employee, timestamp=now())
```

### Étape 3 — Exposez un endpoint proxy pour le frontend

Si vous capturez les empreintes dans un navigateur, votre backend doit
exposer une route (ex: `/api/biometrie/identify`) qui reçoit l'image du
frontend, authentifie l'utilisateur normalement (session, JWT...), puis
relaie vers `biometric-api` via le SDK serveur. C'est ce proxy que le
`frontend-sdk` appellera — jamais `biometric-api` directement.

```python
# Django, à titre d'exemple — le principe est identique dans tout framework
@login_required
def identify_view(request):
    body = json.loads(request.body)
    result = client.identify(body["image"])
    return JsonResponse({
        "success": result.success,
        "employeeId": result.employee_id,
        "score": result.score,
        "message": result.message,
    })
```

---

## 5. Intégrer le frontend (capture d'empreinte dans le navigateur)

> Les deux fichiers `vendor/` (SDK DigitalPersona) ne sont pas fournis dans le dépôt :
> voir [vendor/README.md](../frontend-sdk/vendor/README.md) pour les télécharger.

```html
<script src="vendor/fingerprint.sdk.min.js"></script>
<script src="vendor/websdk.client.min.js"></script>
<script src="dist/biometric-sdk.js"></script>

<script>
  const scanner = new BiometricScanner();
  const client = new BiometricClient({ baseUrl: "/api/biometrie" }); // votre proxy, JAMAIS biometric-api directement

  await scanner.connect();
  const capture = await scanner.capture({
    onQuality: (q) => console.log(`Qualité : ${q.percent}%`),
  });

  if (capture.isAcceptable) {
    const result = await client.identify(capture.image);
  }
</script>
```

`BiometricScanner` encapsule totalement le lecteur DigitalPersona : vous ne
manipulez jamais `Fingerprint.WebApi` ni ses événements bas niveau.

**Règle non négociable** : `BiometricClient` (version navigateur) ne
contacte jamais `biometric-api` directement, car ça exigerait d'exposer
`SERVICE_AUTH_TOKEN` dans du code JavaScript public — un secret serveur ne
doit jamais quitter le serveur. Il appelle toujours un endpoint de **votre**
application, qui relaie via le SDK serveur (étape 3 ci-dessus).

---

## 6. Le protocole de sécurité en détail

Toutes les routes sensibles (`/enroll`, `/identify`, `/verify`, `/delete`)
exigent deux headers, calculés à partir d'un secret partagé
(`SERVICE_AUTH_TOKEN`) connu uniquement du serveur `biometric-api` et de
votre backend :

```
X-Timestamp: <epoch_seconds>
X-Signature: hex(HMAC_SHA256(SERVICE_AUTH_TOKEN, "{timestamp}.{corps_brut_de_la_requête}"))
```

- **`X-Timestamp`** doit être proche de l'heure actuelle (tolérance
  configurable, 30 secondes par défaut) : ça empêche un attaquant de
  rejouer une requête interceptée plus tard.
- **`X-Signature`** garantit que la requête vient bien d'un service qui
  connaît le secret, et que le corps n'a pas été altéré en chemin.

Ce mécanisme est une authentification **service-à-service**, pas une
authentification utilisateur : `biometric-api` ne voit jamais le JWT ou la
session de l'utilisateur final — c'est votre application qui vérifie ça
avant même d'appeler le SDK.

`/health` est la seule route publique, sans signature requise (simple
sonde de disponibilité).

---

## 7. Référence de l'API REST

| Route | Méthode | Signature requise | Description |
|---|---|---|---|
| `/health` | GET | Non | Sonde de disponibilité, nombre d'employés enrôlés. |
| `/enroll` | POST | Oui | Enregistre une empreinte pour un employé (`employeeId`, `fingerType`, `image`). |
| `/identify` | POST | Oui | Identification 1:N — trouve l'employé correspondant à une image parmi tous les enrôlés. |
| `/verify` | POST | Oui | Vérification 1:1 — confirme qu'une image correspond à un `employeeId` donné. |
| `/delete` | POST | Oui | Supprime définitivement toutes les empreintes d'un employé. |

Toutes les images sont envoyées en base64. Toutes les réponses sont en
JSON. Documentation interactive complète (schémas de requête/réponse) sur
`/docs` une fois le serveur lancé.

**Chaque appel à une route sensible est journalisé** dans l'audit log de
`biometric-api` (qui, quand, succès ou échec, depuis quelle IP) — jamais
avec l'image ou les données biométriques elles-mêmes.

---

## 8. Bonnes pratiques et erreurs à éviter

- ❌ **Ne jamais** appeler `biometric-api` directement depuis le navigateur.
  Toujours passer par un proxy de votre backend.
- ❌ **Ne jamais** committer `SERVICE_AUTH_TOKEN` ou `BIOMETRIC_ENCRYPTION_KEY`
  dans le code source. Utilisez des variables d'environnement / un gestionnaire de secrets.
- ❌ **Ne jamais** stocker l'image brute d'une empreinte côté application :
  `biometric-api` ne la conserve jamais après extraction, faites de même.
- ✅ **Toujours** utiliser HTTPS entre votre backend et `biometric-api` en
  production (le HMAC protège l'intégrité, pas la confidentialité en transit).
- ✅ **Toujours** appliquer votre propre RBAC avant d'appeler `enroll` ou
  `delete` — `biometric-api` ne vérifie aucune permission métier.
- ✅ En production multi-instances, configurer `RATE_LIMIT_STORAGE_URI` avec
  Redis (sinon chaque instance a son propre compteur de limite de débit).

---

## 9. Où trouver quoi dans le dépôt

```
biometric-platform/
├── biometric-core/        cœur biométrique (extraction, matching, chiffrement)
├── biometric-api/         serveur REST FastAPI — à démarrer en premier
├── frontend-sdk/          SDK navigateur (BiometricScanner + BiometricClient JS)
├── client-sdk/
│   ├── python/             SDK serveur Python
│   ├── javascript/         SDK serveur Node.js
│   ├── php/                 SDK serveur PHP
│   └── java/                 SDK serveur Java
├── connectors/             intégrations prêtes à l'emploi par framework (en cours)
├── tests/                    tests de biometric-core / biometric-api / intégration bout-en-bout
└── docs/                     ce fichier
```

Chaque dossier de SDK contient son propre `README.md` avec les détails
spécifiques à son langage (installation, gestion d'erreurs, exécution des
tests).
