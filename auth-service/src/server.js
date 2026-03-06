import express from "express";
import logger from "./utils/logger.js";
import requestLogger from "./middleware/requestLogger.js";
import { register } from "./utils/metrics.js";

const app = express();
app.use(requestLogger);

app.get("/validate", (req, res) => {
  res.json({
    valid: true,
    userId: "123"
  });
});

app.get("/metrics", async (req, res) => {
  res.set("Content-Type", register.contentType);
  res.end(await register.metrics());
});

const PORT = 4000;

app.listen(PORT, () => {
  console.log(`Auth Service running on port ${PORT}`);
   logger.info({
    event: "service_started",
    port: PORT
  });
});