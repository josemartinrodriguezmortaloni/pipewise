/* eslint-disable @typescript-eslint/ban-ts-comment */

export async function register() {
  // Polyfill for 'self' in different environments
  try {
    // @ts-ignore
    if (
      typeof globalThis !== "undefined" &&
      typeof globalThis.self === "undefined"
    ) {
      (globalThis as any).self = globalThis;
    }
  } catch (e) {
    // Fallback for environments where globalThis is not available
  }

  try {
    // @ts-ignore
    if (
      typeof global !== "undefined" &&
      typeof (global as any).self === "undefined"
    ) {
      (global as any).self = global;
    }
  } catch (e) {
    // Fallback for environments where global is not available
  }

  // A more robust window object mock for SSR
  try {
    // @ts-ignore
    if (typeof window === "undefined" && typeof globalThis !== "undefined") {
      (globalThis as any).window = {
        ...globalThis,
        addEventListener: () => {},
        removeEventListener: () => {},
        location: {
          protocol: "http:",
          host: "localhost",
          hostname: "localhost",
          port: "3000",
          pathname: "/",
          search: "",
          hash: "",
          href: "http://localhost:3000/",
        },
        matchMedia: () => ({
          matches: false,
          media: "",
          onchange: null,
          addListener: () => {},
          removeListener: () => {},
          addEventListener: () => {},
          removeEventListener: () => {},
          dispatchEvent: () => false,
        }),
        document: {
          createElement: () => ({
            style: {},
            setAttribute: () => {},
            getAttribute: () => null,
            appendChild: () => {},
            removeChild: () => {},
            addEventListener: () => {},
            removeEventListener: () => {},
          }),
          createTextNode: () => ({}),
          head: { appendChild: () => {}, removeChild: () => {} },
          body: { appendChild: () => {}, removeChild: () => {} },
          addEventListener: () => {},
          removeEventListener: () => {},
          querySelector: () => null,
          querySelectorAll: () => [],
          getElementById: () => null,
        },
      };
    }
  } catch (e) {
    // Ignore errors in case of read-only global properties
  }

  // Initialize error monitoring
  if (process.env.NODE_ENV === "production") {
    // In production, we could initialize PostHog or other monitoring here
    console.log("Error monitoring initialized for production");
  }
}

export const onRequestError = async (
  err: Error,
  request: Request,
  context: any
) => {
  // Capture and categorize request errors
  const errorInfo = {
    message: err.message,
    stack: err.stack,
    url: request.url,
    method: request.method,
    userAgent: request.headers.get("user-agent"),
    timestamp: new Date().toISOString(),
    context: context || {},
  };

  // Categorize error types
  const errorType = categorizeRequestError(err);

  console.error("Request Error:", {
    ...errorInfo,
    errorType,
  });

  // In production, send to monitoring service
  if (process.env.NODE_ENV === "production") {
    // Example: await sendToMonitoringService(errorInfo);
  }

  // Log specific AI SDK streaming errors
  if (errorType === "ai_stream_error") {
    console.warn("AI Streaming Error - This may be recoverable:", err.message);
  }
};

function categorizeRequestError(error: Error): string {
  const message = error.message || error.toString();

  if (message.includes("stream") || message.includes("AI"))
    return "ai_stream_error";
  if (message.includes("fetch") || message.includes("network"))
    return "network_error";
  if (message.includes("timeout")) return "timeout_error";
  if (message.includes("parse") || message.includes("JSON"))
    return "parse_error";
  if (message.includes("auth") || message.includes("unauthorized"))
    return "auth_error";

  return "unknown_error";
}
