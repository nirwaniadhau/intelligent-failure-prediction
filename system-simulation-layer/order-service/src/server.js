import express from "express";
import { pool, initDB } from "../db/connections.js"
import logger from "./utils/logger.js";
import requestContext from "./middleware/requestContext.js";
import requestLogger from "./middleware/requestLogger.js";
import { register } from "./utils/metrics.js";

const app=express();
app.use(express.json());

app.use(requestContext);
app.use(requestLogger);

app.post("/create-order", async (req, res) => {
  try {
    const { userId, item } = req.body;

    const result = await pool.query(
      "INSERT INTO orders (user_id, item) VALUES ($1, $2) RETURNING *",
      [userId, item]
    );

    

    res.status(201).json({
      message: "Order created",
      order: result.rows[0],
    });
  } catch (err) {
    console.error("Order creation error:", err);
    res.status(500).json({ error: "Internal Server Error" });
  }
});

app.get("/metrics", async (req, res) => {
  res.set("Content-Type", register.contentType);
  res.end(await register.metrics());
});

const PORT = 5000;

app.listen(PORT, async () => {
  await initDB();
  console.log(`Order Service running on port ${PORT}`);
   logger.info({
    event: "service_started",
    port: PORT
  });
});