<?php

declare(strict_types=1);

namespace BiometricClient;

/**
 * Abstraction du transport HTTP. Permet d'injecter un faux transport dans
 * les tests (sans dépendre d'un vrai réseau ni d'un mock cURL fragile),
 * tout en gardant CurlHttpTransport comme implémentation par défaut en
 * production. Le développeur final n'a jamais besoin de connaître cette
 * interface : BiometricClient l'utilise en interne uniquement.
 */
interface HttpTransport
{
    /**
     * @param string $method 'GET' ou 'POST'
     * @param string $url
     * @param array<string,string> $headers
     * @param string|null $body
     * @param float $timeoutSeconds
     * @return array{status:int, body:string}
     * @throws NetworkException
     * @throws TimeoutException
     */
    public function request(string $method, string $url, array $headers, ?string $body, float $timeoutSeconds): array;
}
