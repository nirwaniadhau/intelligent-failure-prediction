import client from "prom-client";

const register = new client.Registry();

client.collectDefaultMetrics({ register });

export const httpRequestDuration = new client.Histogram({
  name: "http_request_duration_ms",
  help: "HTTP request duration in milliseconds",
  labelNames: ["method", "route", "status_code"],
  buckets: [5, 10, 25, 50, 100, 250, 500, 1000, 2000],
  registers: [register]
});

export const httpErrorCounter = new client.Counter({
  name: "http_errors_total",
  help: "Total HTTP errors",
  labelNames: ["route", "status_code"],
  registers: [register]
});

export const activeRequests = new client.Gauge({
  name: "http_active_requests",
  help: "Number of active requests",
  registers: [register]
});

export { register };