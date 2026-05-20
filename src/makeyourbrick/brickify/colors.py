from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_RGB = np.array((160, 165, 169), dtype=np.uint8)
_LUMA_WEIGHTS = np.array((0.2126, 0.7152, 0.0722), dtype=np.float64)


@dataclass(frozen=True)
class LDrawColor:
    code: int
    name: str
    rgb: tuple[int, int, int]


# Solid, non-transparent LDConfig colours. The values come from LDraw.org's
# official colour definition reference / LDConfig.ldr.
SOLID_LDRAW_COLORS: tuple[LDrawColor, ...] = (
    LDrawColor(0, "Black", (27, 42, 52)),
    LDrawColor(1, "Blue", (30, 90, 168)),
    LDrawColor(2, "Green", (0, 133, 43)),
    LDrawColor(3, "Dark_Turquoise", (6, 157, 159)),
    LDrawColor(4, "Red", (180, 0, 0)),
    LDrawColor(5, "Dark_Pink", (211, 53, 157)),
    LDrawColor(6, "Brown", (84, 51, 36)),
    LDrawColor(7, "Light_Grey", (138, 146, 141)),
    LDrawColor(8, "Dark_Grey", (84, 89, 85)),
    LDrawColor(9, "Light_Blue", (151, 203, 217)),
    LDrawColor(10, "Bright_Green", (88, 171, 65)),
    LDrawColor(11, "Light_Turquoise", (0, 170, 164)),
    LDrawColor(12, "Salmon", (240, 109, 97)),
    LDrawColor(13, "Pink", (246, 169, 187)),
    LDrawColor(14, "Yellow", (250, 200, 10)),
    LDrawColor(15, "White", (244, 244, 244)),
    LDrawColor(17, "Light_Green", (173, 217, 168)),
    LDrawColor(18, "Light_Yellow", (255, 214, 127)),
    LDrawColor(19, "Tan", (215, 186, 140)),
    LDrawColor(20, "Light_Violet", (175, 190, 214)),
    LDrawColor(22, "Purple", (103, 31, 129)),
    LDrawColor(25, "Orange", (214, 121, 35)),
    LDrawColor(26, "Magenta", (144, 31, 118)),
    LDrawColor(27, "Lime", (165, 202, 24)),
    LDrawColor(28, "Dark_Tan", (137, 125, 98)),
    LDrawColor(29, "Bright_Pink", (255, 158, 205)),
    LDrawColor(30, "Medium_Lavender", (160, 110, 185)),
    LDrawColor(31, "Lavender", (205, 164, 222)),
    LDrawColor(68, "Very_Light_Orange", (253, 195, 131)),
    LDrawColor(70, "Reddish_Brown", (95, 49, 9)),
    LDrawColor(71, "Light_Bluish_Grey", (150, 150, 150)),
    LDrawColor(72, "Dark_Bluish_Grey", (100, 100, 100)),
    LDrawColor(73, "Medium_Blue", (115, 150, 200)),
    LDrawColor(74, "Medium_Green", (127, 196, 117)),
    LDrawColor(77, "Light_Pink", (254, 204, 207)),
    LDrawColor(78, "Light_Nougat", (255, 201, 149)),
    LDrawColor(84, "Medium_Nougat", (170, 125, 85)),
    LDrawColor(85, "Medium_Lilac", (68, 26, 145)),
    LDrawColor(86, "Light_Brown", (123, 93, 65)),
    LDrawColor(92, "Nougat", (187, 128, 90)),
    LDrawColor(100, "Light_Salmon", (249, 183, 165)),
    LDrawColor(115, "Medium_Lime", (183, 212, 37)),
    LDrawColor(118, "Aqua", (156, 214, 204)),
    LDrawColor(120, "Light_Lime", (222, 234, 146)),
    LDrawColor(121, "Light_Orange", (248, 154, 57)),
    LDrawColor(128, "Dark_Nougat", (173, 97, 64)),
    LDrawColor(151, "Very_Light_Bluish_Grey", (200, 200, 200)),
    LDrawColor(191, "Bright_Light_Orange", (252, 172, 0)),
    LDrawColor(212, "Bright_Light_Blue", (157, 195, 247)),
    LDrawColor(226, "Bright_Light_Yellow", (255, 236, 108)),
    LDrawColor(232, "Sky_Blue", (119, 201, 216)),
    LDrawColor(272, "Dark_Blue", (25, 50, 90)),
    LDrawColor(288, "Dark_Green", (0, 69, 26)),
    LDrawColor(308, "Dark_Brown", (53, 33, 0)),
    LDrawColor(320, "Dark_Red", (114, 0, 18)),
    LDrawColor(321, "Dark_Azure", (70, 155, 195)),
    LDrawColor(322, "Medium_Azure", (104, 195, 226)),
    LDrawColor(323, "Light_Aqua", (211, 242, 234)),
    LDrawColor(330, "Olive_Green", (119, 119, 78)),
    LDrawColor(335, "Sand_Red", (136, 96, 94)),
    LDrawColor(351, "Medium_Dark_Pink", (247, 133, 177)),
    LDrawColor(353, "Coral", (255, 109, 119)),
    LDrawColor(370, "Medium_Brown", (117, 89, 69)),
    LDrawColor(371, "Medium_Tan", (204, 163, 115)),
    LDrawColor(378, "Sand_Green", (112, 142, 124)),
    LDrawColor(379, "Sand_Blue", (112, 129, 154)),
    LDrawColor(402, "Reddish_Orange", (202, 76, 11)),
    LDrawColor(484, "Dark_Orange", (145, 80, 28)),
)


