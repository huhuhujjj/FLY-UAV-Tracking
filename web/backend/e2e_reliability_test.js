"use strict";
const { assert, BASE, openPage, dropFile, submit, waitForSuccess } = require("./e2e_helpers");

openPage("/image-detection.html", async (page) => {
  assert.equal(await page.locator("#interactive-empty").isVisible(), true);
  await dropFile(page, "image.jpg", "image/jpeg");
  const id = await submit(page);
  await waitForSuccess(page);
  await page.waitForSelector(".detection-table tbody tr");
  const expected = await (await page.request.get(BASE + "/api/jobs/" + id + "/detections")).json();
  assert.equal(await page.locator(".detection-table tbody tr").count(), expected.rows.length);
  assert.ok(expected.rows.length > 0);
  const sizes = await page.locator(".download-size").allTextContents();
  assert.ok(sizes.length > 0 && sizes.every((s) => s.trim().length > 0));
  await page.locator("#reset-btn").click();
  assert.equal(await page.locator("#interactive-empty").isVisible(), true);
  // Reset clears the browser view; refreshing restores the server's last job.
  await page.reload({ waitUntil: "networkidle" });
  await waitForSuccess(page);
  assert.match(await page.locator("#result-media img").getAttribute("src"), new RegExp(id));
  console.log("PASS: detection rows, download sizes, reset and refresh recovery");
}).catch((error) => { console.error(error); process.exitCode = 1; });
