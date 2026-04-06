"use client";

import { createContext, useContext } from "react";

const FlagContext = createContext<Record<string, boolean>>({});

interface FlagProviderProps {
  initialFlags: Record<string, boolean>;
  children: React.ReactNode;
}

export function FlagProvider({ initialFlags, children }: FlagProviderProps) {
  return (
    <FlagContext.Provider value={initialFlags}>{children}</FlagContext.Provider>
  );
}

export function useFlagContext(): Record<string, boolean> {
  return useContext(FlagContext);
}