def _srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    rgb = np.asarray(rgb, dtype=np.float64) / 255.0
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    linear = _srgb_to_linear(rgb)
    xyz = linear @ np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ],
        dtype=np.float64,
    ).T
    xyz /= np.array((0.95047, 1.0, 1.08883), dtype=np.float64)
    epsilon = 216 / 24389
    kappa = 24389 / 27
    f = np.where(xyz > epsilon, np.cbrt(xyz), (kappa * xyz + 16) / 116)
    return np.stack((116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])), axis=-1)


def _palette_arrays(palette: tuple[LDrawColor, ...] = SOLID_LDRAW_COLORS) -> tuple[np.ndarray, np.ndarray]:
    codes = np.array([color.code for color in palette], dtype=np.int32)
    labs = rgb_to_lab(np.array([color.rgb for color in palette], dtype=np.uint8))
    return codes, labs


def quantize_rgb_to_ldraw(
    rgb: np.ndarray,
    *,
    palette: tuple[LDrawColor, ...] = SOLID_LDRAW_COLORS,
    default_color_id: int = 71,
) -> np.ndarray:
    rgb = np.asarray(rgb, dtype=np.uint8)
    result = np.full(rgb.shape[:-1], int(default_color_id), dtype=np.int32)
    mask = np.any(rgb > 0, axis=-1)
    if not mask.any():
        return result
    codes, palette_lab = _palette_arrays(palette)
    source_lab = rgb_to_lab(rgb[mask])
    distances = np.linalg.norm(source_lab[:, None, :] - palette_lab[None, :, :], axis=2)
    result[mask] = codes[np.argmin(distances, axis=1)]
    return result


def soften_texture_shadows(rgb: np.ndarray, occupancy: np.ndarray | None = None) -> np.ndarray:
    """Compress baked photo shadows before matching to the LEGO colour palette."""
    rgb = np.asarray(rgb, dtype=np.uint8)
    corrected = rgb.astype(np.float64)
    mask = np.any(rgb > 0, axis=-1)
    if occupancy is not None:
        mask &= np.asarray(occupancy, dtype=bool)
    if not mask.any():
        return rgb.copy()

    samples = corrected[mask]
    luma = samples @ _LUMA_WEIGHTS
    median_luma = float(np.percentile(luma, 55))
    if median_luma < 64:
        return rgb.copy()

    median_rgb = np.percentile(samples, 55, axis=0)
    shadow_floor = float(np.clip(median_luma * 0.72, 84, 168))
    shadow_mask = mask.copy()
    full_luma = corrected @ _LUMA_WEIGHTS
    shadow_mask &= full_luma < shadow_floor
    if not shadow_mask.any():
        return rgb.copy()

    shadow_luma = np.maximum(full_luma[shadow_mask], 1.0)
    gain = np.minimum(shadow_floor / shadow_luma, 2.6)
    lifted = corrected[shadow_mask] * gain[:, None]
    blend = np.clip((shadow_floor - shadow_luma) / max(shadow_floor, 1.0), 0.0, 0.55)
    lifted = lifted * (1.0 - blend[:, None]) + median_rgb * blend[:, None]
    corrected[shadow_mask] = lifted
    return np.clip(corrected, 0, 255).astype(np.uint8)


