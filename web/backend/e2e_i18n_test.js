"use strict";
const { assert, pilot, openPage, submit, waitForSuccess } = require("./e2e_helpers");

openPage("/image-detection.html", async (page) => {
  assert.equal((await page.locator("h1").textContent()).trim(), "图片检测");
  await page.locator("#lang-toggle").click();
  assert.equal((await page.locator("h1").textContent()).trim(), "Image Detection");
  await page.locator("#file-input").setInputFiles(pilot("image.jpg"));
  await submit(page);
  await waitForSuccess(page);
  assert.equal((await page.locator("#result-inspector h2").textContent()).trim(), "Detection Results");
  await page.locator("#lang-toggle").click();
  assert.equal((await page.locator("#result-inspector h2").textContent()).trim(), "检测结果");
  await page.reload({ waitUntil: "networkidle" });
  assert.equal((await page.locator("h1").textContent()).trim(), "图片检测");
  console.log("PASS: language toggle updates static/results text and persists");
}).catch((error) => { console.error(error); process.exitCode = 1; });
