# SDK DigitalPersona (à télécharger soi-même)

Ce dossier doit contenir deux fichiers fournis par HID Global / DigitalPersona :

| Fichier                   | Rôle                                                  |
|---------------------------|-------------------------------------------------------|
| `fingerprint.sdk.min.js`  | API JavaScript de capture d'empreinte (`Fingerprint.WebApi`) |
| `websdk.client.min.js`    | Client de communication avec l'agent DigitalPersona local    |

Ils ne sont **pas inclus dans ce dépôt** : ce sont des SDK propriétaires dont
la licence ne permet pas forcément la redistribution.

## Où les obtenir

- Installer le **DigitalPersona Lite Client** (ou HID Authentication Device
  Client) sur le poste équipé du lecteur ; les fichiers JavaScript sont
  fournis avec le SDK.
- Ou les récupérer depuis le dépôt d'exemples officiel :
  https://github.com/hidglobal/digitalpersona-devices (dossier des exemples web).

Copiez ensuite les deux fichiers ici, dans `frontend-sdk/vendor/`.
Ils sont ignorés par Git (`.gitignore`), ils ne seront donc jamais committés.
