package com.biometricplatform.client;

import org.junit.jupiter.api.Test;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests JUnit 5 standard. Nécessitent Maven/Gradle avec la dépendance
 * org.junit.jupiter:junit-jupiter pour s'exécuter (vendor/bin non fourni
 * dans ce SDK "zéro dépendance" par défaut). Voir RunTests.java pour un
 * exécuteur sans dépendance, qui couvre les mêmes scénarios.
 */
class BiometricClientTest {

    private static final String TOKEN = "test-service-token";
    private static final String BASE_URL = "http://localhost:8001";

    private static void assertValidSignature(String timestamp, String signature, String body) throws Exception {
        String message = timestamp + "." + body;
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(TOKEN.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        byte[] rawHmac = mac.doFinal(message.getBytes(StandardCharsets.UTF_8));
        StringBuilder hex = new StringBuilder();
        for (byte b : rawHmac) hex.append(String.format("%02x", b));
        assertEquals(hex.toString(), signature);
    }

    @Test
    void missingBaseUrlThrowsConfigurationException() {
        assertThrows(BiometricClientException.ConfigurationException.class,
                () -> new BiometricClient("", TOKEN));
    }

    @Test
    void missingTokenThrowsConfigurationException() {
        assertThrows(BiometricClientException.ConfigurationException.class,
                () -> new BiometricClient(BASE_URL, ""));
    }

    @Test
    void enrollSendsCorrectPayloadAndSignature() throws Exception {
        FakeHttpTransport transport = new FakeHttpTransport(200,
                "{\"success\":true,\"employeeId\":\"E1\",\"fingerType\":\"right_index\",\"message\":\"ok\"}");
        BiometricClient client = new BiometricClient(BASE_URL, TOKEN, 15_000L, transport);

        Results.EnrollResult result = client.enroll("E1", "right_index", "img-b64");

        assertEquals("POST", transport.lastMethod);
        assertEquals(BASE_URL + "/enroll", transport.lastUrl);
        assertValidSignature(transport.lastHeaders.get("X-Timestamp"), transport.lastHeaders.get("X-Signature"), transport.lastBody);
        assertTrue(result.success());
        assertEquals("E1", result.employeeId());
    }

    @Test
    void identifySendsOnlyImage() {
        FakeHttpTransport transport = new FakeHttpTransport(200,
                "{\"success\":true,\"employeeId\":\"E2\",\"score\":55,\"message\":\"ok\"}");
        BiometricClient client = new BiometricClient(BASE_URL, TOKEN, 15_000L, transport);

        Results.IdentifyResult result = client.identify("img-b64");

        assertTrue(transport.lastBody.contains("\"image\":\"img-b64\""));
        assertEquals("E2", result.employeeId());
        assertEquals(55, result.score());
    }

    @Test
    void verifySendsEmployeeIdAndImage() {
        FakeHttpTransport transport = new FakeHttpTransport(200,
                "{\"success\":true,\"match\":true,\"employeeId\":\"E3\",\"score\":80,\"message\":\"ok\"}");
        BiometricClient client = new BiometricClient(BASE_URL, TOKEN, 15_000L, transport);

        Results.VerifyResult result = client.verify("E3", "img-b64");

        assertEquals(BASE_URL + "/verify", transport.lastUrl);
        assertTrue(result.match());
    }

    @Test
    void deleteSendsOnlyEmployeeId() {
        FakeHttpTransport transport = new FakeHttpTransport(200,
                "{\"success\":true,\"employeeId\":\"E4\",\"message\":\"supprim\\u00e9\"}");
        BiometricClient client = new BiometricClient(BASE_URL, TOKEN, 15_000L, transport);

        client.delete("E4");

        assertTrue(transport.lastBody.contains("\"employeeId\":\"E4\""));
        assertFalse(transport.lastBody.contains("image"));
    }

    @Test
    void healthUsesGetWithoutSignature() {
        FakeHttpTransport transport = new FakeHttpTransport(200,
                "{\"status\":\"ok\",\"enrolled_employees\":3,\"service\":\"biometric-api\"}");
        BiometricClient client = new BiometricClient(BASE_URL, TOKEN, 15_000L, transport);

        Results.HealthResult result = client.health();

        assertEquals("GET", transport.lastMethod);
        assertFalse(transport.lastHeaders.containsKey("X-Signature"));
        assertEquals(3, result.enrolledEmployees());
    }

    @Test
    void serverErrorThrowsServerExceptionWithStatusCode() {
        FakeHttpTransport transport = new FakeHttpTransport(401, "{\"message\":\"Signature invalide.\"}");
        BiometricClient client = new BiometricClient(BASE_URL, TOKEN, 15_000L, transport);

        BiometricClientException.ServerException ex = assertThrows(
                BiometricClientException.ServerException.class, () -> client.identify("img"));
        assertEquals(401, ex.getStatusCode());
    }

    @Test
    void networkErrorPropagates() {
        FakeHttpTransport transport = new FakeHttpTransport(0, "",
                new BiometricClientException.NetworkException("connexion refusée"));
        BiometricClient client = new BiometricClient(BASE_URL, TOKEN, 15_000L, transport);

        assertThrows(BiometricClientException.NetworkException.class, () -> client.identify("img"));
    }

    @Test
    void invalidJsonThrowsInvalidResponseException() {
        FakeHttpTransport transport = new FakeHttpTransport(200, "not json at all");
        BiometricClient client = new BiometricClient(BASE_URL, TOKEN, 15_000L, transport);

        assertThrows(BiometricClientException.InvalidResponseException.class, () -> client.identify("img"));
    }
}
