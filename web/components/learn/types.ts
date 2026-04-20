/** Shared types for the Variant D learn page components. */

export type AnnotationLayer = "guidance" | "evasion" | "sentiment" | "terms";

export type AnnotationLayers = Record<AnnotationLayer, boolean>;

export const DEFAULT_LAYERS: AnnotationLayers = {
  guidance: true,
  evasion: true,
  sentiment: true,
  terms: true,
};

export interface ChatContext {
  type: "evasion" | "term" | "guidance";
  text: string;
  metadata?: string;
}
