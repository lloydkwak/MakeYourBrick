# Phase 5 TODO: Image Pipeline and SAM 3D Runner

This temporary working document tracks Phase 5 until it is fully implemented and verified.

## Goal

Connect image input to the existing mesh-to-LDraw pipeline through a SAM 3D Objects runner contract.

The target flow is:

```text
image -> raw_model.glb -> cleaned mesh -> voxel artifact -> sampled/quantized colors -> optimized LDraw + report
```

## Strategy

Phase 5 should not require a GPU for automated tests. The implementation will use two layers:

1. A testable runner interface that can be faked locally.
2. A subprocess-based `Sam3DRunner` for real `facebookresearch/sam-3d-objects` execution on a prepared GPU machine.

## Runner Contract

The runner must expose:

```python
generate(image_path: Path, output_path: Path) -> MeshArtifact
```

The real runner must:

- verify the image exists
- verify the external SAM 3D repo exists
- run a configurable command template
- confirm the expected output mesh was produced
- return `MeshArtifact(path=output_path, source="sam3d")`

## Completion Checklist

- [x] Add Phase 5 TODO document.
- [x] Harden `Sam3DRunner` with configurable subprocess execution.
- [x] Add tests for missing repo, missing image, failed command, and successful command.
- [x] Implement `run_from_image()` orchestration using dependency injection.
- [x] Add fake runner integration test from image to `.ldr`.
- [x] Add `scripts/image_to_ldr.py`.
- [x] Add CLI test using a fake generated mesh path.
- [ ] Document real SAM setup and manual verification commands.
- [ ] Run verification commands.
- [ ] Commit and push each completed feature checkpoint.

## Verification Commands

```bash
python -m compileall src scripts
python -m pytest
python scripts/image_to_ldr.py --image data/input_images/sample.png --sam-command "python third_party/sam-3d-objects/demo.py --input {image} --output {output}" --target-studs 48 --sample-colors --optimize --report outputs/reports/image_report.json --output outputs/ldr/image_output.ldr
```

## Done Definition

- All tests pass without requiring SAM 3D or a GPU.
- Image pipeline orchestration is tested with a fake mesh generator.
- Real SAM execution path is configurable and fails with clear errors when not installed.
- Existing mesh CLI remains unchanged.
