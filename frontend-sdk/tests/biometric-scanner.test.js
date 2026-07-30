/**
 * Tests de BiometricScanner. window.Fingerprint est entièrement mocké
 * (pas de vrai lecteur en CI) pour vérifier que la classe encapsule bien
 * le comportement du SDK DigitalPersona sans jamais l'exposer.
 */
const BiometricScanner = require("../src/biometric-scanner.js");

function makeFakeFingerprintApi({ devices = ["device-1"], qualityLabel = "Good", samples = null } = {}) {
  const api = {
    onQualityReported: null,
    onSamplesAcquired: null,
    onErrorOccurred: null,
    onCommunicationFailed: null,
    enumerateDevices: jest.fn().mockResolvedValue(devices),
    startAcquisition: jest.fn().mockImplementation(() => {
      // Simule le comportement asynchrone réel : les événements arrivent
      // après le début de l'acquisition, pas de façon synchrone.
      setTimeout(() => {
        if (api.onQualityReported) {
          api.onQualityReported({ quality: 0 });
        }
        if (api.onSamplesAcquired) {
          const payload = samples !== null ? samples : JSON.stringify(["ZmFrZS1pbWFnZS1kYXRh"]);
          api.onSamplesAcquired({ samples: payload });
        }
      }, 0);
      return Promise.resolve();
    }),
    stopAcquisition: jest.fn().mockResolvedValue(undefined),
  };
  return api;
}

beforeEach(() => {
  global.window = global;
  global.Fingerprint = {
    WebApi: jest.fn().mockImplementation(() => makeFakeFingerprintApi()),
    QualityCode: { 0: "Good", 1: "NoImage", 2: "TooLight" },
    SampleFormat: { PngImage: 5 },
  };
});

afterEach(() => {
  delete global.Fingerprint;
  jest.restoreAllMocks();
});

describe("BiometricScanner.connect", () => {
  test("réussit quand Fingerprint.WebApi est disponible", async () => {
    const scanner = new BiometricScanner();
    await scanner.connect();
    expect(scanner.isConnected).toBe(true);
  });

  test("lève BiometricScannerError si le SDK DigitalPersona est absent", async () => {
    delete global.Fingerprint;
    const scanner = new BiometricScanner();
    await expect(scanner.connect()).rejects.toThrow(BiometricScanner.BiometricScannerError);
    await expect(scanner.connect()).rejects.toMatchObject({ code: "AGENT_NOT_INSTALLED" });
  });

  test("ne recrée pas l'instance API à chaque appel (évite l'emmêlement du lecteur)", async () => {
    const scanner = new BiometricScanner();
    await scanner.connect();
    await scanner.connect();
    expect(global.Fingerprint.WebApi).toHaveBeenCalledTimes(1);
  });
});

describe("BiometricScanner.capture", () => {
  test("retourne une image exploitable pour une capture réussie", async () => {
    const scanner = new BiometricScanner();
    const capture = await scanner.capture();

    expect(capture.image).toMatch(/^data:image\/png;base64,/);
    expect(capture.qualityPercent).toBeGreaterThan(0);
    expect(capture.isGood).toBe(true);
    expect(capture.isAcceptable).toBe(true);
  });

  test("n'expose jamais de code ou d'objet DigitalPersona brut dans le résultat", async () => {
    const scanner = new BiometricScanner();
    const capture = await scanner.capture();

    // Le développeur ne doit voir que des primitives simples et documentées,
    // jamais de référence directe à un concept DigitalPersona (qualityCode,
    // deviceUid, sampleFormat...).
    const keys = Object.keys(capture);
    expect(keys.sort()).toEqual(["image", "isAcceptable", "isGood", "qualityPercent"].sort());
  });

  test("appelle onQuality avec un pourcentage, jamais un code brut", async () => {
    const scanner = new BiometricScanner();
    const onQuality = jest.fn();
    await scanner.capture({ onQuality });

    expect(onQuality).toHaveBeenCalled();
    const arg = onQuality.mock.calls[0][0];
    expect(arg).toHaveProperty("percent");
    expect(arg).toHaveProperty("isGood");
    expect(typeof arg.percent).toBe("number");
  });

  test("rejette avec NO_DEVICE si aucun lecteur n'est branché", async () => {
    global.Fingerprint.WebApi = jest.fn().mockImplementation(() =>
      makeFakeFingerprintApi({ devices: [] })
    );
    const scanner = new BiometricScanner();
    await expect(scanner.capture()).rejects.toMatchObject({ code: "NO_DEVICE" });
  });

  test("connect() implicite si capture() est appelé sans connect() préalable", async () => {
    const scanner = new BiometricScanner();
    expect(scanner.isConnected).toBe(false);
    await scanner.capture();
    expect(scanner.isConnected).toBe(true);
  });

  test("respecte minQualityPercent personnalisé pour isAcceptable", async () => {
    global.Fingerprint.WebApi = jest.fn().mockImplementation(() =>
      makeFakeFingerprintApi({ qualityLabel: "TooLight" })
    );
    global.Fingerprint.QualityCode = { 0: "TooLight" };

    const scanner = new BiometricScanner({ minQualityPercent: 99 });
    const capture = await scanner.capture();
    expect(capture.isAcceptable).toBe(false);
  });
});

describe("BiometricScanner.disconnect", () => {
  test("arrête l'acquisition en cours sans lever d'erreur", async () => {
    const scanner = new BiometricScanner();
    await scanner.connect();
    await expect(scanner.disconnect()).resolves.toBeUndefined();
    expect(scanner.isConnected).toBe(false);
  });
});
