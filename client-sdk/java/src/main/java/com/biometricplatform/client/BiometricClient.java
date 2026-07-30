package com.biometricplatform.client;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * BiometricClient — SDK officiel Java pour biometric-api.
 *
 * Le développeur n'écrit jamais de HttpClient manuel, ne calcule jamais de
 * signature HMAC : il appelle client.identify(image).
 *
 * Fait pour être utilisé CÔTÉ SERVEUR (Spring Boot, Jakarta EE, une app
 * batch...), jamais côté client lourd exposé à l'utilisateur final : il
 * porte le secret serviceAuthToken.
 *
 * Usage :
 *   BiometricClient client = new BiometricClient("http://localhost:8001", "mon-token");
 *   Results.IdentifyResult result = client.identify(imageBase64);
 */
public final class BiometricClient implements AutoCloseable {

    private final String baseUrl;
    private final String serviceAuthToken;
    private final long timeoutMs;
    private final HttpTransport transport;

    public BiometricClient(String baseUrl, String serviceAuthToken) {
        this(baseUrl, serviceAuthToken, 15_000L, null);
    }

    public BiometricClient(String baseUrl, String serviceAuthToken, long timeoutMs) {
        this(baseUrl, serviceAuthToken, timeoutMs, null);
    }

    // package-private : réservé aux tests, pour injecter un HttpTransport en mémoire
    BiometricClient(String baseUrl, String serviceAuthToken, long timeoutMs, HttpTransport transport) {
        if (baseUrl == null || baseUrl.isEmpty()) {
            throw new BiometricClientException.ConfigurationException(
                    "baseUrl est requis pour initialiser BiometricClient.");
        }
        if (serviceAuthToken == null || serviceAuthToken.isEmpty()) {
            throw new BiometricClientException.ConfigurationException(
                    "serviceAuthToken est requis pour initialiser BiometricClient.");
        }
        this.baseUrl = baseUrl.replaceAll("/+$", "");
        this.serviceAuthToken = serviceAuthToken;
        this.timeoutMs = timeoutMs;
        this.transport = transport != null ? transport : new JdkHttpTransport();
    }

    private Map<String, String> signRequest(String bodyRaw) {
        long timestamp = Instant.now().getEpochSecond();
        String message = timestamp + "." + bodyRaw;
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(serviceAuthToken.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            byte[] rawHmac = mac.doFinal(message.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder();
            for (byte b : rawHmac) {
                hex.append(String.format("%02x", b));
            }
            Map<String, String> headers = new HashMap<>();
            headers.put("X-Timestamp", String.valueOf(timestamp));
            headers.put("X-Signature", hex.toString());
            return headers;
        } catch (NoSuchAlgorithmException | InvalidKeyException e) {
            throw new IllegalStateException("HmacSHA256 indisponible dans cet environnement Java.", e);
        }
    }

    private Map<String, Object> post(String path, Map<String, Object> payload) {
        String bodyRaw = Json.encode(payload);
        Map<String, String> headers = new HashMap<>(signRequest(bodyRaw));
        headers.put("Content-Type", "application/json");

        HttpTransport.HttpResult response = transport.request("POST", baseUrl + path, headers, bodyRaw, timeoutMs);
        return parseResponse(response);
    }

    private Map<String, Object> get(String path) {
        HttpTransport.HttpResult response = transport.request("GET", baseUrl + path, Map.of(), null, timeoutMs);
        return parseResponse(response);
    }

    private Map<String, Object> parseResponse(HttpTransport.HttpResult response) {
        Map<String, Object> data;
        try {
            data = Json.decodeObject(response.body());
        } catch (RuntimeException e) {
            throw new BiometricClientException.InvalidResponseException(
                    "Réponse du serveur biométrique illisible.");
        }

        if (response.status() < 200 || response.status() >= 300) {
            Object message = data.get("message");
            throw new BiometricClientException.ServerException(
                    message != null ? message.toString() : "Erreur du serveur biométrique (HTTP " + response.status() + ").",
                    response.status());
        }

        return data;
    }

    /** Enregistre une nouvelle empreinte pour un employé. */
    public Results.EnrollResult enroll(String employeeId, String fingerType, String imageBase64) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("employeeId", employeeId);
        payload.put("fingerType", fingerType);
        payload.put("image", imageBase64);
        return Results.EnrollResult.fromMap(post("/enroll", payload));
    }

    /** Identification 1:N : retrouve l'employé correspondant parmi tous les enrôlés. */
    public Results.IdentifyResult identify(String imageBase64) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("image", imageBase64);
        return Results.IdentifyResult.fromMap(post("/identify", payload));
    }

    /** Vérification 1:1 : confirme (ou non) qu'une image correspond à cet employé. */
    public Results.VerifyResult verify(String employeeId, String imageBase64) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("employeeId", employeeId);
        payload.put("image", imageBase64);
        return Results.VerifyResult.fromMap(post("/verify", payload));
    }

    /** Supprime définitivement toutes les empreintes d'un employé. */
    public Results.DeleteResult delete(String employeeId) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("employeeId", employeeId);
        return Results.DeleteResult.fromMap(post("/delete", payload));
    }

    /** Sonde de disponibilité du service (aucune authentification requise). */
    public Results.HealthResult health() {
        return Results.HealthResult.fromMap(get("/health"));
    }

    @Override
    public void close() {
        // java.net.http.HttpClient ne nécessite pas de fermeture explicite ;
        // méthode fournie pour un usage try-with-resources idiomatique.
    }
}
