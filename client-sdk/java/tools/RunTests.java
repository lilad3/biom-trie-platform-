package com.biometricplatform.client.tools;

import com.biometricplatform.client.*;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.lang.reflect.Constructor;
import java.nio.charset.StandardCharsets;
import java.util.Map;

/**
 * RunTests — exécuteur de tests Java pur, SANS dépendance à JUnit
 * (indisponible hors-ligne, Maven Central non accessible ici).
 *
 * En développement normal (avec Maven/Gradle + JUnit installés), utilisez
 * plutôt src/test/java/.../BiometricClientTest.java (le vrai fichier de
 * tests, écrit au format JUnit 5 standard).
 *
 * Ce runner réexécute les MÊMES scénarios manuellement, pour prouver que
 * le SDK fonctionne correctement même sans JUnit installé. FakeHttpTransport
 * étant package-private, ce runner l'instancie via réflexion.
 */
public final class RunTests {

    private static int passed = 0;
    private static int failed = 0;

    public static void main(String[] args) throws Exception {
        System.out.println("BiometricClient (Java) — tests");
        System.out.println("================================");

        check("lève ConfigurationException si baseUrl manquant", () -> {
            try {
                new BiometricClient("", "token");
                throw new RuntimeException("aucune exception levée");
            } catch (BiometricClientException.ConfigurationException expected) {
                return true;
            }
        });

        check("lève ConfigurationException si serviceAuthToken manquant", () -> {
            try {
                new BiometricClient("http://localhost:8001", "");
                throw new RuntimeException("aucune exception levée");
            } catch (BiometricClientException.ConfigurationException expected) {
                return true;
            }
        });

        check("enroll envoie le bon corps JSON et une signature valide", () -> {
            Object transport = fakeTransport(200,
                    "{\"success\":true,\"employeeId\":\"E1\",\"fingerType\":\"right_index\",\"message\":\"ok\"}");
            BiometricClient client = newClientWithTransport(transport);
            Results.EnrollResult result = client.enroll("E1", "right_index", "img-b64");

            assertEquals("POST", field(transport, "lastMethod"));
            assertEquals("http://localhost:8001/enroll", field(transport, "lastUrl"));
            String body = (String) field(transport, "lastBody");
            assertTrue(body.contains("\"employeeId\":\"E1\""));
            assertTrue(body.contains("\"fingerType\":\"right_index\""));
            assertTrue(body.contains("\"image\":\"img-b64\""));
            verifySignature((Map<?, ?>) field(transport, "lastHeaders"), body);
            assertTrue(result.success());
            return true;
        });

        check("identify envoie uniquement image", () -> {
            Object transport = fakeTransport(200,
                    "{\"success\":true,\"employeeId\":\"E2\",\"score\":55,\"message\":\"ok\"}");
            BiometricClient client = newClientWithTransport(transport);
            Results.IdentifyResult result = client.identify("img-b64");

            String body = (String) field(transport, "lastBody");
            assertTrue(body.contains("\"image\":\"img-b64\""));
            assertFalse(body.contains("employeeId"));
            assertEquals("E2", result.employeeId());
            return true;
        });

        check("verify envoie employeeId et image", () -> {
            Object transport = fakeTransport(200,
                    "{\"success\":true,\"match\":true,\"employeeId\":\"E3\",\"score\":80,\"message\":\"ok\"}");
            BiometricClient client = newClientWithTransport(transport);
            Results.VerifyResult result = client.verify("E3", "img-b64");

            assertEquals("http://localhost:8001/verify", field(transport, "lastUrl"));
            assertTrue(result.match());
            return true;
        });

        check("delete envoie uniquement employeeId", () -> {
            Object transport = fakeTransport(200,
                    "{\"success\":true,\"employeeId\":\"E4\",\"message\":\"supprime\"}");
            BiometricClient client = newClientWithTransport(transport);
            client.delete("E4");

            String body = (String) field(transport, "lastBody");
            assertTrue(body.contains("\"employeeId\":\"E4\""));
            assertFalse(body.contains("image"));
            return true;
        });

        check("health utilise GET sans signature", () -> {
            Object transport = fakeTransport(200,
                    "{\"status\":\"ok\",\"enrolled_employees\":3,\"service\":\"biometric-api\"}");
            BiometricClient client = newClientWithTransport(transport);
            Results.HealthResult result = client.health();

            assertEquals("GET", field(transport, "lastMethod"));
            Map<?, ?> headers = (Map<?, ?>) field(transport, "lastHeaders");
            assertFalse(headers.containsKey("X-Signature"));
            assertEquals(3, result.enrolledEmployees());
            return true;
        });

        check("erreur HTTP 401 lève ServerException avec statusCode", () -> {
            Object transport = fakeTransport(401, "{\"message\":\"Signature invalide.\"}");
            BiometricClient client = newClientWithTransport(transport);
            try {
                client.identify("img");
                throw new RuntimeException("aucune exception levée");
            } catch (BiometricClientException.ServerException e) {
                assertEquals(401, e.getStatusCode());
                return true;
            }
        });

        check("JSON invalide lève InvalidResponseException", () -> {
            Object transport = fakeTransport(200, "not json at all");
            BiometricClient client = newClientWithTransport(transport);
            try {
                client.identify("img");
                throw new RuntimeException("aucune exception levée");
            } catch (BiometricClientException.InvalidResponseException e) {
                return true;
            }
        });

        System.out.println("================================");
        System.out.println(passed + " passés, " + failed + " échoués");
        if (failed > 0) {
            System.exit(1);
        }
    }

