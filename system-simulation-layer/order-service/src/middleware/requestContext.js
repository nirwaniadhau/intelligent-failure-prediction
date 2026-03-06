import { v4 as uuidv4 } from "uuid";

const requestContext = (req, res, next) => {

  const requestId = uuidv4();

  req.requestId = requestId;

  res.setHeader("x-request-id", requestId);

  next();
};

export default requestContext;