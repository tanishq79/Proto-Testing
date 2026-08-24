import type { Express, Request, Response } from "express";
import { request as httpRequest } from "node:http";

const INFERENCE_ORIGIN = process.env.INFERENCE_API_ORIGIN || "http://127.0.0.1:8001";

function proxyInferenceRequest(req: Request, res: Response) {
  const upstream = new URL(`${INFERENCE_ORIGIN}${req.originalUrl}`);
  const headers = { ...req.headers, host: upstream.host };
  const proxy = httpRequest(
    {
      hostname: upstream.hostname,
      port: upstream.port || 80,
      path: `${upstream.pathname}${upstream.search}`,
      method: req.method,
      headers,
    },
    upstreamResponse => {
      res.status(upstreamResponse.statusCode || 502);
      Object.entries(upstreamResponse.headers).forEach(([key, value]) => {
        if (value !== undefined) res.setHeader(key, value);
      });
      upstreamResponse.pipe(res);
    }
  );

  proxy.on("error", () => {
    if (!res.headersSent) {
      res.status(503).json({ detail: "The local retrieval service is unavailable. Start the FastAPI service and try again." });
    }
  });
  req.pipe(proxy);
}

/** Mounts the local FastAPI retrieval service behind the single WebDev origin. */
export function registerInferenceProxy(app: Express) {
  app.use(["/api/health", "/api/search"], proxyInferenceRequest);
}