def _visual_rgb_source(mesh) -> tuple[np.ndarray, np.ndarray] | tuple[None, None]:
    visual = getattr(mesh, "visual", None)
    vertex_colors = getattr(visual, "vertex_colors", None)
    if vertex_colors is not None and len(vertex_colors) == len(mesh.vertices):
        colors = np.asarray(vertex_colors, dtype=np.uint8)
        if colors.shape[1] >= 3 and np.any(colors[:, :3] > 0):
            return np.asarray(mesh.vertices, dtype=np.float64), colors[:, :3]

    face_colors = getattr(visual, "face_colors", None)
    if face_colors is not None and len(face_colors) == len(mesh.faces):
        colors = np.asarray(face_colors, dtype=np.uint8)
        if colors.shape[1] >= 3 and np.any(colors[:, :3] > 0):
            return np.asarray(mesh.triangles_center, dtype=np.float64), colors[:, :3]

    material = getattr(visual, "material", None)
    uv = getattr(visual, "uv", None)
    image = getattr(material, "image", None)
    if uv is not None and image is not None and len(uv) == len(mesh.vertices):
        image_rgb = np.asarray(image.convert("RGB") if hasattr(image, "convert") else image, dtype=np.uint8)
        if image_rgb.ndim == 3 and image_rgb.shape[2] >= 3:
            height, width = image_rgb.shape[:2]
            uv_array = np.asarray(uv, dtype=np.float64)
            u = np.mod(uv_array[:, 0], 1.0)
            v = np.clip(uv_array[:, 1], 0.0, 1.0)
            x = np.clip(np.rint(u * (width - 1)).astype(np.int64), 0, width - 1)
            y = np.clip(np.rint((1.0 - v) * (height - 1)).astype(np.int64), 0, height - 1)
            colors = image_rgb[y, x, :3]
            if np.any(colors > 0):
                return np.asarray(mesh.vertices, dtype=np.float64), colors.astype(np.uint8)

    diffuse = getattr(material, "diffuse", None)
    if diffuse is not None and len(diffuse) >= 3:
        return np.asarray([[0.0, 0.0, 0.0]], dtype=np.float64), np.asarray([diffuse[:3]], dtype=np.uint8)

    return None, None


def _nearest_indices(source_points: np.ndarray, query_points: np.ndarray) -> np.ndarray:
    try:
        from scipy.spatial import cKDTree

        return cKDTree(source_points).query(query_points, workers=-1)[1]
    except Exception:
        indices = np.zeros(len(query_points), dtype=np.int64)
        chunk_size = 512
        for start in range(0, len(query_points), chunk_size):
            chunk = query_points[start : start + chunk_size]
            distances = np.sum((chunk[:, None, :] - source_points[None, :, :]) ** 2, axis=2)
            indices[start : start + len(chunk)] = np.argmin(distances, axis=1)
        return indices


def sample_mesh_rgb(mesh, point_grid: np.ndarray, occupancy: np.ndarray, default_rgb: np.ndarray = DEFAULT_RGB) -> np.ndarray:
    rgb = np.zeros((*occupancy.shape, 3), dtype=np.uint8)
    rgb[occupancy] = default_rgb
    source_points, source_rgb = _visual_rgb_source(mesh)
    if source_points is None or source_rgb is None:
        return rgb
    occupied_points = point_grid[occupancy]
    if len(occupied_points) == 0:
        return rgb
    if len(source_points) == 1:
        rgb[occupancy] = source_rgb[0]
        return soften_texture_shadows(rgb, occupancy)
    rgb[occupancy] = source_rgb[_nearest_indices(source_points, occupied_points)]
    return soften_texture_shadows(rgb, occupancy)
