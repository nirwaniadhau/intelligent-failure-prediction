import pkg from "pg";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const { Pool } = pkg;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const pool = new Pool({
  user: "postgres",
  host: "localhost",
  database: "failsight_db",
  password: "Nirwani_29",
  port: 5432,
});

const initDB = async () => {
  try {
    const schema = fs.readFileSync(
      path.join(__dirname, "init.sql"),
      "utf-8"
    );
    await pool.query(schema);
    console.log("Database initialized");
  } catch (err) {
    console.error("DB initialization error:", err);
  }
};

export { pool, initDB };