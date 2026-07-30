<?php

declare(strict_types=1);

namespace BiometricClient\Tests;

use BiometricClient\HttpTransport;
use BiometricClient\NetworkException;
use BiometricClient\TimeoutException;

/**
 * Transport HTTP en mémoire pour les tests : ne fait aucun appel réseau
 * réel. Enregistre la dernière requête reçue pour permettre aux tests de
 * vérifier method/url/headers/body, et retourne une réponse programmée.
 */
class FakeHttpTransport implements HttpTransport
{
    public ?array $lastRequest = null;
    private int $responseStatus;
    private string $responseBody;
    private ?\Throwable $throwOnRequest;

    public function __construct(int $responseStatus = 200, string $responseBody = '{}', ?\Throwable $throwOnRequest = null)
    {
        $this->responseStatus = $responseStatus;
        $this->responseBody = $responseBody;
        $this->throwOnRequest = $throwOnRequest;
    }

    public function request(string $method, string $url, array $headers, ?string $body, float $timeoutSeconds): array
    {
        $this->lastRequest = compact('method', 'url', 'headers', 'body', 'timeoutSeconds');

        if ($this->throwOnRequest !== null) {
            throw $this->throwOnRequest;
        }

        return ['status' => $this->responseStatus, 'body' => $this->responseBody];
    }
}
