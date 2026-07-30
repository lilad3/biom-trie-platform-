"use strict";

const { BiometricClient } = require("./client");
const errors = require("./errors");

module.exports = {
  BiometricClient,
  ...errors,
};
