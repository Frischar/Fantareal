# Fa Card Writer Human Character Prompt Pack

This folder is the self-contained prompt pack used by Card Writer copilot/wheelchair mode.

It is the Fa-specific runtime adapter for the author's public skill:

`virtual-character-realism-design-zh`

Upstream skill repository:

`https://github.com/cOkieeman/virtual-character-realism-design-zh`

The public skill is the broader author-maintained design system. This folder is the bundled Fa adapter: it keeps the same goal and method, but compresses them into prompt files that Card Writer can load, reason with, and turn into reviewable JSON candidates.

The mod must work offline and must not require `design_docs` or the external skill repository at runtime. When the public skill evolves, update this prompt pack intentionally instead of adding a live dependency.

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
- Treat `virtual-character-realism-design-zh` as the upstream author skill and this folder as the Fa runtime adaptation layer.
