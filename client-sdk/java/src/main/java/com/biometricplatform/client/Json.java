package com.biometricplatform.client;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Sérialisation/désérialisation JSON minimale, sans dépendance externe
 * (Jackson/Gson nécessiteraient Maven/Gradle, indisponibles pour ce SDK
 * "zéro dépendance"). Suffisant pour les objets JSON plats à un niveau
 * échangés avec biometric-api (chaînes, nombres, booléens, null).
 *
 * Usage interne uniquement : le développeur qui utilise BiometricClient ne
 * manipule jamais directement cette classe.
 */
final class Json {

    private Json() {
    }

    static String encode(Map<String, Object> map) {
        StringBuilder sb = new StringBuilder("{");
        boolean first = true;
        for (Map.Entry<String, Object> entry : map.entrySet()) {
            if (!first) {
                sb.append(',');
            }
            first = false;
            sb.append('"').append(escape(entry.getKey())).append("\":");
            sb.append(encodeValue(entry.getValue()));
        }
        sb.append('}');
        return sb.toString();
    }

    private static String encodeValue(Object value) {
        if (value == null) {
            return "null";
        }
        if (value instanceof String) {
            return '"' + escape((String) value) + '"';
        }
        if (value instanceof Boolean || value instanceof Number) {
            return value.toString();
        }
        throw new IllegalArgumentException("Type non supporté par l'encodeur JSON minimal : " + value.getClass());
    }

    private static String escape(String s) {
        StringBuilder sb = new StringBuilder();
        for (char c : s.toCharArray()) {
            switch (c) {
                case '"': sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                default:
                    if (c < 0x20) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
            }
        }
        return sb.toString();
    }

    /**
     * Parse un objet JSON plat (un seul niveau) en Map&lt;String,Object&gt;.
     * Les valeurs sont String, Double, Boolean ou null. Suffisant pour tous
     * les schémas de réponse de biometric-api (enroll/identify/verify/delete/health).
     */
    static Map<String, Object> decodeObject(String json) {
        Parser parser = new Parser(json);
        parser.skipWhitespace();
        Map<String, Object> result = parser.parseObject();
        parser.skipWhitespace();
        if (!parser.atEnd()) {
            throw new IllegalArgumentException("JSON invalide : caractères en trop après l'objet.");
        }
        return result;
    }

    private static final class Parser {
        private final String s;
        private int pos = 0;

        Parser(String s) {
            this.s = s;
        }

        boolean atEnd() {
            return pos >= s.length();
        }

        void skipWhitespace() {
            while (pos < s.length() && Character.isWhitespace(s.charAt(pos))) {
                pos++;
            }
        }

        char peek() {
            if (pos >= s.length()) {
                throw new IllegalArgumentException("JSON invalide : fin de chaîne inattendue.");
            }
            return s.charAt(pos);
        }

        char next() {
            char c = peek();
            pos++;
            return c;
        }

        void expect(char expected) {
            char c = next();
            if (c != expected) {
                throw new IllegalArgumentException("JSON invalide : attendu '" + expected + "' à la position " + (pos - 1));
            }
        }

        Map<String, Object> parseObject() {
            Map<String, Object> map = new LinkedHashMap<>();
            expect('{');
            skipWhitespace();
            if (peek() == '}') {
                pos++;
                return map;
            }
            while (true) {
                skipWhitespace();
                String key = parseString();
                skipWhitespace();
                expect(':');
                skipWhitespace();
                Object value = parseValue();
                map.put(key, value);
                skipWhitespace();
                char c = next();
                if (c == '}') {
                    break;
                }
                if (c != ',') {
                    throw new IllegalArgumentException("JSON invalide : attendu ',' ou '}'.");
                }
            }
            return map;
        }

        Object parseValue() {
            char c = peek();
            if (c == '"') {
                return parseString();
            }
            if (c == '{') {
                return parseObject();
            }
            if (c == 't') {
                expectLiteral("true");
                return Boolean.TRUE;
            }
            if (c == 'f') {
                expectLiteral("false");
                return Boolean.FALSE;
            }
            if (c == 'n') {
                expectLiteral("null");
                return null;
            }
            return parseNumber();
        }

        void expectLiteral(String literal) {
            if (pos + literal.length() > s.length() || !s.startsWith(literal, pos)) {
                throw new IllegalArgumentException("JSON invalide : littéral attendu '" + literal + "'.");
            }
            pos += literal.length();
        }

        String parseString() {
            expect('"');
            StringBuilder sb = new StringBuilder();
            while (true) {
                char c = next();
                if (c == '"') {
                    break;
                }
                if (c == '\\') {
                    char escapeChar = next();
                    switch (escapeChar) {
                        case '"': sb.append('"'); break;
                        case '\\': sb.append('\\'); break;
                        case '/': sb.append('/'); break;
                        case 'n': sb.append('\n'); break;
                        case 'r': sb.append('\r'); break;
                        case 't': sb.append('\t'); break;
                        case 'u':
                            String hex = s.substring(pos, pos + 4);
                            pos += 4;
                            sb.append((char) Integer.parseInt(hex, 16));
                            break;
                        default:
                            throw new IllegalArgumentException("Séquence d'échappement JSON invalide : \\" + escapeChar);
                    }
                } else {
                    sb.append(c);
                }
            }
            return sb.toString();
        }

        Double parseNumber() {
            int start = pos;
            while (pos < s.length() && "-+.eE0123456789".indexOf(s.charAt(pos)) >= 0) {
                pos++;
            }
            return Double.parseDouble(s.substring(start, pos));
        }
    }
}
