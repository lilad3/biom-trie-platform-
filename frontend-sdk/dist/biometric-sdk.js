/*!
 * biometric-platform frontend-sdk
 * Fichier généré automatiquement par build.sh — ne pas éditer directement.
 * Éditer les fichiers sous src/ puis relancer ./build.sh
 */
/**
 * @biometric-platform/frontend-sdk — BiometricScanner
 * =====================================================
 * Encapsule TOTALEMENT le lecteur d'empreintes DigitalPersona
 * (Fingerprint.WebApi, WebSDK, événements bas niveau) derrière une API
 * simple à 3 méthodes : connect(), capture(), disconnect().
 *
 * Le développeur qui utilise ce SDK ne doit JAMAIS avoir besoin de savoir
 * que DigitalPersona existe : pas de Fingerprint.WebApi, pas d'événements
 * onSamplesAcquired/onQualityReported, pas de format PngImage. Si demain
 * la plateforme change de matériel de capture (un autre lecteur, une autre
 * marque), seul le contenu interne de cette classe change — l'API publique
 * (connect/capture/disconnect) reste identique, et aucun code appelant
 * n'a besoin d'être modifié.
 *
 * Usage :
 *   const scanner = new BiometricScanner();
 *   await scanner.connect();
 *   const capture = await scanner.capture();
 *   // capture.image est un base64 PNG prêt à envoyer à BiometricClient.identify()
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.BiometricScanner = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // Table de correspondance qualité -> pourcentage, usage interne uniquement.
  // Le développeur ne manipule jamais les codes de qualité DigitalPersona
  // bruts : il reçoit toujours un pourcentage 0-100 et un booléen isGood.
  const QUALITY_PERCENT_MAP = {
    Good: 92,
    TooLight: 45,
    TooDark: 45,
    TooNoisy: 30,
    LowContrast: 35,
    NoImage: 0,
  };

  function qualityToPercent(label) {
    return QUALITY_PERCENT_MAP.hasOwnProperty(label) ? QUALITY_PERCENT_MAP[label] : 20;
  }

  function toStandardBase64(str) {
    let standard = str.replace(/-/g, "+").replace(/_/g, "/");
    while (standard.length % 4 !== 0) {
      standard += "=";
    }
    return standard;
  }

  class BiometricScannerError extends Error {
    constructor(message, code) {
      super(message);
      this.name = "BiometricScannerError";
      this.code = code || "SCANNER_ERROR";
    }
  }

  class BiometricScanner {
    /**
     * @param {Object} [options]
     * @param {number} [options.minQualityPercent=40] Seuil en-dessous duquel
     *   une capture est considérée inexploitable (capture.isAcceptable = false).
     */
    constructor(options = {}) {
      this._api = null;
      this._connected = false;
      this._minQualityPercent = options.minQualityPercent ?? 40;
    }

    /**
     * Établit la connexion avec l'agent DigitalPersona local. Doit être
     * appelée avant capture(). Lève BiometricScannerError si le SDK/pilote
     * n'est pas installé sur la machine de l'utilisateur.
     * @returns {Promise<void>}
     */
    async connect() {
      const Fingerprint = (typeof window !== "undefined" ? window : global).Fingerprint;

      if (typeof Fingerprint === "undefined" || !Fingerprint.WebApi) {
        throw new BiometricScannerError(
          "Lecteur biométrique non détecté : le pilote/agent local n'est pas installé.",
          "AGENT_NOT_INSTALLED"
        );
      }

      try {
        if (!this._api) {
          this._api = new Fingerprint.WebApi();
        }
        this._connected = true;
      } catch (error) {
        this._api = null;
        this._connected = false;
        throw new BiometricScannerError(
          "Impossible d'initialiser le lecteur biométrique.",
          "INIT_FAILED"
        );
      }
    }

    /**
     * true si connect() a réussi et que le scanner est prêt à capturer.
     */
    get isConnected() {
      return this._connected;
    }

    /**
     * Capture une empreinte sur le lecteur physique et retourne une image
     * prête à l'emploi. Appelle automatiquement connect() si nécessaire.
     *
     * @param {Object} [options]
     * @param {function({percent:number, isGood:boolean})} [options.onQuality]
     *   Callback optionnel appelé en temps réel pendant la capture, pour
     *   afficher un indicateur de qualité à l'utilisateur (ex: barre de
     *   progression). Ne reçoit jamais les codes DigitalPersona bruts.
     * @returns {Promise<{image: string, qualityPercent: number, isGood: boolean, isAcceptable: boolean}>}
     */
    async capture(options = {}) {
      if (!this._connected) {
        await this.connect();
      }

      const api = this._api;
      const root = typeof window !== "undefined" ? window : global;
      const QualityCode = root.Fingerprint && root.Fingerprint.QualityCode;
      const SampleFormat = root.Fingerprint && root.Fingerprint.SampleFormat;
      const minQualityPercent = this._minQualityPercent;

      return new Promise((resolve, reject) => {
        api
          .enumerateDevices()
          .then((devices) => {
            if (!devices || devices.length === 0) {
              reject(
                new BiometricScannerError(
                  "Aucun lecteur d'empreinte détecté. Vérifiez le branchement USB.",
                  "NO_DEVICE"
                )
              );
              return;
            }

            let lastQualityLabel = null;

            api.onQualityReported = (event) => {
              lastQualityLabel = QualityCode ? QualityCode[event.quality] : String(event.quality);
              const percent = qualityToPercent(lastQualityLabel);

              if (typeof options.onQuality === "function") {
                options.onQuality({
                  percent,
                  isGood: percent >= 90,
                });
              }
            };

            api.onSamplesAcquired = (event) => {
              let raw = event.samples;
              if (typeof raw === "string") {
                try {
                  raw = JSON.parse(raw);
                } catch (e) {
                  /* raw reste une chaîne brute */
                }
              }

              let image = null;
              if (Array.isArray(raw) && raw.length > 0) {
                image = "data:image/png;base64," + toStandardBase64(raw[0]);
              } else if (typeof raw === "string" && raw.length > 0) {
                image = "data:image/png;base64," + toStandardBase64(raw);
              }

              const qualityPercent = qualityToPercent(lastQualityLabel);

              api.stopAcquisition().catch(() => {});

              if (!image) {
                reject(
                  new BiometricScannerError(
                    "La capture n'a produit aucune image exploitable.",
                    "EMPTY_CAPTURE"
                  )
                );
                return;
              }

              resolve({
                image,
                qualityPercent,
                isGood: qualityPercent >= 90,
                isAcceptable: qualityPercent >= minQualityPercent,
              });
            };

            api.onErrorOccurred = (event) => {
              reject(
                new BiometricScannerError(
                  "Erreur du lecteur : " + (event.error || "inconnue"),
                  "DEVICE_ERROR"
                )
              );
            };

            api.onCommunicationFailed = () => {
              this._connected = false;
              reject(
                new BiometricScannerError(
                  "Communication avec l'agent biométrique local perdue.",
                  "COMMUNICATION_FAILED"
                )
              );
            };

            const format = SampleFormat ? SampleFormat.PngImage : undefined;
            api.startAcquisition(format).catch(reject);
          })
          .catch(() =>
            reject(
              new BiometricScannerError(
                "Impossible d'énumérer les lecteurs disponibles.",
                "ENUMERATE_FAILED"
              )
            )
          );
      });
    }

    /**
     * Arrête proprement toute acquisition en cours. À appeler si l'utilisateur
     * annule une capture avant qu'elle ne se termine (ex: fermeture d'un modal).
     */
    async disconnect() {
      if (this._api) {
        try {
          await this._api.stopAcquisition();
        } catch (e) {
          /* déjà arrêté, sans conséquence */
        }
      }
      this._connected = false;
    }
  }

  BiometricScanner.BiometricScannerError = BiometricScannerError;
  return BiometricScanner;
});

