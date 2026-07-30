package com.biometricplatform.client;

import java.util.HashMap;
import java.util.Map;

/**
 * Transport HTTP en mémoire pour les tests : aucun appel réseau réel.
 * Enregistre la dernière requête reçue pour permettre aux tests de vérifier
 * method/url/headers/body, et retourne une réponse programmée.
 */
final class FakeHttpTransport implements HttpTransport {

    String lastMethod;
    String lastUrl;
    Map<String, String> lastHeaders;
    String lastBody;

    private final int responseStatus;
    private final String responseBody;
    private final BiometricClientException throwOnRequest;

    FakeHttpTransport(int responseStatus, String responseBody) {
        this(responseStatus, responseBody, null);
    }

    FakeHttpTransport(int responseStatus, String responseBody, BiometricClientException throwOnRequest) {
        this.responseStatus = responseStatus;
        this.responseBody = responseBody;
        this.throwOnRequest = throwOnRequest;
    }

    @Override
    public HttpResult request(String method, String url, Map<String, String> headers, String body, long timeoutMs) {
        this.lastMethod = method;
        this.lastUrl = url;
        this.lastHeaders = new HashMap<>(headers);
        this.lastBody = body;

        if (throwOnRequest != null) {
            throw throwOnRequest;
        }

        return new HttpResult(responseStatus, responseBody);
    }
}
