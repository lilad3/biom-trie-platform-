package com.biometricplatform.client;

/**
 * Abstraction du transport HTTP, injectable pour les tests (évite de
 * dépendre d'un vrai réseau ou d'un mock HttpClient fragile). L'implémentation
 * par défaut en production utilise java.net.http.HttpClient (JDK standard,
 * aucune dépendance externe). Usage interne uniquement.
 */
interface HttpTransport {
    HttpResult request(String method, String url, java.util.Map<String, String> headers, String body, long timeoutMs)
            throws BiometricClientException;

    record HttpResult(int status, String body) {
    }
}
