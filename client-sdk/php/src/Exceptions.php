<?php

declare(strict_types=1);

namespace BiometricClient;

/**
 * Hiérarchie d'exceptions du SDK. Le développeur ne voit jamais d'exception
 * cURL/HTTP brute : tout est traduit en exceptions de ce namespace.
 */
class BiometricClientException extends \Exception
{
    public string $code_;
    public ?int $statusCode;

    public function __construct(string $message, string $code = 'CLIENT_ERROR', ?int $statusCode = null)
    {
        parent::__construct($message);
        $this->code_ = $code;
        $this->statusCode = $statusCode;
    }
}

class ConfigurationException extends BiometricClientException
{
    public function __construct(string $message)
    {
        parent::__construct($message, 'CONFIGURATION_ERROR');
    }
}

class NetworkException extends BiometricClientException
{
    public function __construct(string $message = "Impossible de contacter le serveur biométrique.")
    {
        parent::__construct($message, 'NETWORK_ERROR');
    }
}

class TimeoutException extends BiometricClientException
{
    public function __construct(string $message = "Le serveur biométrique n'a pas répondu à temps.")
    {
        parent::__construct($message, 'TIMEOUT');
    }
}

class ServerException extends BiometricClientException
{
    public function __construct(string $message, int $statusCode)
    {
        parent::__construct($message, 'SERVER_ERROR', $statusCode);
    }
}

class InvalidResponseException extends BiometricClientException
{
    public function __construct(string $message = "Réponse du serveur biométrique illisible.")
    {
        parent::__construct($message, 'INVALID_RESPONSE');
    }
}
