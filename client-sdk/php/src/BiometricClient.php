<?php

declare(strict_types=1);

namespace BiometricClient;

/**
 * BiometricClient — SDK officiel PHP pour biometric-api.
 *
 * Le développeur n'écrit jamais de curl_init() manuel, ne calcule jamais de
 * signature HMAC : il appelle $client->identify($image).
 *
 * Fait pour être utilisé CÔTÉ SERVEUR (Laravel, Symfony, PHP natif...),
 * jamais côté navigateur : il porte le secret $serviceAuthToken.
 *
 * Usage :
 *   $client = new BiometricClient('http://localhost:8001', 'mon-token');
 *   $result = $client->identify($imageBase64);
 *   if ($result['success']) { echo $result['employeeId']; }
 */
class BiometricClient
{
    private string $baseUrl;
    private string $serviceAuthToken;
    private float $timeoutSeconds;
    private HttpTransport $transport;

    public function __construct(
        string $baseUrl,
        string $serviceAuthToken,
        float $timeoutSeconds = 15.0,
        ?HttpTransport $transport = null
    ) {
        if ($baseUrl === '') {
            throw new ConfigurationException('baseUrl est requis pour initialiser BiometricClient.');
        }
        if ($serviceAuthToken === '') {
            throw new ConfigurationException('serviceAuthToken est requis pour initialiser BiometricClient.');
        }

        $this->baseUrl = rtrim($baseUrl, '/');
        $this->serviceAuthToken = $serviceAuthToken;
        $this->timeoutSeconds = $timeoutSeconds;
        $this->transport = $transport ?? new CurlHttpTransport();
    }

    /**
     * Calcule les headers X-Timestamp/X-Signature attendus par biometric-api,
     * selon le même protocole que les autres SDK de la plateforme :
     *   X-Signature: hex(HMAC_SHA256(serviceAuthToken, "{timestamp}.{rawBody}"))
     */
    private function signRequest(string $bodyRaw, ?int $timestamp = null): array
    {
        $timestamp = $timestamp ?? time();
        $message = "$timestamp." . $bodyRaw;
        $signature = hash_hmac('sha256', $message, $this->serviceAuthToken);
        return ['X-Timestamp' => (string) $timestamp, 'X-Signature' => $signature];
    }

    private function post(string $path, array $payload): array
    {
        $bodyRaw = json_encode($payload, JSON_UNESCAPED_UNICODE);
        if ($bodyRaw === false) {
            throw new InvalidResponseException('Impossible de sérialiser la requête en JSON.');
        }

        $headers = array_merge(
            ['Content-Type' => 'application/json'],
            $this->signRequest($bodyRaw)
        );

        $response = $this->transport->request('POST', $this->baseUrl . $path, $headers, $bodyRaw, $this->timeoutSeconds);
        return $this->parseResponse($response);
    }

    private function get(string $path): array
    {
        $response = $this->transport->request('GET', $this->baseUrl . $path, [], null, $this->timeoutSeconds);
        return $this->parseResponse($response);
    }

    private function parseResponse(array $response): array
    {
        $data = json_decode($response['body'], true);
        if (!is_array($data)) {
            throw new InvalidResponseException();
        }

        if ($response['status'] < 200 || $response['status'] >= 300) {
            $message = $data['message'] ?? "Erreur du serveur biométrique (HTTP {$response['status']}).";
            throw new ServerException($message, $response['status']);
        }

        return $data;
    }

    /** Enregistre une nouvelle empreinte pour un employé. */
    public function enroll(string $employeeId, string $fingerType, string $imageBase64): array
    {
        return $this->post('/enroll', [
            'employeeId' => $employeeId,
            'fingerType' => $fingerType,
            'image' => $imageBase64,
        ]);
    }

    /** Identification 1:N : retrouve l'employé correspondant parmi tous les enrôlés. */
    public function identify(string $imageBase64): array
    {
        return $this->post('/identify', ['image' => $imageBase64]);
    }

    /** Vérification 1:1 : confirme (ou non) qu'une image correspond à cet employé. */
    public function verify(string $employeeId, string $imageBase64): array
    {
        return $this->post('/verify', ['employeeId' => $employeeId, 'image' => $imageBase64]);
    }

    /** Supprime définitivement toutes les empreintes d'un employé. */
    public function delete(string $employeeId): array
    {
        return $this->post('/delete', ['employeeId' => $employeeId]);
    }

    /** Sonde de disponibilité du service (aucune authentification requise). */
    public function health(): array
    {
        return $this->get('/health');
    }
}
