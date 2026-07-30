package com.biometricplatform.client;

/**
 * Hiérarchie d'exceptions du SDK. Le développeur ne voit jamais d'exception
 * HttpClient brute : tout est traduit en exceptions de ce package.
 */
public class BiometricClientException extends RuntimeException {
    private final String code;
    private final Integer statusCode;

    public BiometricClientException(String message, String code, Integer statusCode) {
        super(message);
        this.code = code;
        this.statusCode = statusCode;
    }

    public BiometricClientException(String message, String code) {
        this(message, code, null);
    }

    public String getCode() {
        return code;
    }

    public Integer getStatusCode() {
        return statusCode;
    }

    public static class ConfigurationException extends BiometricClientException {
        public ConfigurationException(String message) {
            super(message, "CONFIGURATION_ERROR");
        }
    }

    public static class NetworkException extends BiometricClientException {
        public NetworkException(String message) {
            super(message, "NETWORK_ERROR");
        }
    }

    public static class TimeoutException extends BiometricClientException {
        public TimeoutException(String message) {
            super(message, "TIMEOUT");
        }
    }

    public static class ServerException extends BiometricClientException {
        public ServerException(String message, int statusCode) {
            super(message, "SERVER_ERROR", statusCode);
        }
    }

    public static class InvalidResponseException extends BiometricClientException {
        public InvalidResponseException(String message) {
            super(message, "INVALID_RESPONSE");
        }
    }
}
