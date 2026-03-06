import logger from "../utils/logger.js";
import { httpRequestDuration, httpErrorCounter, activeRequests } from "../utils/metrics.js";

const requestLogger = (req, res, next) => {

  const start = Date.now();

  activeRequests.inc();

  res.on("finish", () => {

    const latency = Date.now() - start;

    const labels = {
      method: req.method,
      route: req.path,
      status_code: res.statusCode
    };

    logger.info({
      request_id: req.requestId,
      event: "http_request_completed",
      method: req.method,
      endpoint: req.path,
      status_code: res.statusCode,
      latency_ms: latency
    });

    httpRequestDuration.observe(labels, latency);

    if (res.statusCode >= 400) {
      httpErrorCounter.inc(labels);
    }

    activeRequests.dec();
  });

  next();
};

export default requestLogger;