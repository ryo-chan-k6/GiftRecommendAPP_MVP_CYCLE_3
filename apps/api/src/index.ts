import { createApp } from "./app.js";

const DEFAULT_PORT = 3001;

function resolvePort(): number {
  const raw = process.env.PORT;
  if (raw === undefined || raw.trim() === "") {
    return DEFAULT_PORT;
  }
  const port = Number(raw);
  if (!Number.isInteger(port) || port <= 0) {
    throw new Error(`PORT must be a positive integer, got ${raw}`);
  }
  return port;
}

const port = resolvePort();
const app = createApp();

app.listen(port, () => {
  console.log(`info: api listening on http://localhost:${port}`);
});
