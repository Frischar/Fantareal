# Fa Card Writer Human Character Prompt Pack

This folder is the self-contained prompt pack used by Card Writer copilot/wheelchair mode.

It is a distilled Fa-specific runtime version of the broader human-character-system notes. The original generic skill and long tutorial/reference material are intentionally not required at runtime, so the mod can work without `design_docs`.

## Fast Mode

Loaded for every copilot request:

- `wheelchair_core.md`
- `runtime_package.md`
- `container_router.md`
- `candidate_rules.md`
- `database_designer.md`
- `worldbook_preset_memory.md`

## Deep Mode

Deep mode loads all fast-mode files, plus:

- `orchestration_planner.md`
- `deep_reference.md`
- `question_bank_reference.md`
- `case_reference.md`
- `fa_container_deep_router.md`

Deep mode may think with more context internally. P2.5 keeps the goal scoped to a runnable character package: persona, worldbook, memory, database tag linkage, and only a light preset adapter.

High-order preset generation is intentionally out of scope for this prompt pack. Preset candidates should stay small and only cover basic runtime discipline.

`plan`, `candidate_groups`, `group_id`, `group_title`, `container_role`, `depends_on`, and `draft_only` are review UI metadata. Candidate application must still rely on `candidates[].module/action/target/before/after`.

## Source Boundary

- Keep this folder focused on Fa Card Writer behavior.
- Do not reference local `design_docs` files from runtime code.
- Do not include project-specific story material such as the Aihong redemption timeline.
- The generic human-character-system skill can live in a separate GitHub repository later.
