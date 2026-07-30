<?php

declare(strict_types=1);

namespace BiometricClient\Tests;

use BiometricClient\BiometricClient;
use BiometricClient\ConfigurationException;
use BiometricClient\NetworkException;
use BiometricClient\ServerException;
use BiometricClient\InvalidResponseException;
use PHPUnit\Framework\TestCase;

const TOKEN = 'test-service-token';
const BASE_URL = 'http://localhost:8001';

function verifySignature(TestCase $test, array $headers, string $body, string $token = TOKEN): void
{
    $timestamp = $headers['X-Timestamp'];
    $expected = hash_hmac('sha256', "$timestamp.$body", $token);
    $test->assertSame($expected, $headers['X-Signature']);
}

final class BiometricClientTest extends TestCase
{
    public function testMissingBaseUrlThrows(): void
    {
        $this->expectException(ConfigurationException::class);
        new BiometricClient('', TOKEN);
    }

    public function testMissingTokenThrows(): void
    {
        $this->expectException(ConfigurationException::class);
        new BiometricClient(BASE_URL, '');
    }

    public function testEnrollSendsCorrectPayloadAndSignature(): void
    {
        $transport = new FakeHttpTransport(200, json_encode([
            'success' => true, 'employeeId' => 'E1', 'fingerType' => 'right_index', 'message' => 'ok',
        ]));
        $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);

        $result = $client->enroll('E1', 'right_index', 'img-b64');

        $this->assertSame('POST', $transport->lastRequest['method']);
        $this->assertSame(BASE_URL . '/enroll', $transport->lastRequest['url']);
        $body = json_decode($transport->lastRequest['body'], true);
        $this->assertSame(['employeeId' => 'E1', 'fingerType' => 'right_index', 'image' => 'img-b64'], $body);
        verifySignature($this, $transport->lastRequest['headers'], $transport->lastRequest['body']);
        $this->assertTrue($result['success']);
    }

    public function testIdentifySendsOnlyImage(): void
    {
        $transport = new FakeHttpTransport(200, json_encode([
            'success' => true, 'employeeId' => 'E2', 'score' => 55, 'message' => 'ok',
        ]));
        $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);

        $result = $client->identify('img-b64');

        $body = json_decode($transport->lastRequest['body'], true);
        $this->assertSame(['image' => 'img-b64'], $body);
        $this->assertSame('E2', $result['employeeId']);
    }

    public function testVerifySendsEmployeeIdAndImage(): void
    {
        $transport = new FakeHttpTransport(200, json_encode([
            'success' => true, 'match' => true, 'employeeId' => 'E3', 'score' => 80, 'message' => 'ok',
        ]));
        $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);

        $result = $client->verify('E3', 'img-b64');

        $this->assertSame(BASE_URL . '/verify', $transport->lastRequest['url']);
        $this->assertTrue($result['match']);
    }

    public function testDeleteSendsOnlyEmployeeId(): void
    {
        $transport = new FakeHttpTransport(200, json_encode([
            'success' => true, 'employeeId' => 'E4', 'message' => 'supprimé',
        ]));
        $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);
        $client->delete('E4');

        $body = json_decode($transport->lastRequest['body'], true);
        $this->assertSame(['employeeId' => 'E4'], $body);
    }

    public function testHealthUsesGetWithoutSignature(): void
    {
        $transport = new FakeHttpTransport(200, json_encode([
            'status' => 'ok', 'enrolled_employees' => 3, 'service' => 'biometric-api',
        ]));
        $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);
        $result = $client->health();

        $this->assertSame('GET', $transport->lastRequest['method']);
        $this->assertArrayNotHasKey('X-Signature', $transport->lastRequest['headers']);
        $this->assertSame(3, $result['enrolled_employees']);
    }

    public function testServerErrorThrowsServerException(): void
    {
        $transport = new FakeHttpTransport(401, json_encode(['message' => 'Signature invalide.']));
        $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);

        $this->expectException(ServerException::class);
        $client->identify('img');
    }

    public function testServerErrorPreservesStatusCode(): void
    {
        $transport = new FakeHttpTransport(401, json_encode(['message' => 'Signature invalide.']));
        $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);

        try {
            $client->identify('img');
            $this->fail('ServerException attendue');
        } catch (ServerException $e) {
            $this->assertSame(401, $e->statusCode);
        }
    }

    public function testNetworkErrorPropagates(): void
    {
        $transport = new FakeHttpTransport(0, '', new NetworkException('connexion refusée'));
        $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);

        $this->expectException(NetworkException::class);
        $client->identify('img');
    }

    public function testInvalidJsonThrowsInvalidResponseException(): void
    {
        $transport = new FakeHttpTransport(200, 'not json at all');
        $client = new BiometricClient(BASE_URL, TOKEN, 15.0, $transport);

        $this->expectException(InvalidResponseException::class);
        $client->identify('img');
    }
}
