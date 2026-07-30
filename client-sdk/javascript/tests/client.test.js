"use strict";

const crypto = require("crypto");
const { BiometricClient } = require("../src/client");
const {
  ConfigurationError,
  NetworkError,
  ServerError,
  InvalidResponseError,
} = require("../src/errors");

const BASE_URL = "http://localhost:8001";
const TOKEN = "test-service-token";

function mockFetchOnce(status, body) {
  global.fetch = jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

function verifySignature(headers, bodyBuffer, token = TOKEN) {
  const timestamp = headers["X-Timestamp"];
  const signature = headers["X-Signature"];
  const message = Buffer.concat([Buffer.from(`${timestamp}.`, "utf-8"), bodyBuffer]);
  const expected = crypto.createHmac("sha256", token).update(message).digest("hex");
  expect(signature).toBe(expected);
}

afterEach(() => {
  jest.restoreAllMocks();
  delete global.fetch;
});

describe("BiometricClient configuration", () => {
  test("lève ConfigurationError si baseUrl manquant", () => {
    expect(() => new BiometricClient({ serviceAuthToken: TOKEN })).toThrow(ConfigurationError);
  });

  test("lève ConfigurationError si serviceAuthToken manquant", () => {
    expect(() => new BiometricClient({ baseUrl: BASE_URL })).toThrow(ConfigurationError);
  });

  test("retire les slashs de fin de baseUrl", async () => {
    mockFetchOnce(200, { success: true, employeeId: "E1", score: 1, message: "ok" });
    const client = new BiometricClient({ baseUrl: BASE_URL + "///", serviceAuthToken: TOKEN });
    await client.identify("img");
    expect(global.fetch.mock.calls[0][0]).toBe(BASE_URL + "/identify");
  });
});

describe("BiometricClient.enroll", () => {
  test("envoie POST /enroll avec le bon corps et une signature valide", async () => {
    mockFetchOnce(200, { success: true, employeeId: "E1", fingerType: "right_index", message: "ok" });
    const client = new BiometricClient({ baseUrl: BASE_URL, serviceAuthToken: TOKEN });

    const result = await client.enroll("E1", "right_index", "img-b64");

    const [url, init] = global.fetch.mock.calls[0];
    expect(url).toBe(`${BASE_URL}/enroll`);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body.toString())).toEqual({
      employeeId: "E1",
      fingerType: "right_index",
      image: "img-b64",
    });
    verifySignature(init.headers, init.body);
    expect(result.employeeId).toBe("E1");
  });
});

describe("BiometricClient.identify / verify / delete", () => {
  test("identify envoie uniquement image", async () => {
    mockFetchOnce(200, { success: true, employeeId: "E2", score: 60, message: "ok" });
    const client = new BiometricClient({ baseUrl: BASE_URL, serviceAuthToken: TOKEN });
    const result = await client.identify("img-b64");

    const [, init] = global.fetch.mock.calls[0];
    expect(JSON.parse(init.body.toString())).toEqual({ image: "img-b64" });
    expect(result.employeeId).toBe("E2");
  });

  test("verify envoie employeeId et image", async () => {
    mockFetchOnce(200, { success: true, match: true, employeeId: "E3", score: 80, message: "ok" });
    const client = new BiometricClient({ baseUrl: BASE_URL, serviceAuthToken: TOKEN });
    const result = await client.verify("E3", "img-b64");

    const [url, init] = global.fetch.mock.calls[0];
    expect(url).toBe(`${BASE_URL}/verify`);
    expect(JSON.parse(init.body.toString())).toEqual({ employeeId: "E3", image: "img-b64" });
    expect(result.match).toBe(true);
  });

  test("delete envoie uniquement employeeId", async () => {
    mockFetchOnce(200, { success: true, employeeId: "E4", message: "supprimé" });
    const client = new BiometricClient({ baseUrl: BASE_URL, serviceAuthToken: TOKEN });
    await client.delete("E4");

    const [url, init] = global.fetch.mock.calls[0];
    expect(url).toBe(`${BASE_URL}/delete`);
    expect(JSON.parse(init.body.toString())).toEqual({ employeeId: "E4" });
  });
});

describe("BiometricClient.health", () => {
  test("appelle GET /health sans signature", async () => {
    mockFetchOnce(200, { status: "ok", enrolled_employees: 3, service: "biometric-api" });
    const client = new BiometricClient({ baseUrl: BASE_URL, serviceAuthToken: TOKEN });
    const result = await client.health();

    const [url, init] = global.fetch.mock.calls[0];
    expect(url).toBe(`${BASE_URL}/health`);
    expect(init.method).toBe("GET");
    expect(init.headers["X-Signature"]).toBeUndefined();
    expect(result.enrolled_employees).toBe(3);
  });
});

describe("BiometricClient gestion d'erreurs", () => {
  test("lève ServerError sur réponse HTTP non-ok", async () => {
    mockFetchOnce(401, { message: "Signature invalide." });
    const client = new BiometricClient({ baseUrl: BASE_URL, serviceAuthToken: TOKEN });

    await expect(client.identify("img")).rejects.toThrow(ServerError);
    await expect(client.identify("img")).rejects.toMatchObject({ statusCode: 401 });
  });

  test("lève NetworkError si fetch échoue", async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error("network down"));
    const client = new BiometricClient({ baseUrl: BASE_URL, serviceAuthToken: TOKEN });

    await expect(client.identify("img")).rejects.toThrow(NetworkError);
  });

  test("lève InvalidResponseError si le corps n'est pas du JSON", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => {
        throw new Error("not json");
      },
    });
    const client = new BiometricClient({ baseUrl: BASE_URL, serviceAuthToken: TOKEN });

    await expect(client.identify("img")).rejects.toThrow(InvalidResponseError);
  });
});
