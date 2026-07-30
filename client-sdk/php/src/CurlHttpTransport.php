<?php

declare(strict_types=1);

namespace BiometricClient;

/**
 * Implémentation par défaut de HttpTransport, basée sur l'extension cURL
 * de PHP. Utilisée automatiquement par BiometricClient en production ;
 * les tests injectent une implémentation en mémoire à la place.
 */
class CurlHttpTransport implements HttpTransport
{
    public function request(string $method, string $url, array $headers, ?string $body, float $timeoutSeconds): array
    {
        $ch = curl_init($url);
        if ($ch === false) {
            throw new NetworkException("Impossible d'initialiser la requête HTTP.");
        }

        $headerLines = [];
        foreach ($headers as $name => $value) {
            $headerLines[] = "$name: $value";
        }

        curl_setopt_array($ch, [
            CURLOPT_CUSTOMREQUEST => $method,
            CURLOPT_HTTPHEADER => $headerLines,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT_MS => (int) ($timeoutSeconds * 1000),
            CURLOPT_CONNECTTIMEOUT_MS => (int) ($timeoutSeconds * 1000),
        ]);

        if ($body !== null) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
        }

        $responseBody = curl_exec($ch);
        $errno = curl_errno($ch);
        $status = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($errno === CURLE_OPERATION_TIMEDOUT) {
            throw new TimeoutException();
        }
        if ($errno !== 0 || $responseBody === false) {
            throw new NetworkException("Erreur réseau lors de l'appel au serveur biométrique (cURL errno $errno).");
        }

        return ['status' => $status, 'body' => $responseBody];
    }
}
