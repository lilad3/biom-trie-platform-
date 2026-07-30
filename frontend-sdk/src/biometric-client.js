/**
 * @biometric-platform/frontend-sdk — BiometricClient
 * =====================================================
 * Encapsule TOTALEMENT les appels HTTP vers biometric-api. Le développeur
 * n'écrit jamais de fetch(), ne construit jamais d'URL, ne gère jamais les
 * headers de signature : il appelle client.enroll(...), client.identify(...),
 * client.verify(...), client.delete(...).
 *
 * IMPORTANT — sécurité : ce client ne porte JAMAIS le secret d'authentification
 * inter-services (SERVICE_AUTH_TOKEN). Ce jeton reste côté serveur (dans
 * l'application hôte : Django, Laravel...), qui signe la requête HMAC avant
 * de la relayer. Ce SDK frontend appelle donc en pratique un endpoint proxy
 * de l'application hôte (ex: /api/biometrie/identify côté Django), jamais
 * directement biometric-api : aucune clé ne doit jamais apparaître dans le
 * JavaScript exécuté dans le navigateur (exigence explicite du cahier des
 * charges : "Aucune API Key visible dans le JavaScript").
 *
 * Usage :
 *   const client = new BiometricClient({ baseUrl: "/api/biometrie" });
 *   const result = await client.identify(capture.image);
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.BiometricClient = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  class BiometricClientError extends Error {
    constructor(message, code, status) {
      super(message);
      this.name = "BiometricClientError";
      this.code = code || "CLIENT_ERROR";
      this.status = status || null;
    }
  }

  class BiometricClient {
    /**
     * @param {Object} options
     * @param {string} options.baseUrl Base de l'API proxy côté application
     *   hôte (PAS l'URL directe de biometric-api). Ex: "/api/biometrie".
     * @param {Object} [options.headers] En-têtes additionnels à joindre à
     *   chaque requête (ex: en-tête CSRF requis par Django).
     * @param {number} [options.timeoutMs=15000]
     */
    constructor(options = {}) {
      if (!options.baseUrl) {
        throw new BiometricClientError(
          "baseUrl est requis pour initialiser BiometricClient.",
          "MISSING_BASE_URL"
        );
      }
      this._baseUrl = options.baseUrl.replace(/\/+$/, "");
      this._headers = options.headers || {};
      this._timeoutMs = options.timeoutMs || 15000;
    }

    async _post(path, body) {
      const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
      const timeout = controller
        ? setTimeout(() => controller.abort(), this._timeoutMs)
        : null;

      let response;
      try {
        response = await fetch(this._baseUrl + path, {
          method: "POST",
          headers: Object.assign(
            { "Content-Type": "application/json" },
            this._headers
          ),
          body: JSON.stringify(body),
          signal: controller ? controller.signal : undefined,
        });
      } catch (error) {
        if (error && error.name === "AbortError") {
          throw new BiometricClientError(
            "Le serveur biométrique n'a pas répondu à temps.",
            "TIMEOUT"
          );
        }
        throw new BiometricClientError(
          "Impossible de contacter le serveur biométrique.",
          "NETWORK_ERROR"
        );
      } finally {
        if (timeout) clearTimeout(timeout);
      }

      let data;
      try {
        data = await response.json();
      } catch (error) {
        throw new BiometricClientError(
          "Réponse du serveur biométrique illisible.",
          "INVALID_RESPONSE",
          response.status
        );
      }

      if (!response.ok) {
        throw new BiometricClientError(
          (data && data.message) || "Erreur du serveur biométrique.",
          "SERVER_ERROR",
          response.status
        );
      }

      return data;
    }

    /**
     * Enregistre une nouvelle empreinte pour un employé.
     * @param {string} employeeId
     * @param {string} fingerType ex: "right_index"
     * @param {string} image base64 (data URL ou brut), tel que retourné par BiometricScanner.capture()
     * @returns {Promise<{success:boolean, employeeId:string, fingerType:string, message:string}>}
     */
    async enroll(employeeId, fingerType, image) {
      return this._post("/enroll", { employeeId, fingerType, image });
    }

    /**
     * Identification 1:N — retrouve l'employé correspondant à l'image parmi
     * tous les employés enrôlés.
     * @param {string} image
     * @returns {Promise<{success:boolean, employeeId?:string, score?:number, message:string}>}
     */
    async identify(image) {
      return this._post("/identify", { image });
    }

    /**
     * Vérification 1:1 — confirme (ou non) qu'une image correspond bien à
     * l'employé donné.
     * @param {string} employeeId
     * @param {string} image
     * @returns {Promise<{success:boolean, match:boolean, employeeId:string, score?:number, message:string}>}
     */
    async verify(employeeId, image) {
      return this._post("/verify", { employeeId, image });
    }

    /**
     * Supprime définitivement toutes les empreintes d'un employé.
     * @param {string} employeeId
     * @returns {Promise<{success:boolean, employeeId:string, message:string}>}
     */
    async delete(employeeId) {
      return this._post("/delete", { employeeId });
    }
  }

  BiometricClient.BiometricClientError = BiometricClientError;
  return BiometricClient;
});
