package com.biometricplatform.client;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Map;

/**
 * Implémentation par défaut de HttpTransport, basée sur java.net.http.HttpClient
 * (disponible nativement depuis Java 11, aucune dépendance externe). Utilisée
 * automatiquement par BiometricClient en production ; les tests injectent une
 * implémentation en mémoire à la place.
 */
final class JdkHttpTransport implements HttpTransport {

    private final HttpClient httpClient = HttpClient.newHttpClient();

    @Override
    public HttpResult request(String method, String url, Map<String, String> headers, String body, long timeoutMs)
            throws BiometricClientException {
        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .timeout(Duration.ofMillis(timeoutMs));

        for (Map.Entry<String, String> header : headers.entrySet()) {
            builder.header(header.getKey(), header.getValue());
        }

        if ("GET".equals(method)) {
            builder.GET();
        } else {
            builder.method(method, body != null
                    ? HttpRequest.BodyPublishers.ofString(body)
                    : HttpRequest.BodyPublishers.noBody());
        }

        try {
            HttpResponse<String> response = httpClient.send(builder.build(), HttpResponse.BodyHandlers.ofString());
            return new HttpResult(response.statusCode(), response.body());
        } catch (java.net.http.HttpTimeoutException e) {
            throw new BiometricClientException.TimeoutException("Le serveur biométrique n'a pas répondu à temps.");
        } catch (IOException e) {
            throw new BiometricClientException.NetworkException(
                    "Impossible de contacter le serveur biométrique : " + e.getMessage());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new BiometricClientException.NetworkException("Requête interrompue.");
        }
    }
}
