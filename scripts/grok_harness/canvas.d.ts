// Development-only documented subset; not the native Grok SDK or compiler.
declare module "grok/canvas" {
  export { useState } from "react";
  export type { CSSProperties, PointerEvent, ChangeEvent } from "react";
  export function Page(props: { title: string; width: "column"; children: import("react").ReactNode }): import("react").ReactNode;
  export function Section(props: { children: import("react").ReactNode }): import("react").ReactNode;
  export function useGrokTheme(): {
    kind: "light" | "dark";
    bg: { base: string };
    font: { family: string };
    motion: { hover: string; easing: string };
  };
}
