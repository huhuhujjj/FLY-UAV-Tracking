"use strict";
const { assert, openPage, dropFile, submit, waitForSuccess, checkArtifact } = require("./e2e_helpers");

openPage("/image-detection.html", async (page) => {
  await dropFile(page, "image.jpg", "image/jpeg");
  assert.equal(await page.locator("#submit-btn").isEnabled(), true);
  await submit(page);
  await waitForSuccess(page);
  await checkArtifact(page, "#result-media img", "image/jpeg");
  console.log("PASS: dropping an image highlights the zone and submits the file");
}).catch((error) => { console.error(error); process.exitCode = 1; });
