/**
 * biometric-client/src/client.js
 * =================================
 * BiometricClient — SDK officiel Node.js pour biometric-api.
 *
 * Le développeur n'écrit jamais de fetch()/http.request() manuel, ne calcule
 * jamais de signature HMAC : il utilise directement client.enroll(...),
 * client.identify(...), client.verify(...), client.delete(...).
 *
 * Fait pour être utilisé CÔTÉ SERVEUR (Express, NestJS, un script...),
 * jamais côté navigateur : il porte le secret serviceAuthToken. Pour le
 * frontend, voir frontend-sdk/ (BiometricScanner + BiometricClient JS
 * navigateur, qui lui parle à un proxy, jamais à biometric-api directement).
 *
 * Usage :
 *   const { BiometricClient } = require("biometric-client");
 *   const client = new BiometricClient({
 *     baseUrl: "http://localhost:8001",
 *     serviceAuthToken: "...",
 *   });
 *   const result = await client.identify(imageBase64);
 */
"use strict";

const { signRequest } = require("./auth");
const {
  ConfigurationError,
  NetworkError,
  TimeoutError,
  ServerError,
  InvalidResponseError,
} = require("./errors");

class BiometricClient {
  /**
   * @param {Object} options
   * @param {string} options.baseUrl
   * @param {string} options.serviceAuthToken
   * @param {number} [options.timeoutMs=15000]
   */
  constructor(options = {}) {
    if (!options.baseUrl) {
      throw new ConfigurationError("baseUrl est requis pour initialiser BiometricClient.");
    }
    if (!options.serviceAuthToken) {
      throw new ConfigurationError("serviceAuthToken est requis pour initialiser BiometricClient.");
    }
    this._baseUrl = options.baseUrl.replace(/\/+$/, "");
    this._serviceAuthToken = options.serviceAuthToken;
    this._timeoutMs = options.timeoutMs || 15000;
  }

  async _request(method, path, payload) {
    const bodyBuffer = payload !== undefined ? Buffer.from(JSON.stringify(payload), "utf-8") : Buffer.alloc(0);
    const headers = { "Content-Type": "application/json" };

    if (payload !== undefined) {
      Object.assign(headers, signRequest(bodyBuffer, this._serviceAuthToken));
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this._timeoutMs);

    let response;
    try {
      response = await fetch(this._baseUrl + path, {
        method,
        headers,
        body: payload !== undefined ? bodyBuffer : undefined,
        signal: controller.signal,
      });
    } catch (error) {
      if (error && error.name === "AbortError") {
        throw new TimeoutError();
      }
      throw new NetworkError(`Impossible de contacter le serveur biométrique : ${error.message}`);
    } finally {
      clearTimeout(timeout);
    }

    let data;
    try {
      data = await response.json();
    } catch (error) {
      throw new InvalidResponseError();
    }

    if (!response.ok) {
      throw new ServerError(
        (data && data.message) || `Erreur du serveur biométrique (HTTP ${response.status}).`,
        response.status
      );
    }

    return data;
  }

  /** Enregistre une nouvelle empreinte pour un employé. */
  async enroll(employeeId, fingerType, imageBase64) {
    return this._request("POST", "/enroll", { employeeId, fingerType, image: imageBase64 });
  }

  /** Identification 1:N : retrouve l'employé correspondant parmi tous les enrôlés. */
  async identify(imageBase64) {
    return this._request("POST", "/identify", { image: imageBase64 });
  }

  /** Vérification 1:1 : confirme (ou non) qu'une image correspond à cet employé. */
  async verify(employeeId, imageBase64) {
    return this._request("POST", "/verify", { employeeId, image: imageBase64 });
  }

  /** Supprime définitivement toutes les empreintes d'un employé. */
  async delete(employeeId) {
    return this._request("POST", "/delete", { employeeId });
  }

  /** Sonde de disponibilité du service (aucune authentification requise). */
  async health() {
    return this._request("GET", "/health", undefined);
  }
}

module.exports = { BiometricClient };
