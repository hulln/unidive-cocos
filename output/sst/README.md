# SST Output Layout

This folder keeps extraction outputs and final annotated deliverables.

## Stable extraction outputs (used by scripts/docs)
- `backchannel_candidates_expanded.csv`
- `filtered_export_bc_candidates.xlsx`
- `coco_candidates_v1.xlsx`
- `coconstruction_candidates.csv`
- `sl_sst-ud-merged.backchannels.conllu`

## Final deliverable package
- `final_bc_coco/`

## Workflow reference
Run steps in `scripts/README.md` (01 -> 07).
Key manual points:
- Filter backchannels before apply step.
- Annotate coconstruction YES cases before coconstruction apply step.
