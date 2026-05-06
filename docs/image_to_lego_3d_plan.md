# Image-to-LEGO 3D 자동 변환 시스템 구체화 문서

작성일: 2026-05-06

## 1. 목표

단일 2D 이미지에서 객체를 추출하고, 3D 메쉬를 생성한 뒤, 물리적으로 조립 가능한 LEGO/LDraw 설계 파일(`.ldr`)로 변환하는 Python 파이프라인을 만든다.

최종 산출물은 다음 3가지다.

- `outputs/meshes/raw_model.glb`: AI가 생성한 원본 3D 메쉬
- `outputs/voxels/model_voxels.npz`: 복셀 점유 행렬, 복셀 색상, 좌표계 메타데이터
- `outputs/ldr/lego_output.ldr`: LDraw 호환 LEGO 조립 파일

## 2. 참고 저장소 조사 요약

### facebookresearch/sam-3d-objects

URL: https://github.com/facebookresearch/sam-3d-objects

- 2025년에 공개된 Meta의 SAM 3D Objects 구현체다.
- 단일 이미지에서 3D 객체 자산을 생성하는 데 초점을 둔다.
- README 기준 실행 진입점은 `demo.py`와 notebook이며, 모델 체크포인트는 Hugging Face 다운로드 흐름을 사용한다.
- 현재 이 프로젝트에서는 직접 코드를 복사하지 않고, `third_party/sam-3d-objects`에 외부 클론을 둔 뒤 wrapper가 subprocess 또는 Python API로 호출하는 방식이 가장 안전하다.
- 실제 반환 artifact는 버전별로 달라질 수 있으므로 wrapper는 `.glb` 직접 출력, mesh export, PLY/GS 중간 출력 변환을 모두 흡수할 수 있게 설계한다.

### elalish/manifold

URL: https://github.com/elalish/manifold

- C++ 기반 manifold mesh boolean/repair 라이브러리이며 Python 패키지는 `manifold3d`로 설치한다.
- 목적은 self-intersection, open boundary, non-manifold edge 때문에 voxel fill이 실패하는 문제를 줄이는 것이다.
- 모든 손상 메쉬가 자동으로 성공하는 것은 아니므로 `trimesh.repair`, convex fallback, 사용자 경고 경로를 같이 둔다.

### mikedh/trimesh

URL: https://github.com/mikedh/trimesh

- GLB/STL/OBJ 로딩, scene 병합, mesh repair, voxelization, nearest point query에 사용한다.
- 이 프로젝트에서는 메쉬 IO, 단위 정규화, voxel grid 생성, 표면 색상 샘플링의 중심 라이브러리로 둔다.

### CreativeMindstorms/brickalize

URL: https://github.com/CreativeMindstorms/brickalize

- STL을 LEGO 조립 모델로 변환하는 선행 구현체다.
- shell extraction, brick set, support, greedy brick placement 아이디어를 벤치마킹한다.
- 본 프로젝트는 Python 패키지 구조와 LDraw writer를 별도 구현하고, 초기 버전은 1x1 brick-only 출력으로 검증한다.

### intelligent-control-lab/StableLego

URL: https://github.com/intelligent-control-lab/StableLego

- LEGO assembly 안정성, assembly JSON, Gurobi 기반 최적화 흐름을 참고할 수 있다.
- 1차 개발 범위에는 Gurobi를 넣지 않는다.
- Phase 5 이후 stability score, support/overlap penalty, 큰 브릭 배치 재탐색의 참고 자료로 사용한다.

### dzungpng/brick-optimization-builder

URL: https://github.com/dzungpng/brick-optimization-builder

- LEGO 구조물의 안정성과 색상 제약을 고려한 brick optimization 사례다.
- Maya plugin 중심이므로 직접 의존하지 않고, 최적화 목적함수와 색상/구조 제약 아이디어만 참고한다.

## 3. 핵심 설계 원칙

- AI 추론 환경과 일반 geometry/brickify 환경을 느슨하게 분리한다.
- 각 모듈은 파일 artifact를 남겨 중간 결과를 Blender, Windows 3D Viewer, LDraw, Stud.io에서 따로 확인할 수 있게 한다.
- Phase 1에서는 1x1 brick-only `.ldr`를 먼저 성공시킨다.
- 큰 브릭 병합은 색상, 점유 공간, 연결성을 모두 만족하는 경우에만 적용한다.
- SAM 3D 출력 품질이 불안정할 수 있으므로 사용자가 직접 준비한 `.glb`를 pipeline 입력으로 넣는 우회 경로를 제공한다.

## 4. 디렉토리 구조

