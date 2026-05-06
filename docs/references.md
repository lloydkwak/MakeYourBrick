# References

## Primary Repositories

- SAM 3D Objects: https://github.com/facebookresearch/sam-3d-objects
- Manifold: https://github.com/elalish/manifold
- Trimesh: https://github.com/mikedh/trimesh
- Brickalize: https://github.com/CreativeMindstorms/brickalize
- StableLego: https://github.com/intelligent-control-lab/StableLego
- Brick Optimization Builder: https://github.com/dzungpng/brick-optimization-builder

## File Formats and Standards

- LDraw file format specification: https://www.ldraw.org/article/218.html
- LDraw color definitions: https://www.ldraw.org/article/547.html

## Academic and Technical Background

- SAM 3D: 3Dfy Anything in Images, arXiv:2511.16624. Paper page: https://huggingface.co/papers/2511.16624
- ManifoldPlus: A Robust and Scalable Watertight Manifold Surface Generation Method for Triangle Soups, arXiv:2005.11621. Project page: https://yichaozhou.com/publication/2005manifold/
- Robust Watertight Manifold Surface Generation Method for ShapeNet Models, arXiv:1802.01698. Semantic Scholar page: https://www.semanticscholar.org/paper/Robust-Watertight-Manifold-Surface-Generation-for-Huang-Su/9324c5239d358b9cc28811588be8e2d0b85d65e9
- Voxelization and mesh processing: Trimesh documentation and source examples guide mesh loading, scene concatenation, and voxelization.
- LEGO stability and optimization: StableLego and Brick Optimization Builder are used as design references for future stability scoring and brick placement improvements.

## How References Are Used

The current implementation does not vendor code from these repositories. It uses them as architecture and algorithm references, while keeping MakeYourBrick's own implementation small and testable.
