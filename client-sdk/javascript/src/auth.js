/**
 * biometric-client/src/auth.js
 * ==============================
 * Signature HMAC-SHA256 des requêtes vers biometric-api, selon le protocole
 * exact attendu par app.security.auth.verify_service_signature côté serveur :
 *
 *   X-Timestamp: <epoch_seconds>
 *   X-Signature: hex(HMAC_SHA256(SERVICE_AUTH_TOKEN, `${timestamp}.${rawBody}`))
 *
 * Réimplémenté volontairement ici plutôt que d'importer biometric-api : ce
 * SDK doit être installable seul, dans n'importe quel projet Node (Express,
 * NestJS, script...), sans jamais dépendre du code du serveur biométrique.
 */
"use strict";

const crypto = require("crypto");

/**
 * @param {Buffer} bodyBuffer
 * @param {string} serviceAuthToken
 * @param {number} [timestamp] epoch seconds ; par défaut l'heure courante
 * @returns {{ "X-Timestamp": string, "X-Signature": string }}
 */
function signRequest(bodyBuffer, serviceAuthToken, timestamp) {
  const ts = timestamp !== undefined ? timestamp : Math.floor(Date.now() / 1000);
  const message = Buffer.concat([Buffer.from(`${ts}.`, "utf-8"), bodyBuffer]);
  const signature = crypto
    .createHmac("sha256", serviceAuthToken)
    .update(message)
    .digest("hex");
  return { "X-Timestamp": String(ts), "X-Signature": signature };
}

module.exports = { signRequest };
