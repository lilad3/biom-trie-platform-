# biometric-client (Node.js)

SDK officiel Node.js pour `biometric-api`, à utiliser **côté serveur**
(Express, NestJS, un script...). Ne pas confondre avec `frontend-sdk/`, qui
tourne dans le navigateur et ne porte jamais de secret.

## Installation

```bash
npm install <chemin-vers>/client-sdk/javascript
```

## Usage

```js
const { BiometricClient } = require("biometric-client");

const client = new BiometricClient({
  baseUrl: "http://localhost:8001",
  serviceAuthToken: process.env.BIOMETRIC_SERVICE_TOKEN,
});

const result = await client.identify(imageBase64);
if (result.success) {
  console.log("Employé identifié :", result.employeeId);
}
```

## Gestion des erreurs

```js
const { NetworkError, ServerError, TimeoutError } = require("biometric-client");

try {
  await client.identify(imageBase64);
} catch (err) {
  if (err instanceof TimeoutError) { /* ... */ }
  else if (err instanceof ServerError) { console.log(err.statusCode); }
  else if (err instanceof NetworkError) { /* ... */ }
}
```

## ⚠️ Sécurité

`serviceAuthToken` est un secret serveur. N'utilisez jamais ce SDK dans du
code exécuté côté navigateur (webpack bundle client, etc.) — pour le
frontend, utilisez `frontend-sdk/`.

## Tests

```bash
npm install
npm test
```
