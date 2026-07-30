/**
 * Tests de BiometricClient. fetch est entièrement mocké : ces tests
 * vérifient le contrat HTTP (endpoints, méthode, gestion d'erreurs) sans
 * dépendre d'un vrai serveur biometric-api.
 */
const BiometricClient = require("../src/biometric-client.js");

function mockFetchOnce(status, body) {
  global.fetch = jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

afterEach(() => {
  jest.restoreAllMocks();
  delete global.fetch;
});

describe("BiometricClient construction", () => {
  test("lève une erreur si baseUrl est manquant", () => {
    expect(() => new BiometricClient({})).toThrow(BiometricClient.BiometricClientError);
  });

  test("retire les slashs de fin de baseUrl", async () => {
    mockFetchOnce(200, { success: true, employeeId: "E1", score: 42, message: "ok" });
    const client = new BiometricClient({ baseUrl: "/api/biometrie///" });
    await client.identify("img");
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/biometrie/identify",
      expect.anything()
    );
  });
});

describe("BiometricClient.identify", () => {
  test("appelle POST {baseUrl}/identify avec le bon corps JSON", async () => {
    mockFetchOnce(200, { success: true, employeeId: "EMP1", score: 55, message: "ok" });
    const client = new BiometricClient({ baseUrl: "/api/biometrie" });

    const result = await client.identify("base64-image");

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [url, init] = global.fetch.mock.calls[0];
    expect(url).toBe("/api/biometrie/identify");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ image: "base64-image" });
    expect(result.employeeId).toBe("EMP1");
  });

  test("n'expose jamais de méthode fetch/XHR brute au développeur", () => {
    const client = new BiometricClient({ baseUrl: "/api" });
    expect(client.fetch).toBeUndefined();
    expect(client._post).toBeInstanceOf(Function); // interne, non documenté comme API publique
  });
});

describe("BiometricClient.enroll / verify / delete", () => {
  test("enroll envoie employeeId, fingerType, image", async () => {
    mockFetchOnce(200, { success: true, employeeId: "E1", fingerType: "right_index", message: "ok" });
    const client = new BiometricClient({ baseUrl: "/api/biometrie" });
    await client.enroll("E1", "right_index", "img-b64");

    const [url, init] = global.fetch.mock.calls[0];
    expect(url).toBe("/api/biometrie/enroll");
    expect(JSON.parse(init.body)).toEqual({
      employeeId: "E1",
      fingerType: "right_index",
      image: "img-b64",
    });
  });

  test("verify envoie employeeId et image vers /verify", async () => {
    mockFetchOnce(200, { success: true, match: true, employeeId: "E1", score: 80, message: "ok" });
    const client = new BiometricClient({ baseUrl: "/api/biometrie" });
    const result = await client.verify("E1", "img-b64");

    expect(global.fetch.mock.calls[0][0]).toBe("/api/biometrie/verify");
    expect(result.match).toBe(true);
  });

  test("delete envoie employeeId vers /delete", async () => {
    mockFetchOnce(200, { success: true, employeeId: "E1", message: "supprimé" });
    const client = new BiometricClient({ baseUrl: "/api/biometrie" });
    await client.delete("E1");

    expect(global.fetch.mock.calls[0][0]).toBe("/api/biometrie/delete");
    expect(JSON.parse(global.fetch.mock.calls[0][1].body)).toEqual({ employeeId: "E1" });
  });
});

describe("BiometricClient gestion d'erreurs", () => {
  test("lève BiometricClientError si le serveur répond une erreur HTTP", async () => {
    mockFetchOnce(401, { message: "Signature invalide." });
    const client = new BiometricClient({ baseUrl: "/api/biometrie" });

    await expect(client.identify("img")).rejects.toThrow(BiometricClient.BiometricClientError);
    await expect(client.identify("img")).rejects.toMatchObject({
      code: "SERVER_ERROR",
      status: 401,
    });
  });

  test("lève NETWORK_ERROR si fetch échoue (réseau coupé)", async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error("network down"));
    const client = new BiometricClient({ baseUrl: "/api/biometrie" });

    await expect(client.identify("img")).rejects.toMatchObject({ code: "NETWORK_ERROR" });
  });

  test("lève INVALID_RESPONSE si le corps n'est pas du JSON valide", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => {
        throw new Error("not json");
      },
    });
    const client = new BiometricClient({ baseUrl: "/api/biometrie" });

    await expect(client.identify("img")).rejects.toMatchObject({ code: "INVALID_RESPONSE" });
  });
});

describe("BiometricClient en-têtes personnalisés", () => {
  test("fusionne les headers fournis (ex: CSRF Django) avec Content-Type", async () => {
    mockFetchOnce(200, { success: true, message: "ok" });
    const client = new BiometricClient({
      baseUrl: "/api/biometrie",
      headers: { "X-CSRFToken": "abc123" },
    });
    await client.identify("img");

    const [, init] = global.fetch.mock.calls[0];
    expect(init.headers).toMatchObject({
      "Content-Type": "application/json",
      "X-CSRFToken": "abc123",
    });
  });
});
