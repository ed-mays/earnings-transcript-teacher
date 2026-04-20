"use client";

import { cn } from "@/lib/utils";
import type { AnnotationLayer, AnnotationLayers } from "./types";

interface LayerConfig {
  key: AnnotationLayer;
  label: string;
  dotClass: string;
}

const LAYER_CONFIG: readonly LayerConfig[] = [
  { key: "guidance", label: "Guidance", dotClass: "bg-blue-500" },
  { key: "evasion", label: "Evasion", dotClass: "bg-amber-500" },
  { key: "sentiment", label: "Sentiment", dotClass: "bg-purple-500" },
  { key: "terms", label: "Terms", dotClass: "bg-green-500" },
];

interface LayerToggleProps {
  layers: AnnotationLayers;
  onChange: (layer: AnnotationLayer) => void;
}

/** Sticky pill bar for toggling annotation layers on the learn page. */
export function LayerToggle({ layers, onChange }: LayerToggleProps) {
  return (
    <div
      role="group"
      aria-label="Annotation layers"
      className="sticky top-0 z-10 flex flex-wrap gap-2 border-b bg-background/95 px-4 py-3 backdrop-blur"
    >
      {LAYER_CONFIG.map((layer) => {
        const active = layers[layer.key];
        return (
          <button
            key={layer.key}
            type="button"
            role="switch"
            aria-checked={active}
            aria-label={`Toggle ${layer.label} layer`}
            onClick={() => onChange(layer.key)}
            className={cn(
              "inline-flex min-h-[44px] items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition-colors",
              active
                ? "border-foreground/20 bg-foreground/5 text-foreground"
                : "border-transparent bg-transparent text-muted-foreground hover:bg-foreground/5",
            )}
          >
            <span
              aria-hidden
              className={cn(
                "h-2.5 w-2.5 rounded-full",
                layer.dotClass,
                !active && "opacity-40",
              )}
            />
            {layer.label}
          </button>
        );
      })}
    </div>
  );
}
