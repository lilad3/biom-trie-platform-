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
