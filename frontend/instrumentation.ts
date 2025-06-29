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
}
