// import express from "express";

// const router = express.Router();


// // CPU spike simulation
// router.get("/cpu-spike", (req, res) => {

//   const end = Date.now() + 5000;

//   while (Date.now() < end) {
//     Math.sqrt(Math.random());
//   }

//   res.json({
//     simulation: "cpu-spike",
//     duration: "5 seconds"
//   });
// });


// // Memory leak simulation
// let memoryLeakArray = [];

// router.get("/memory-leak", (req, res) => {

//   for (let i = 0; i < 50000; i++) {
//     memoryLeakArray.push({ data: "x".repeat(1000) });
//   }

//   res.json({
//     simulation: "memory-leak",
//     objects_allocated: memoryLeakArray.length
//   });
// });


// // Latency simulation
// router.get("/latency", async (req, res) => {

//   await new Promise(resolve => setTimeout(resolve, 3000));

//   res.json({
//     simulation: "latency",
//     delay: "3 seconds"
//   });
// });


// // Error storm simulation
// router.get("/error-storm", (req, res) => {

//   if (Math.random() > 0.3) {
//     return res.status(500).json({
//       simulation: "error-storm",
//       error: "simulated failure"
//     });
//   }

//   res.json({
//     simulation: "error-storm",
//     status: "success"
//   });
// });


// export default router;


import express from "express";

const router = express.Router();

/* ===============================
   CPU SPIKE SIMULATION
================================ */

router.get("/cpu-spike", (req, res) => {

  const level = req.query.level || "medium";

  let duration;

  if (level === "low") duration = 2000;
  else if (level === "high") duration = 8000;
  else duration = 5000;

  const end = Date.now() + duration;

  while (Date.now() < end) {
    Math.sqrt(Math.random());
  }

  res.json({
    simulation: "cpu-spike",
    level: level,
    duration_ms: duration
  });

});


/* ===============================
   MEMORY LEAK SIMULATION
================================ */

let memoryLeakArray = [];

router.get("/memory-leak", (req, res) => {

  const level = req.query.level || "medium";

  let allocations;

  if (level === "low") allocations = 20000;
  else if (level === "high") allocations = 100000;
  else allocations = 50000;

  for (let i = 0; i < allocations; i++) {
    memoryLeakArray.push({ data: "x".repeat(1000) });
  }

  res.json({
    simulation: "memory-leak",
    level: level,
    objects_allocated: memoryLeakArray.length
  });

});


/* ===============================
   LATENCY INJECTION
================================ */

router.get("/latency", async (req, res) => {

  const level = req.query.level || "medium";

  let delay;

  if (level === "low") delay = 1000;
  else if (level === "high") delay = 5000;
  else delay = 3000;

  await new Promise(resolve => setTimeout(resolve, delay));

  res.json({
    simulation: "latency",
    level: level,
    delay_ms: delay
  });

});


/* ===============================
   ERROR STORM SIMULATION
================================ */

router.get("/error-storm", (req, res) => {

  const level = req.query.level || "medium";

  let errorProbability;

  if (level === "low") errorProbability = 0.3;
  else if (level === "high") errorProbability = 0.9;
  else errorProbability = 0.6;

  if (Math.random() < errorProbability) {
    return res.status(500).json({
      simulation: "error-storm",
      level: level,
      error: "simulated failure"
    });
  }

  res.json({
    simulation: "error-storm",
    level: level,
    status: "success"
  });

});

export default router;