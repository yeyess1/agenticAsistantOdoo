// Export the Archify diagrams in docs/diagrams/*.html to light/dark SVG and PNG for the README.
// Uses the viewer's own Export menu (canonical export, no viewer UI) through headless Chrome + CDP.
// Usage: node scripts/export_diagrams.mjs [name ...]   (default: agent-graph; the architecture diagram comes from scripts/diagrams/architecture.py)
import { spawn } from "node:child_process";
import { mkdtempSync, readdirSync, renameSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const DIR = resolve("docs/diagrams");
const NAMES = process.argv.slice(2).length ? process.argv.slice(2) : ["agent-graph"];
const FORMATS = ["svg-light", "svg-dark", "png"];
const CHROME = process.env.CHROME || "google-chrome";
const PORT = 9333;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const profile = mkdtempSync(join(tmpdir(), "archify-export-"));
const chrome = spawn(CHROME, [
  "--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  "--no-first-run", "--window-size=2048,1320", "about:blank",
], { stdio: "ignore" });

async function target() {
  for (let i = 0; i < 50; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch {}
    await sleep(200);
  }
  throw new Error("Chrome did not start");
}

const ws = new WebSocket(await target());
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let seq = 0;
const pending = new Map();
ws.addEventListener("message", (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    const { ok, fail } = pending.get(msg.id);
    pending.delete(msg.id);
    msg.error ? fail(new Error(msg.error.message)) : ok(msg.result);
  }
});
const send = (method, params = {}) =>
  new Promise((ok, fail) => {
    const id = ++seq;
    pending.set(id, { ok, fail });
    ws.send(JSON.stringify({ id, method, params }));
  });
const evaluate = async (expression) =>
  (await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true })).result.value;

const downloads = mkdtempSync(join(tmpdir(), "archify-dl-"));
await send("Page.enable");
await send("Browser.setDownloadBehavior", { behavior: "allow", downloadPath: downloads });

try {
  for (const name of NAMES) {
    await send("Page.navigate", { url: pathToFileURL(join(DIR, `${name}.html`)).href });
    await sleep(2500);
    for (const format of FORMATS) {
      const clicked = await evaluate(
        `(() => { const b = document.querySelector('[data-format="${format}"]'); if (!b) return false; b.click(); return true; })()`,
      );
      if (!clicked) throw new Error(`${name}: export button ${format} not found`);
      const ext = format === "png" ? ".png" : ".svg";
      let file;
      for (let i = 0; i < 100 && !file; i++) {
        await sleep(200);
        file = readdirSync(downloads).find((f) => f.endsWith(ext) && !f.endsWith(".crdownload"));
      }
      if (!file) throw new Error(`${name}: ${format} download timed out`);
      const out = join(DIR, `${name}${format === "png" ? "" : format.replace("svg", "")}${ext}`);
      renameSync(join(downloads, file), out);
      console.log("wrote", out);
    }
  }
} finally {
  ws.close();
  chrome.kill();
  await sleep(300);
  rmSync(profile, { recursive: true, force: true });
  rmSync(downloads, { recursive: true, force: true });
}