```text
MakeYourBrick/
  pyproject.toml
  configs/
    default.yaml
  data/
    examples/
      .gitkeep
    input_images/
      .gitkeep
    masks/
      .gitkeep
    ldraw/
      ldraw_colors.json
  docs/
    image_to_lego_3d_plan.md
  outputs/
    meshes/
      .gitkeep
    voxels/
      .gitkeep
    ldr/
      .gitkeep
  scripts/
    run_pipeline.py
  src/
    makeyourbrick/
      __init__.py
      config.py
      pipeline.py
      types.py
      ai/
        __init__.py
        sam3d_runner.py
      mesh/
        __init__.py
        solidify.py
      voxel/
        __init__.py
        voxelize.py
      brickify/
        __init__.py
        colors.py
        optimizer.py
      io/
        __init__.py
        ldr_writer.py
      utils/
        __init__.py
        paths.py
  tests/
    __init__.py
  third_party/
    .gitkeep
  requirements.txt
```

## 5. 파일별 역할

### `configs/default.yaml`

파이프라인 기본 설정 파일이다.

- 입력 이미지 경로
- 출력 디렉토리
- SAM 3D 외부 저장소 경로
- 목표 LEGO 크기
- voxel pitch 산정 방식
- brick catalog
- color quantization 설정

### `pyproject.toml`

`src/` 레이아웃을 Python 패키지로 인식시키기 위한 최소 설정이다.

개발 중에는 다음처럼 editable install을 사용할 수 있다.

```bash
pip install -e .
```

### `src/makeyourbrick/config.py`

YAML 설정을 Python dataclass로 로드한다.

초기 구현에서는 단순 dataclass default를 쓰고, 이후 `pyyaml`을 통해 `configs/default.yaml`을 병합한다.

### `src/makeyourbrick/types.py`

모듈 간 데이터 계약을 정의한다.

- `MeshArtifact`
- `VoxelArtifact`
- `Brick`
- `BrickSpec`
- `LDrawTransform`

### `src/makeyourbrick/ai/sam3d_runner.py`

SAM 3D Objects wrapper다.

책임:

- 입력 이미지 전처리 결과를 SAM 3D demo에 전달
- 외부 repo subprocess 실행
- 결과 파일을 `outputs/meshes/raw_model.glb`로 정규화
- SAM 3D가 GLB를 직접 주지 않는 경우 변환 hook 제공

1차 구현에서는 외부 repo가 준비되어 있지 않으면 명확한 예외 메시지를 낸다.

### `src/makeyourbrick/mesh/solidify.py`

메쉬 정제 모듈이다.

책임:

- `trimesh.load`로 GLB/OBJ/STL 로드
- `trimesh.Scene`이면 geometry를 하나로 병합
- degenerate face, duplicate face, unreferenced vertex 제거
- `manifold3d` 기반 watertight 변환 시도
- 실패 시 `trimesh.repair.fill_holes`와 fallback 경로 기록
- `outputs/meshes/watertight_model.glb` 저장

### `src/makeyourbrick/voxel/voxelize.py`

복셀화 및 색상 샘플링 모듈이다.

책임:

- 목표 stud 수 기준 pitch 계산
- `mesh.voxelized(pitch).fill()` 실행
- 복셀 중심 좌표 계산
- 원본 mesh surface nearest query로 RGB 샘플링
- `np.savez_compressed`로 점유 행렬, RGB, pitch, origin 저장

### `src/makeyourbrick/brickify/colors.py`

LEGO/LDraw 색상 양자화 모듈이다.

책임:

- `data/ldraw/ldraw_colors.json` 로드
- RGB를 CIELAB로 변환
- `scipy.spatial.distance.cdist`로 가장 가까운 색상 ID 계산
- 투명/메탈릭 색상 제외 옵션 제공

### `src/makeyourbrick/brickify/optimizer.py`

복셀을 LEGO brick list로 변환한다.

초기 브릭 후보:

| Brick | LDraw part | footprint | height |
| --- | --- | --- | --- |
| 2x4 brick | `3001.dat` | 2 x 4 | 1 |
| 1x4 brick | `3010.dat` | 1 x 4 | 1 |
| 2x2 brick | `3003.dat` | 2 x 2 | 1 |
| 1x2 brick | `3004.dat` | 1 x 2 | 1 |
| 1x1 brick | `3005.dat` | 1 x 1 | 1 |

1차 알고리즘:

1. Y layer를 아래에서 위로 순회한다.
2. X/Z 평면에서 아직 사용되지 않은 voxel을 찾는다.
3. 같은 색상의 가장 큰 후보 brick부터 배치 가능성을 검사한다.
4. 회전 가능한 brick은 `(width, depth)`와 `(depth, width)`를 모두 시도한다.
5. 배치 성공 시 해당 영역을 used 처리하고 `Brick`을 추가한다.
6. 실패 시 1x1 brick으로 fallback한다.

후속 안정성 개선:

- 위/아래 layer overlap score
- floating brick 제거
- staggered placement preference
- 긴 brick의 cantilever 제한
- StableLego/BOB 방식의 stability score 도입

### `src/makeyourbrick/io/ldr_writer.py`

LDraw `.ldr` writer다.

좌표 변환:

