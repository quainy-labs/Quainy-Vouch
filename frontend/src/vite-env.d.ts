/// <reference types="vite/client" />

import type { Root } from "react-dom/client";

declare global {
  interface Window {
    __quainyVouchRoot?: Root;
  }
}

export {};
