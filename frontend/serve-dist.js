// -*- coding: utf-8 -*-
// 零依赖静态服务器：serve dist/hws 于 /openjiuwen/，代理 /v1 /v2 到 manager 31111。
// 用于绕过 ng serve 的 esbuild service 崩溃（ng build 产物正常，serve 崩）。
const http = require("http");
const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "dist", "hws");
const PORT = 4200;
const MANAGER = { host: "127.0.0.1", port: 31111 };
const MIME = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".gif": "image/gif",
  ".ico": "image/x-icon", ".woff": "font/woff", ".woff2": "font/woff2", ".ttf": "font/ttf",
  ".eot": "application/vnd.ms-fontobject", ".map": "application/json", ".txt": "text/plain",
};

function proxy(req, res) {
  const opts = { host: MANAGER.host, port: MANAGER.port, method: req.method,
    path: req.url, headers: { ...req.headers, host: `${MANAGER.host}:${MANAGER.port}` } };
  const up = http.request(opts, (upRes) => {
    res.writeHead(upRes.statusCode, upRes.headers);
    upRes.pipe(res);
  });
  up.on("error", (e) => { res.writeHead(502); res.end("proxy error: " + e.message); });
  req.pipe(up);
}

const server = http.createServer((req, res) => {
  const url = req.url.split("?")[0];
  // API 代理
  if (url === "/v1" || url.startsWith("/v1/") || url === "/v2" || url.startsWith("/v2/")) {
    return proxy(req, res);
  }
  // 根路径 → /openjiuwen/
  if (url === "/" || url === "") {
    res.writeHead(302, { Location: "/openjiuwen/" });
    return res.end();
  }
  // /openjiuwen/* → dist/hws/*
  const rel = url.replace(/^\/openjiuwen\//, "");
  let fp = path.join(ROOT, rel);
  // 防目录穿越
  if (!fp.startsWith(ROOT)) { res.writeHead(403); return res.end("forbidden"); }
  fs.stat(fp, (err, st) => {
    if (!err && st.isFile()) {
      const ext = path.extname(fp).toLowerCase();
      res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
      fs.createReadStream(fp).pipe(res);
      return;
    }
    // 目录或不存在 → 返回 index.html（SPA fallback，hash 路由）
    const idx = path.join(ROOT, "index.html");
    fs.stat(idx, (e2, st2) => {
      if (e2 || !st2.isFile()) { res.writeHead(404); return res.end("index.html not found"); }
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      fs.createReadStream(idx).pipe(res);
    });
  });
});
server.listen(PORT, "0.0.0.0", () => {
  console.log(`static server on http://0.0.0.0:${PORT}/openjiuwen/ -> ${ROOT}`);
  console.log(`proxy /v1,/v2 -> ${MANAGER.host}:${MANAGER.port}`);
});
