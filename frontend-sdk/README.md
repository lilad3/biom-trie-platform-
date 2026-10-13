# frontend-sdk

SDK JavaScript qui masque totalement DigitalPersona (et, plus largement,
tout matériel de capture biométrique) derrière une API simple.

## Deux classes, deux responsabilités

- **`BiometricScanner`** — parle au lecteur USB local (via l'agent DigitalPersona).
  Le développeur ne voit jamais `Fingerprint.WebApi`, les événements bas niveau,
  ni les codes de qualité DigitalPersona.
- **`BiometricClient`** — parle au serveur biométrique (HTTP JSON). Le développeur
  n'écrit jamais de `fetch()` ni ne gère de headers de signature.

## Usage

> Les deux fichiers `vendor/` (SDK DigitalPersona) ne sont pas fournis dans le dépôt :
> voir [vendor/README.md](vendor/README.md) pour les télécharger.

```html
<script src="vendor/fingerprint.sdk.min.js"></script>
<script src="vendor/websdk.client.min.js"></script>
<script src="dist/biometric-sdk.js"></script>
```

```js
const scanner = new BiometricScanner();
const client = new BiometricClient({ baseUrl: "/api/biometrie" });

await scanner.connect();
const capture = await scanner.capture({
  onQuality: (q) => console.log(`Qualité : ${q.percent}%`),
});

if (capture.isAcceptable) {
  const result = await client.identify(capture.image);
  if (result.success) {
    console.log("Employé identifié :", result.employeeId);
  }
}
```

## ⚠️ Sécurité : pourquoi `baseUrl` n'est JAMAIS l'URL de biometric-api directement

`biometric-api` exige une signature HMAC (`X-Signature`/`X-Timestamp`) calculée
à partir de `SERVICE_AUTH_TOKEN`. Ce jeton est un secret serveur : il ne doit
**jamais** apparaître dans du code exécuté dans le navigateur.

Donc `BiometricClient` doit toujours pointer vers un **endpoint proxy** exposé
par l'application hôte (Django, Laravel...), qui :
1. authentifie l'utilisateur final (JWT/session/RBAC — logique métier normale de l'appli hôte) ;
2. relaie la requête vers `biometric-api` en signant lui-même avec le token, côté serveur.

Voir `connectors/django/` pour un exemple de ce proxy côté Django.

## Build

Ce SDK est distribué en un seul fichier concaténé (`dist/biometric-sdk.js`)
pour un `<script>` simple, sans étape de bundling côté intégrateur. Voir
`build.sh` pour régénérer `dist/` à partir de `src/`.

## Compatibilité

Nécessite `fetch`, `Promise`, et `class` (ES2015+) — supporté par tous les
navigateurs modernes. Pas de dépendance à un framework (React, Vue...) :
utilisable tel quel dans n'importe quelle page HTML.