/**
 * @biometric-platform/frontend-sdk — BiometricClient
 * =====================================================
 * Encapsule TOTALEMENT les appels HTTP vers biometric-api. Le développeur
 * n'écrit jamais de fetch(), ne construit jamais d'URL, ne gère jamais les
 * headers de signature : il appelle client.enroll(...), client.identify(...),
 * client.verify(...), client.delete(...).
 *
 * IMPORTANT — sécurité : ce client ne porte JAMAIS le secret d'authentification
 * inter-services (SERVICE_AUTH_TOKEN). Ce jeton reste côté serveur (dans
 * l'application hôte : Django, Laravel...), qui signe la requête HMAC avant
 * de la relayer. Ce SDK frontend appelle donc en pratique un endpoint proxy
 * de l'application hôte (ex: /api/biometrie/identify côté Django), jamais
 * directement biometric-api : aucune clé ne doit jamais apparaître dans le
 * JavaScript exécuté dans le navigateur (exigence explicite du cahier des
 * charges : "Aucune API Key visible dans le JavaScript").
 *
 * Usage :
 *   const client = new BiometricClient({ baseUrl: "/api/biometrie" });
 *   const result = await client.identify(capture.image);
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.BiometricClient = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  class BiometricClientError extends Error {
    constructor(message, code, status) {
      super(message);
      this.name = "BiometricClientError";
      this.code = code || "CLIENT_ERROR";
      this.status = status || null;
    }
  }

  class BiometricClient {
    /**
     * @param {Object} options
     * @param {string} options.baseUrl Base de l'API proxy côté application
     *   hôte (PAS l'URL directe de biometric-api). Ex: "/api/biometrie".
     * @param {Object} [options.headers] En-têtes additionnels à joindre à
     *   chaque requête (ex: en-tête CSRF requis par Django).
     * @param {number} [options.timeoutMs=15000]
     */
    constructor(options = {}) {
      if (!options.baseUrl) {
        throw new BiometricClientError(
          "baseUrl est requis pour initialiser BiometricClient.",
          "MISSING_BASE_URL"
        );
      }
      this._baseUrl = options.baseUrl.replace(/\/+$/, "");
      this._headers = options.headers || {};
      this._timeoutMs = options.timeoutMs || 15000;
    }

    async _post(path, body) {
      const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
      const timeout = controller
        ? setTimeout(() => controller.abort(), this._timeoutMs)
        : null;

      let response;
      try {
        response = await fetch(this._baseUrl + path, {
          method: "POST",
          headers: Object.assign(
            { "Content-Type": "application/json" },
            this._headers
          ),
          body: JSON.stringify(body),
          signal: controller ? controller.signal : undefined,
        });
      } catch (error) {
        if (error && error.name === "AbortError") {
          throw new BiometricClientError(
            "Le serveur biométrique n'a pas répondu à temps.",
            "TIMEOUT"
          );
        }
        throw new BiometricClientError(
          "Impossible de contacter le serveur biométrique.",
          "NETWORK_ERROR"
        );
      } finally {
        if (timeout) clearTimeout(timeout);
      }

      let data;
      try {
        data = await response.json();
      } catch (error) {
        throw new BiometricClientError(
          "Réponse du serveur biométrique illisible.",
          "INVALID_RESPONSE",
          response.status
        );
      }

      if (!response.ok) {
        throw new BiometricClientError(
          (data && data.message) || "Erreur du serveur biométrique.",
          "SERVER_ERROR",
          response.status
        );
      }

      return data;
    }

    /**
     * Enregistre une nouvelle empreinte pour un employé.
     * @param {string} employeeId
     * @param {string} fingerType ex: "right_index"
     * @param {string} image base64 (data URL ou brut), tel que retourné par BiometricScanner.capture()
     * @returns {Promise<{success:boolean, employeeId:string, fingerType:string, message:string}>}
     */
    async enroll(employeeId, fingerType, image) {
      return this._post("/enroll", { employeeId, fingerType, image });
    }

    /**
     * Identification 1:N — retrouve l'employé correspondant à l'image parmi
     * tous les employés enrôlés.
     * @param {string} image
     * @returns {Promise<{success:boolean, employeeId?:string, score?:number, message:string}>}
     */
    async identify(image) {
      return this._post("/identify", { image });
    }

    /**
     * Vérification 1:1 — confirme (ou non) qu'une image correspond bien à
     * l'employé donné.
     * @param {string} employeeId
     * @param {string} image
     * @returns {Promise<{success:boolean, match:boolean, employeeId:string, score?:number, message:string}>}
     */
    async verify(employeeId, image) {
      return this._post("/verify", { employeeId, image });
    }

    /**
     * Supprime définitivement toutes les empreintes d'un employé.
     * @param {string} employeeId
     * @returns {Promise<{success:boolean, employeeId:string, message:string}>}
     */
    async delete(employeeId) {
      return this._post("/delete", { employeeId });
    }
  }

  BiometricClient.BiometricClientError = BiometricClientError;
  return BiometricClient;
});
