"use client";

import { useFlagContext } from "@/components/FlagProvider";

/**
 * Returns the enabled state of a feature flag.
 * Falls back to defaultValue (false) if the key is not in the flag context.
 */
export function useFlag(key: string, defaultValue = false): boolean {
  const flags = useFlagContext();
  return key in flags ? flags[key] : defaultValue;
}
