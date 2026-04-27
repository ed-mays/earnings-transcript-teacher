"use client";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { JUDGMENT_LABELS, type Judgment, type JudgmentChoice } from "./types";

interface QAJudgmentPromptProps {
  judgment: Judgment;
  onChange: (next: Judgment) => void;
  onReveal: () => void;
}

const CHOICES: JudgmentChoice[] = ["yes", "partial", "no"];

/** Active-learning hinge: user commits to an answer before seeing the system's verdict. */
export function QAJudgmentPrompt({ judgment, onChange, onReveal }: QAJudgmentPromptProps) {
  const canReveal = judgment.choice !== null && judgment.text.trim().length > 0;

  return (
    <div className="space-y-4 rounded-xl border border-border bg-muted/40 px-5 py-5">
      <div>
        <p className="text-sm font-semibold text-foreground">Your turn</p>
        <p className="text-xs text-muted-foreground">
          Commit to a judgment before the system shows its analysis. This is the
          point of the exercise.
        </p>
      </div>

      <fieldset className="space-y-2">
        <legend className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Did the executive answer the question?
        </legend>
        <div className="flex flex-wrap gap-2">
          {CHOICES.map((choice) => {
            const selected = judgment.choice === choice;
            return (
              <label
                key={choice}
                className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors ${
                  selected
                    ? "border-primary bg-primary/10 text-foreground"
                    : "border-border text-muted-foreground hover:bg-muted"
                }`}
              >
                <input
                  type="radio"
                  name="judgment-choice"
                  value={choice}
                  checked={selected}
                  onChange={() => onChange({ ...judgment, choice })}
                  className="sr-only"
                />
                <span>{JUDGMENT_LABELS[choice]}</span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <div className="space-y-1.5">
        <label
          htmlFor="judgment-reasoning"
          className="text-xs font-semibold uppercase tracking-wide text-muted-foreground"
        >
          In your own words, why? (1–2 sentences)
        </label>
        <Textarea
          id="judgment-reasoning"
          value={judgment.text}
          onChange={(e) => onChange({ ...judgment, text: e.target.value })}
          placeholder="What did you notice? What did they avoid?"
          className="min-h-20"
        />
      </div>

      <div className="flex justify-end">
        <Button onClick={onReveal} disabled={!canReveal}>
          Reveal system analysis →
        </Button>
      </div>
    </div>
  );
}
