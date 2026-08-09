import express from "express";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { serveStatic } from "./static";

const testDirectories: string[] = [];

afterEach(() => {
  for (const directory of testDirectories.splice(0)) {
    fs.rmSync(directory, { force: true, recursive: true });
  }
});

describe("production static fallback", () => {
  it("serves the SPA entry point for nested routes under Express 5", async () => {
    const distPath = fs.mkdtempSync(path.join(os.tmpdir(), "fab-static-"));
    testDirectories.push(distPath);
    fs.writeFileSync(
      path.join(distPath, "index.html"),
      "<!doctype html><title>FAB static acceptance</title>",
      "utf8",
    );
    const app = express();
    serveStatic(app, distPath);
    const server = app.listen(0);

    try {
      const address = server.address();
      if (!address || typeof address === "string") {
        throw new Error("Expected TCP test server address");
      }
      const response = await fetch(
        `http://127.0.0.1:${address.port}/admin/operations`,
      );

      expect(response.status).toBe(200);
      expect(await response.text()).toContain("FAB static acceptance");
    } finally {
      await new Promise<void>((resolve, reject) => {
        server.close((error) => {
          if (error) reject(error);
          else resolve();
        });
      });
    }
  });
});
