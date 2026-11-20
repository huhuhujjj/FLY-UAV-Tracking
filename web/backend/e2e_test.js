"use strict";
const { assert, pilot, openPage, submit, waitForSuccess, checkArtifact } = require("./e2e_helpers");

(async () => {
  await openPage("/image-detection.html", async (page) => {
    assert.equal(await page.locator("#interactive-empty").isVisible(), true);
    await page.locator("#file-input").setInputFiles(pilot("image.jpg"));
    await submit(page);
    await waitForSuccess(page);
    await checkArtifact(page, "#result-media img", "image/jpeg");
  });
  await openPage("/index.html", async (page) => {
    await page.locator("#file-input").setInputFiles(pilot("clip.mp4"));
    await submit(page);
    await waitForSuccess(page);
    await checkArtifact(page, "#result-media video", "video/mp4");
    assert.match(await page.locator("#result-inspector").textContent(), /帧/);
  });
  console.log("PASS: image and video uploads return non-empty annotated media");
})().catch((error) => { console.error(error); process.exitCode = 1; });
