/**
 * biometric-client/src/errors.js
 * =================================
 * Hiérarchie d'erreurs du SDK. Le développeur ne voit jamais d'erreur
 * fetch/http brute : tout est traduit en erreurs de ce module.
 */
"use strict";

class BiometricClientError extends Error {
  constructor(message, code = "CLIENT_ERROR", statusCode = null) {
    super(message);
    this.name = "BiometricClientError";
    this.code = code;
    this.statusCode = statusCode;
  }
}

class ConfigurationError extends BiometricClientError {
  constructor(message) {
    super(message, "CONFIGURATION_ERROR");
    this.name = "ConfigurationError";
  }
}

class NetworkError extends BiometricClientError {
  constructor(message = "Impossible de contacter le serveur biométrique.") {
    super(message, "NETWORK_ERROR");
    this.name = "NetworkError";
  }
}

class TimeoutError extends BiometricClientError {
  constructor(message = "Le serveur biométrique n'a pas répondu à temps.") {
    super(message, "TIMEOUT");
    this.name = "TimeoutError";
  }
}

class ServerError extends BiometricClientError {
  constructor(message, statusCode) {
    super(message, "SERVER_ERROR", statusCode);
    this.name = "ServerError";
  }
}

class InvalidResponseError extends BiometricClientError {
  constructor(message = "Réponse du serveur biométrique illisible.") {
    super(message, "INVALID_RESPONSE");
    this.name = "InvalidResponseError";
  }
}

module.exports = {
  BiometricClientError,
  ConfigurationError,
  NetworkError,
  TimeoutError,
  ServerError,
  InvalidResponseError,
};
