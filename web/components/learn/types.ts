/** Shared types for the Variant D learn page components. */

export type AnnotationLayer = "guidance" | "sentiment" | "terms";

export type AnnotationLayers = Record<AnnotationLayer, boolean>;

export const DEFAULT_LAYERS: AnnotationLayers = {
  guidance: true,
  sentiment: true,
  terms: true,
};

export interface ChatContext {
  type: "term" | "guidance" | "qa-forensics";
  text: string;
  metadata?: string;
}
