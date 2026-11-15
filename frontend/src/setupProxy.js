const { createProxyMiddleware } = require("http-proxy-middleware");

// The home page, /healthz and the API are served by the backend so the host decides the city.
const SERVER_PAGES = ["/", "/healthz", "/privacy", "/terms"];
const toBackend = (pathname) => SERVER_PAGES.includes(pathname) || pathname.startsWith("/api");

module.exports = function setupProxy(app) {
  app.use(
    createProxyMiddleware(toBackend, {
      target: "http://localhost:8001",
      changeOrigin: false,
      logLevel: "warn",
    }),
  );
};
