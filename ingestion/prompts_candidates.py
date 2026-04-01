"""
Prompt variants under active evaluation.

Rules:
  - Do NOT import this file in the production pipeline.
  - Each constant must include a comment stating the hypothesis being tested.
  - When a variant wins, it replaces the corresponding constant in prompts.py
    via a single Git commit. The commit message is the version record.
  - When a variant loses, delete it. Dead variants must not accumulate here.

Naming convention: <PHASE>_v<N>_<short_hypothesis>
Example: TIER_1_v2_few_shot_examples
"""

# Variants are added here as part of active tuning experiments.
# See docs/prompt-versioning.md for the full workflow.
