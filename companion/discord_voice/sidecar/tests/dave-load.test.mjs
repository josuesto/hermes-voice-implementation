import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { generateDependencyReport } from "@discordjs/voice";

const require = createRequire(import.meta.url);

test("DAVE and Opus load without logging into Discord", () => {
  const davey = require("@snazzah/davey");
  const opus = require("opusscript");
  assert.ok(davey);
  assert.ok(opus);
  const report = generateDependencyReport();
  assert.match(report, /davey/i);
  assert.match(report, /opus/i);
  assert.doesNotMatch(report, /token/i);
});
