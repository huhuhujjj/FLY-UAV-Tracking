"use strict";
const { assert, BASE, openPage } = require("./e2e_helpers");

openPage("/workspace.html", async (page) => {
  assert.equal(await page.locator(".hub-card").count(), 2);
  await page.locator(".hub-card").nth(0).click();
  assert.equal(page.url(), BASE + "/image-detection.html");
  assert.equal(await page.locator('.picker-card[data-type="video"]').isVisible(), false);
  await page.goto(BASE + "/workspace.html");
  await page.locator(".hub-card").nth(1).click();
  assert.equal(page.url(), BASE + "/index.html");
  assert.equal(await page.locator('.picker-card[data-type="image"]').isVisible(), false);
  await page.locator("#lang-toggle").click();
  assert.equal((await page.locator("h1").textContent()).trim(), "Video Tracking");
  console.log("PASS: workspace links to the two fixed media-type pages");
}).catch((error) => { console.error(error); process.exitCode = 1; });
