"use strict";
// Deliberately not a browser rendering / screenshot test. We execute the
// project's browser-facing JS inside jsdom within an offline Docker container.
const { JSDOM, VirtualConsole } = require("jsdom");
const fs = require("node:fs");
const errors = [];
const virtualConsole = new VirtualConsole();
virtualConsole.on("jsdomError", e => errors.push(String(e && e.message || e).slice(0, 200)));
async function main() {
  const source = fs.readFileSync("/work/index.html", "utf8");
  const hasCSS = /<link\b[^>]*href=["']styles\.css["'][^>]*>/i.test(source);
  const hasJS = /<script\b[^>]*src=["']app\.js["'][^>]*>/i.test(source);
  if (!hasCSS || !hasJS) throw Error("index.html debe enlazar styles.css y app.js");
  const dom = await JSDOM.fromFile("/work/index.html", {
    runScripts: "dangerously", resources: "usable", virtualConsole,
  });
  try {
    if (dom.window.document.readyState !== "complete") {
      await Promise.race([
        new Promise(resolve => dom.window.addEventListener("load", resolve, { once: true })),
        new Promise((_, reject) => setTimeout(() => reject(Error("timeout de carga DOM")), 4500)),
      ]);
    }
    const doc = dom.window.document;
    if (!doc.documentElement || !doc.querySelector("main")) {
      throw Error("La página debe tener estructura HTML5 y elemento main");
    }
    if (errors.length) throw Error("Errores DOM/JavaScript: " + errors.join(" | "));
    process.stdout.write(JSON.stringify({
      state: "dom_smoke_verified", title: doc.title,
      main_present: true, script_linked: true, stylesheet_linked: true,
      javascript_loaded: true, rendered_in_real_browser: false,
    }) + "\n");
  } finally {
    dom.window.close();
  }
}
main().catch(e => { console.error(String(e.message || e).slice(0, 500)); process.exitCode = 1; });