    // --- Utilitaires de réflexion : FakeHttpTransport et le constructeur package-private
    // de BiometricClient sont volontairement non publics (détail d'implémentation
    // interne), donc ce runner externe (package tools) doit passer par la réflexion. ---

    private static Object fakeTransport(int status, String body) throws Exception {
        Class<?> cls = Class.forName("com.biometricplatform.client.FakeHttpTransport");
        Constructor<?> ctor = cls.getDeclaredConstructor(int.class, String.class);
        ctor.setAccessible(true);
        return ctor.newInstance(status, body);
    }

    private static BiometricClient newClientWithTransport(Object transport) throws Exception {
        Class<?> transportInterface = Class.forName("com.biometricplatform.client.HttpTransport");
        Constructor<?> ctor = BiometricClient.class.getDeclaredConstructor(
                String.class, String.class, long.class, transportInterface);
        ctor.setAccessible(true);
        return (BiometricClient) ctor.newInstance("http://localhost:8001", "test-service-token", 15_000L, transport);
    }

    private static Object field(Object obj, String name) throws Exception {
        var f = obj.getClass().getDeclaredField(name);
        f.setAccessible(true);
        return f.get(obj);
    }

    private static void verifySignature(Map<?, ?> headers, String body) throws Exception {
        String timestamp = (String) headers.get("X-Timestamp");
        String signature = (String) headers.get("X-Signature");
        String message = timestamp + "." + body;
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec("test-service-token".getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        byte[] rawHmac = mac.doFinal(message.getBytes(StandardCharsets.UTF_8));
        StringBuilder hex = new StringBuilder();
        for (byte b : rawHmac) hex.append(String.format("%02x", b));
        assertEquals(hex.toString(), signature);
    }

    private static void assertEquals(Object expected, Object actual) {
        if (!expected.equals(actual)) {
            throw new RuntimeException("attendu <" + expected + "> mais obtenu <" + actual + ">");
        }
    }

    private static void assertTrue(boolean cond) {
        if (!cond) throw new RuntimeException("assertion vraie échouée");
    }

    private static void assertFalse(boolean cond) {
        if (cond) throw new RuntimeException("assertion fausse échouée");
    }

    private static void check(String label, ThrowingSupplier body) {
        try {
            body.get();
            System.out.println("  [OK] " + label);
            passed++;
        } catch (Exception e) {
            System.out.println("  [FAIL] " + label + " -- " + e.getMessage());
            failed++;
        }
    }

    private interface ThrowingSupplier {
        boolean get() throws Exception;
    }
}
