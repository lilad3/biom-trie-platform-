# biometric-client (Java)

SDK officiel Java pour `biometric-api`, à utiliser **côté serveur** (Spring
Boot, Jakarta EE, une application batch...).

**Zéro dépendance de production** : `java.net.http.HttpClient` (JDK
standard depuis Java 11) pour le réseau, un encodeur/décodeur JSON maison
minimal pour les schémas plats échangés avec `biometric-api`. Nécessite
Java 17+.

## Installation (Maven)

```xml
<dependency>
    <groupId>com.biometricplatform</groupId>
    <artifactId>biometric-client</artifactId>
    <version>1.0.0</version>
</dependency>
```

(Publier d'abord dans votre dépôt Maven interne, ou utilisez `mvn install`
en local depuis ce dossier.)

## Usage

```java
import com.biometricplatform.client.BiometricClient;
import com.biometricplatform.client.Results;

BiometricClient client = new BiometricClient(
    "http://localhost:8001",
    System.getenv("BIOMETRIC_SERVICE_TOKEN")
);

Results.IdentifyResult result = client.identify(imageBase64);
if (result.success()) {
    System.out.println("Employé identifié : " + result.employeeId());
}
```

## Gestion des erreurs

```java
import com.biometricplatform.client.BiometricClientException;

try {
    client.identify(imageBase64);
} catch (BiometricClientException.TimeoutException e) {
    // le serveur n'a pas répondu à temps
} catch (BiometricClientException.ServerException e) {
    // e.getStatusCode(), e.getMessage()
} catch (BiometricClientException.NetworkException e) {
    // impossible de contacter le serveur
}
```

## ⚠️ Sécurité

Le jeton d'authentification (`serviceAuthToken`) est un secret serveur. Ce
SDK ne doit jamais être embarqué dans un client lourd exposé à l'utilisateur
final (application desktop distribuée, applet...).

## Tests

Avec Maven + JUnit 5 installés :

```bash
mvn test
```

Sans Maven (validation rapide, zéro dépendance) :

```bash
javac -d target/classes $(find src/main/java -name "*.java")
javac -cp target/classes -d target/test-classes src/test/java/.../FakeHttpTransport.java
javac -cp target/classes:target/test-classes -d target/tools tools/RunTests.java
java -cp target/classes:target/test-classes:target/tools com.biometricplatform.client.tools.RunTests
```

Les deux approches testent exactement les mêmes scénarios ; `RunTests`
existe pour permettre de valider ce SDK même sans accès à Maven Central.