- Voxel X -> LDraw X
- Voxel Y -> LDraw Y, brick height 1개는 24 LDU
- Voxel Z -> LDraw Z
- 1 stud는 20 LDU
- 기본 brick의 local origin은 LDraw part 원점 기준 보정이 필요하므로 part별 offset table을 둔다.

LDraw line 형식:

```text
1 <color_id> <x> <y> <z> <a> <b> <c> <d> <e> <f> <g> <h> <i> <part.dat>
```

초기 버전은 identity rotation만 쓰고, 2x4/1x4 회전 배치 시 Y축 90도 회전 행렬을 적용한다.

### `scripts/run_pipeline.py`

CLI entry point다.

예상 사용:

```bash
python scripts/run_pipeline.py --image data/input_images/sample.png --target-studs 48
python scripts/run_pipeline.py --mesh outputs/meshes/raw_model.glb --skip-ai
python scripts/run_pipeline.py --voxels outputs/voxels/model_voxels.npz --only-ldr
```

## 6. 기술 스택

### 필수

- Python 3.10+
- NumPy: voxel matrix, color array
- SciPy: KDTree, color distance
- Trimesh: mesh loading, repair, voxelization
- manifold3d: watertight mesh repair
- Pillow/OpenCV: image loading/preprocessing
- PyYAML: config loading

### AI 추론용

- PyTorch
- TorchVision
- Hugging Face Hub
- SAM 3D Objects external repo
- NVIDIA GPU, VRAM 16GB 이상 권장

### 개발/검증용

- pytest
- ruff
- Blender 또는 Windows 3D Viewer
- LDraw 또는 Stud.io

## 7. 중간 데이터 계약

### `MeshArtifact`

```python
{
    "path": "outputs/meshes/raw_model.glb",
    "source": "sam3d",
    "is_watertight": false,
    "scale_unit": "normalized"
}
```

### `model_voxels.npz`

필수 배열:

- `occupancy`: `bool`, shape `(nx, ny, nz)`
- `rgb`: `uint8`, shape `(nx, ny, nz, 3)`
- `origin`: `float32`, shape `(3,)`
- `pitch`: `float32`, scalar
- `stud_scale`: `float32`, scalar

### `Brick`

```python
{
    "part_id": "3001.dat",
    "color_id": 16,
    "x": 0,
    "y": 0,
    "z": 0,
    "width": 2,
    "depth": 4,
    "height": 1,
    "rotation": 0
}
```

## 8. 구현 마일스톤

### Phase 0: 스캐폴딩

- 저장소 구조 생성
- `requirements.txt` 작성
- 이 문서 작성
- placeholder module 생성

### Phase 1: LDR writer 단독 검증

- 작은 synthetic voxel cube 생성
- 모든 voxel을 `3005.dat` 1x1 brick으로 출력
- LDraw/Stud.io에서 열어 좌표와 색상 검증

### Phase 2: GLB 입력 -> voxel

- 사용자가 준비한 GLB를 입력으로 받는다.
- SAM 3D 없이 `solidify -> voxelize -> 1x1 LDR`를 검증한다.

### Phase 3: 색상 양자화

- vertex/material/texture 색상 샘플링 구현
- LDraw 색상 ID로 매핑
- 색상별 voxel 분포를 로그로 출력한다.

### Phase 4: Greedy brick optimizer

- 1x1 only에서 2x4/1x4/2x2/1x2/1x1 후보 기반 greedy 배치로 확장한다.
- brick 수 감소율, 실패 fallback 수, 색상 mismatch 수를 리포트한다.

### Phase 5: SAM 3D 연결

- `third_party/sam-3d-objects`를 설정한다.
- sample image -> raw mesh artifact 생성
- 품질이 낮은 경우 mask/background removal 옵션을 추가한다.

### Phase 6: 안정성 개선

- 하부 지지율 검사
- floating brick 제거
- 큰 brick 배치 재탐색
- StableLego/BOB 논문/코드 아이디어를 반영한 stability score 추가

## 9. 주요 리스크와 대응

| 리스크 | 원인 | 대응 |
| --- | --- | --- |
| SAM 3D 설치 난이도 | CUDA/PyTorch/checkpoint 차이 | 외부 repo 격리, `--skip-ai` 경로 제공 |
| open mesh voxel fill 실패 | AI 생성 mesh 결함 | manifold3d + trimesh repair + fallback |
| 색상 불일치 | texture/material/vertex color 구조 차이 | 초기 RGB default, 이후 nearest surface sampling |
| LDraw part origin 차이 | part별 원점 정의 | part offset table과 Stud.io 검증 |
| 물리적 안정성 부족 | greedy packing 한계 | Phase 6 안정성 점수 도입 |
| 과도한 brick 수 | 높은 voxel resolution | target studs 제한, optimizer 도입 |

## 10. 초기 개발 우선순위

1. `ldr_writer.py`와 1x1 brick-only 출력
2. synthetic voxel test
3. GLB 로딩/voxelization
4. 색상표 로드와 RGB -> LDraw ID 매핑
5. greedy optimizer
6. SAM 3D wrapper
