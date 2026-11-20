"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const BASE = process.env.UAV_BASE || "http://127.0.0.1:8765";
const PROJECT = path.resolve(__dirname, "..", "..");
const pilot = (name) => path.join(PROJECT, "model/data/processed/step3_pilot", name);

async function openPage(route, check) {
  const browser = await chromium.launch();
  try {
    // A fixed locale makes text assertions independent of the developer's OS.
    const page = await browser.newPage({ locale: "zh-CN" });
    await page.goto(BASE + route, { waitUntil: "networkidle" });
    await check(page);
  } finally {
    await browser.close();
  }
}

async function dropFile(page, name, mime) {
  const bytes = fs.readFileSync(pilot(name));
  await page.evaluate(({ content, name, mime }) => {
    const file = new File([Uint8Array.from(atob(content), (c) => c.charCodeAt(0))], name, { type: mime });
    const transfer = new DataTransfer();
    transfer.items.add(file);
    const zone = document.querySelector("#job-strip");
    for (const type of ["dragenter", "dragover"]) {
      zone.dispatchEvent(new DragEvent(type, { dataTransfer: transfer, bubbles: true, cancelable: true }));
    }
    window.__dropHighlighted = zone.classList.contains("is-dragover");
    zone.dispatchEvent(new DragEvent("drop", { dataTransfer: transfer, bubbles: true, cancelable: true }));
  }, { content: bytes.toString("base64"), name, mime });
  assert.equal(await page.evaluate(() => window.__dropHighlighted), true);
  assert.equal(await page.locator("#chosen-file .file-name").textContent(), name);
}

async function submit(page) {
  const response = page.waitForResponse((r) => r.url() === BASE + "/api/jobs" && r.request().method() === "POST");
  await page.locator("#submit-btn").click();
  const accepted = await response;
  assert.equal(accepted.status(), 202);
  return (await accepted.json()).job_id;
}

async function waitForSuccess(page) {
  await page.waitForFunction(() => {
    const banner = document.querySelector("#status-banner");
    if (banner.classList.contains("status-banner--failed")) throw new Error(banner.textContent);
    return banner.classList.contains("status-banner--success");
  }, null, { timeout: 300000 });
}

async function checkArtifact(page, selector, contentType) {
  const src = await page.locator(selector).getAttribute("src");
  assert.match(src, /^\/api\/artifacts\//);
  const response = await page.request.get(BASE + src);
  assert.equal(response.status(), 200);
  assert.ok(response.headers()["content-type"].startsWith(contentType));
  assert.ok((await response.body()).length > 0);
  return src;
}

module.exports = { assert, BASE, pilot, openPage, dropFile, submit, waitForSuccess, checkArtifact };
