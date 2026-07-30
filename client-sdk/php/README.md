# biometric-client (PHP)

SDK officiel PHP pour `biometric-api`, à utiliser **côté serveur** (Laravel,
Symfony, PHP natif...).

## Installation

```bash
composer require biometric-platform/biometric-client
```

Ou en local (avant publication sur Packagist), ajoutez dans `composer.json` :

```json
"repositories": [{ "type": "path", "url": "chemin/vers/client-sdk/php" }]
```

## Usage

```php
use BiometricClient\BiometricClient;

$client = new BiometricClient('http://localhost:8001', getenv('BIOMETRIC_SERVICE_TOKEN'));

$result = $client->identify($imageBase64);
if ($result['success']) {
    echo "Employé identifié : " . $result['employeeId'];
}
```

## Gestion des erreurs

```php
use BiometricClient\{NetworkException, ServerException, TimeoutException};

try {
    $client->identify($imageBase64);
} catch (TimeoutException $e) {
    // le serveur n'a pas répondu à temps
} catch (ServerException $e) {
    // $e->statusCode, $e->getMessage()
} catch (NetworkException $e) {
    // impossible de contacter le serveur
}
```

## ⚠️ Sécurité

Le jeton d'authentification (`serviceAuthToken`) est un secret serveur.
N'utilisez jamais ce SDK dans du code exposé côté client.

## Tests

Avec Composer + PHPUnit installés :

```bash
composer install
vendor/bin/phpunit tests/
```

Sans Composer (validation rapide, sans dépendance) :

```bash
php tests/run-tests.php
```

Les deux fichiers testent exactement les mêmes scénarios ; `run-tests.php`
existe pour permettre de valider ce SDK même sans accès à Packagist.
