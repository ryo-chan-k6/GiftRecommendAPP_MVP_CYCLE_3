/**
 * スタイルガイド用の最小静的サーバー（開発プレビュー専用）
 */
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { dirname, extname, join } from "node:path";
import { fileURLToPath } from "node:url";

const previewDir = dirname(fileURLToPath(import.meta.url));
const port = Number(process.env.PORT ?? 3099);

const contentTypes = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
};

createServer(async (req, res) => {
  const pathname = req.url?.split("?")[0] ?? "/";
  const relativePath = pathname === "/" ? "/style-guide.html" : pathname;
  const filePath = join(previewDir, relativePath);

  if (!filePath.startsWith(previewDir)) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }

  try {
    const body = await readFile(filePath);
    res.writeHead(200, {
      "Content-Type": contentTypes[extname(filePath)] ?? "text/plain",
    });
    res.end(body);
  } catch {
    res.writeHead(404);
    res.end("Not found");
  }
}).listen(port, () => {
  console.log(`Style guide: http://localhost:${port}/style-guide.html`);
});
