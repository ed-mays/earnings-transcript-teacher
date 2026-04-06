"use client";

/** Admin page for managing feature flags. Client component (toggle + create + delete state). */

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface FlagRow {
  key: string;
  enabled: boolean;
  description: string;
  category: string;
  updated_at: string;
}

interface FlagListResponse {
  flags: FlagRow[];
}

type Category = "feature" | "kill_switch";

function categoryBadge(category: string) {
  return category === "kill_switch" ? (
    <Badge variant="destructive">kill switch</Badge>
  ) : (
    <Badge variant="outline">feature</Badge>
  );
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function AdminFlagsPage() {
  const [flags, setFlags] = useState<FlagRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create form state
  const [newKey, setNewKey] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newCategory, setNewCategory] = useState<Category>("feature");
  const [newEnabled, setNewEnabled] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    async function loadFlags() {
      try {
        const resp = await fetch("/api/admin/flags");
        if (!resp.ok) {
          const data = (await resp.json()) as { error?: string };
          setError(data.error ?? `Failed to load flags (${resp.status}).`);
          return;
        }
        const data = (await resp.json()) as FlagListResponse;
        setFlags(data.flags);
      } catch {
        setError("Network error — could not reach the server.");
      } finally {
        setLoading(false);
      }
    }
    void loadFlags();
  }, []);

  async function handleToggle(flag: FlagRow) {
    const next = !flag.enabled;
    // Optimistic update
    setFlags((prev) =>
      prev.map((f) => (f.key === flag.key ? { ...f, enabled: next } : f))
    );
    try {
      const resp = await fetch(`/api/admin/flags/${encodeURIComponent(flag.key)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: next }),
      });
      if (!resp.ok) {
        // Revert on failure
        setFlags((prev) =>
          prev.map((f) => (f.key === flag.key ? { ...f, enabled: flag.enabled } : f))
        );
      } else {
        const updated = (await resp.json()) as FlagRow;
        setFlags((prev) =>
          prev.map((f) => (f.key === flag.key ? updated : f))
        );
      }
    } catch {
      // Revert on network error
      setFlags((prev) =>
        prev.map((f) => (f.key === flag.key ? { ...f, enabled: flag.enabled } : f))
      );
    }
  }

  async function handleCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!newKey.trim()) return;

    setCreating(true);
    setCreateError(null);

    try {
      const resp = await fetch("/api/admin/flags", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          key: newKey.trim(),
          description: newDescription.trim(),
          category: newCategory,
          enabled: newEnabled,
        }),
      });
      const data = (await resp.json()) as FlagRow & { error?: string; detail?: string };
      if (resp.status === 201) {
        setFlags((prev) => [...prev, data]);
        setNewKey("");
        setNewDescription("");
        setNewCategory("feature");
        setNewEnabled(false);
      } else {
        setCreateError(data.detail ?? data.error ?? `Error (${resp.status}).`);
      }
    } catch {
      setCreateError("Network error — could not reach the server.");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(key: string) {
    try {
      const resp = await fetch(`/api/admin/flags/${encodeURIComponent(key)}`, {
        method: "DELETE",
      });
      if (resp.ok || resp.status === 204) {
        setFlags((prev) => prev.filter((f) => f.key !== key));
      }
    } catch {
      // Silent — flag remains in list if delete fails
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-12">
      <h1 className="mb-2 text-3xl font-semibold text-foreground">Admin — Feature Flags</h1>
      <p className="mb-8 text-muted-foreground">
        Create, toggle, and delete feature flags. Changes take effect immediately.
      </p>

      {error && <p className="mb-6 text-sm text-destructive">{error}</p>}

      {/* Create form */}
      <Card className="mb-8 max-w-lg">
        <CardContent>
          <form onSubmit={handleCreate} className="flex flex-col gap-4">
            <h2 className="text-base font-medium text-foreground">New flag</h2>

            <div>
              <label htmlFor="flag-key" className="mb-1.5 block text-sm font-medium text-foreground">
                Key
              </label>
              <Input
                id="flag-key"
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                placeholder="e.g. chat_enabled"
                disabled={creating}
                className="font-mono"
              />
            </div>

            <div>
              <label htmlFor="flag-description" className="mb-1.5 block text-sm font-medium text-foreground">
                Description
              </label>
              <Input
                id="flag-description"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="What does this flag control?"
                disabled={creating}
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                Category
              </label>
              <Select value={newCategory} onValueChange={(v) => setNewCategory(v as Category)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="feature">Feature</SelectItem>
                  <SelectItem value="kill_switch">Kill Switch</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-3">
              <Switch
                id="flag-enabled"
                checked={newEnabled}
                onCheckedChange={setNewEnabled}
                disabled={creating}
              />
              <label htmlFor="flag-enabled" className="text-sm text-foreground">
                Enabled
              </label>
            </div>

            {createError && <p className="text-sm text-destructive">{createError}</p>}

            <Button type="submit" disabled={creating || !newKey.trim()} className="w-full">
              {creating ? "Creating…" : "Create flag"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Flags table */}
      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : flags.length === 0 ? (
        <p className="text-sm text-muted-foreground">No flags found.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Key</TableHead>
              <TableHead>Enabled</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Updated</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {flags.map((flag) => (
              <TableRow key={flag.key}>
                <TableCell className="font-mono text-sm">{flag.key}</TableCell>
                <TableCell>
                  <Switch
                    checked={flag.enabled}
                    onCheckedChange={() => void handleToggle(flag)}
                    aria-label={`Toggle ${flag.key}`}
                  />
                </TableCell>
                <TableCell>{categoryBadge(flag.category)}</TableCell>
                <TableCell className="text-muted-foreground">{flag.description}</TableCell>
                <TableCell className="text-muted-foreground">{formatDate(flag.updated_at)}</TableCell>
                <TableCell>
                  <AlertDialog>
                    <AlertDialogTrigger
                      render={
                        <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" />
                      }
                    >
                      Delete
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Delete flag?</AlertDialogTitle>
                        <AlertDialogDescription>
                          This will permanently delete{" "}
                          <span className="font-mono font-medium">{flag.key}</span>. This action cannot be
                          undone.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          variant="destructive"
                          onClick={() => void handleDelete(flag.key)}
                        >
                          Delete
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
