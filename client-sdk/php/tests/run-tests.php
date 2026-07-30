<?php

declare(strict_types=1);

/**
 * run-tests.php
 * ==============
 * Mini test-runner PHP pur, SANS dépendance à PHPUnit. Utilisé uniquement
 * pour valider ce SDK dans un environnement sans accès à Packagist/Composer.
 *
 * En développement normal (avec composer install), utilisez plutôt :
 *   vendor/bin/phpunit tests/
 * qui exécutera tests/BiometricClientTest.php (le vrai fichier de tests,
 * écrit au format PHPUnit standard).
 *
 * Ce runner réexécute les MÊMES scénarios manuellement, pour prouver que
 * le SDK fonctionne correctement même sans PHPUnit installé.
 */

require __DIR__ . '/../src/HttpTransport.php';
require __DIR__ . '/../src/Exceptions.php';
require __DIR__ . '/../src/CurlHttpTransport.php';
require __DIR__ . '/../src/BiometricClient.php';
require __DIR__ . '/FakeHttpTransport.php';

use BiometricClient\BiometricClient;
use BiometricClient\ConfigurationException;
use BiometricClient\NetworkException;
use BiometricClient\ServerException;
use BiometricClient\InvalidResponseException;
use BiometricClient\Tests\FakeHttpTransport;

const TOKEN = 'test-service-token';
const BASE_URL = 'http://localhost:8001';

$passed = 0;
$failed = 0;

function check(string $label, callable $fn): void
{
    global $passed, $failed;
    try {
        $fn();
        echo "  [OK] $label\n";
        $passed++;
    } catch (\Throwable $e) {
        echo "  [FAIL] $label -- " . $e->getMessage() . "\n";
        $failed++;
    }
}

function assertTrue(bool $cond, string $msg = 'assertion échouée'): void
{
    if (!$cond) {
        throw new \RuntimeException($msg);
    }
}

function assertSame($expected, $actual, string $msg = ''): void
{
    if ($expected !== $actual) {
        $e = var_export($expected, true);
        $a = var_export($actual, true);
        throw new \RuntimeException("$msg (attendu: $e, obtenu: $a)");
    }
}

function verifySig(array $headers, string $body, string $token = TOKEN): void
{
    $timestamp = $headers['X-Timestamp'];
    $expected = hash_hmac('sha256', "$timestamp.$body", $token);
    assertSame($expected, $headers['X-Signature'], 'Signature HMAC incorrecte');
}

echo "BiometricClient (PHP) — tests\n";
echo "================================\n";

check('lève ConfigurationException si baseUrl manquant', function () {
    try {
        new BiometricClient('', TOKEN);
        throw new \RuntimeException('aucune exception levée');
    } catch (ConfigurationException $e) {
        // attendu
    }
});

check('lève ConfigurationException si serviceAuthToken manquant', function () {
    try {
        new BiometricClient(BASE_URL, '');
        throw new \RuntimeException('aucune exception levée');
    } catch (ConfigurationException $e) {
        // attendu
    }
});

check('enroll envoie le bon corps JSON et une signature valide', function () {
    $transport = new FakeHttpTransport(200, json_encode([
        'success' => true, 'employeeId' => 'E1', 'fingerType' => 'right_index', 'message' => 'ok',
    ]));
    $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);
    $result = $client->enroll('E1', 'right_index', 'img-b64');

    assertSame('POST', $transport->lastRequest['method']);
    assertSame(BASE_URL . '/enroll', $transport->lastRequest['url']);
    $body = json_decode($transport->lastRequest['body'], true);
    assertSame(['employeeId' => 'E1', 'fingerType' => 'right_index', 'image' => 'img-b64'], $body);
    verifySig($transport->lastRequest['headers'], $transport->lastRequest['body']);
    assertTrue($result['success'] === true);
});

check('identify envoie uniquement image', function () {
    $transport = new FakeHttpTransport(200, json_encode([
        'success' => true, 'employeeId' => 'E2', 'score' => 55, 'message' => 'ok',
    ]));
    $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);
    $result = $client->identify('img-b64');

    $body = json_decode($transport->lastRequest['body'], true);
    assertSame(['image' => 'img-b64'], $body);
    assertSame('E2', $result['employeeId']);
});

check('verify envoie employeeId et image', function () {
    $transport = new FakeHttpTransport(200, json_encode([
        'success' => true, 'match' => true, 'employeeId' => 'E3', 'score' => 80, 'message' => 'ok',
    ]));
    $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);
    $result = $client->verify('E3', 'img-b64');

    assertSame(BASE_URL . '/verify', $transport->lastRequest['url']);
    assertTrue($result['match'] === true);
});

check('delete envoie uniquement employeeId', function () {
    $transport = new FakeHttpTransport(200, json_encode([
        'success' => true, 'employeeId' => 'E4', 'message' => 'supprimé',
    ]));
    $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);
    $client->delete('E4');

    $body = json_decode($transport->lastRequest['body'], true);
    assertSame(['employeeId' => 'E4'], $body);
});

check('health utilise GET sans signature', function () {
    $transport = new FakeHttpTransport(200, json_encode([
        'status' => 'ok', 'enrolled_employees' => 3, 'service' => 'biometric-api',
    ]));
    $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);
    $result = $client->health();

    assertSame('GET', $transport->lastRequest['method']);
    assertTrue(!isset($transport->lastRequest['headers']['X-Signature']));
    assertSame(3, $result['enrolled_employees']);
});

check('erreur HTTP 401 lève ServerException avec statusCode', function () {
    $transport = new FakeHttpTransport(401, json_encode(['message' => 'Signature invalide.']));
    $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);
    try {
        $client->identify('img');
        throw new \RuntimeException('aucune exception levée');
    } catch (ServerException $e) {
        assertSame(401, $e->statusCode);
    }
});

check('erreur réseau propage NetworkException', function () {
    $transport = new FakeHttpTransport(0, '', new NetworkException('connexion refusée'));
    $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);
    try {
        $client->identify('img');
        throw new \RuntimeException('aucune exception levée');
    } catch (NetworkException $e) {
        // attendu
    }
});

check('JSON invalide lève InvalidResponseException', function () {
    $transport = new FakeHttpTransport(200, 'not json at all');
    $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);
    try {
        $client->identify('img');
        throw new \RuntimeException('aucune exception levée');
    } catch (InvalidResponseException $e) {
        // attendu
    }
});

echo "================================\n";
echo "$passed passés, $failed échoués\n";

exit($failed > 0 ? 1 : 0);
