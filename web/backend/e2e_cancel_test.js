"use strict";
const { assert, BASE, pilot, openPage, submit } = require("./e2e_helpers");

openPage("/index.html", async (page) => {
  await page.locator("#file-input").setInputFiles(pilot("clip.mp4"));
  const id = await submit(page);
  await page.locator("#cancel-btn").click();
  // Cancellation hides results after the worker returns; it does not stop inference.
  await page.waitForFunction(async (id) => {
    const job = await (await fetch("/api/jobs/" + id)).json();
    return job.status === "INTERRUPTED";
  }, id, { timeout: 300000 });
  const job = await (await page.request.get(BASE + "/api/jobs/" + id)).json();
  assert.deepEqual(job.artifacts, []);
  assert.equal(job.run, null);
  const artifact = await page.request.get(BASE + "/api/artifacts/" + id + "/annotated.mp4");
  assert.equal(artifact.status(), 404);
  console.log("PASS: cancelled task becomes INTERRUPTED and publishes no artifacts");
}).catch((error) => { console.error(error); process.exitCode = 1; });
