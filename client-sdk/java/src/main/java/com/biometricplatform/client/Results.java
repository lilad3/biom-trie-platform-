package com.biometricplatform.client;

import java.util.Map;

/** Résultats typés retournés par BiometricClient, construits depuis la réponse JSON du serveur. */
public final class Results {

    private Results() {
    }

    public record EnrollResult(boolean success, String employeeId, String fingerType, String message) {
        static EnrollResult fromMap(Map<String, Object> m) {
            return new EnrollResult(
                    bool(m, "success"), str(m, "employeeId"), str(m, "fingerType"), str(m, "message"));
        }
    }

    public record IdentifyResult(boolean success, String employeeId, Integer score, String message) {
        static IdentifyResult fromMap(Map<String, Object> m) {
            return new IdentifyResult(
                    bool(m, "success"), str(m, "employeeId"), intOrNull(m, "score"), str(m, "message"));
        }
    }

    public record VerifyResult(boolean success, boolean match, String employeeId, Integer score, String message) {
        static VerifyResult fromMap(Map<String, Object> m) {
            return new VerifyResult(
                    bool(m, "success"), bool(m, "match"), str(m, "employeeId"), intOrNull(m, "score"), str(m, "message"));
        }
    }

    public record DeleteResult(boolean success, String employeeId, String message) {
        static DeleteResult fromMap(Map<String, Object> m) {
            return new DeleteResult(bool(m, "success"), str(m, "employeeId"), str(m, "message"));
        }
    }

    public record HealthResult(String status, int enrolledEmployees, String service) {
        static HealthResult fromMap(Map<String, Object> m) {
            return new HealthResult(str(m, "status"), intOrZero(m, "enrolled_employees"), str(m, "service"));
        }
    }

    private static boolean bool(Map<String, Object> m, String key) {
        Object v = m.get(key);
        return v instanceof Boolean && (Boolean) v;
    }

    private static String str(Map<String, Object> m, String key) {
        Object v = m.get(key);
        return v == null ? null : v.toString();
    }

    private static Integer intOrNull(Map<String, Object> m, String key) {
        Object v = m.get(key);
        return v instanceof Number ? ((Number) v).intValue() : null;
    }

    private static int intOrZero(Map<String, Object> m, String key) {
        Object v = m.get(key);
        return v instanceof Number ? ((Number) v).intValue() : 0;
    }
}
