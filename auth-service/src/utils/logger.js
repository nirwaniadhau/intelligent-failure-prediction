import pino from "pino";

const logger = pino({
  level: "info",
  timestamp: pino.stdTimeFunctions.isoTime,
  base: {
    service: "auth-service"
  }
});

export default logger;