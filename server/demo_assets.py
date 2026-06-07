from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
PACKAGED_DEMO_DIR = ROOT_DIR / "assets" / "demo_cases"
OPA_DATASET_DIR = ROOT_DIR / "assets" / "datasets" / "opa" / "raw" / "new_OPA"
REPORT_SCREENSHOT_DIR = ROOT_DIR / "report" / "screenshots"

DEMO_CASE_IDS = ["opa_test_001", "opa_test_002", "opa_test_006", "opa_test_052", "opa_test_059"]
DEMO_CASE_TITLES = {
    "success_with_duplicate_cleanup": "成功案例",
    "score_saturation_boundary": "分数饱和边界",
    "dedup_success": "去重成功案例",
    "negative_false_positive_risk": "负例误报风险",
    "clear_negative_rejection": "清晰拒绝案例",
}


def demo_case_available(case_id: str, summary: dict[str, str]) -> bool:
    required_assets = ("background", "foreground", "mask")
    return all(
        (resolve_demo_asset(case_id, asset_name, summary) or Path()).is_file()
        for asset_name in required_assets
    )


def optional_demo_url(case_id: str, asset_name: str) -> str | None:
    asset_path = resolve_demo_asset(case_id, asset_name, {})
    if asset_path is None or not asset_path.is_file():
        return None
    return f"/api/demo/cases/{case_id}/{asset_name}"


def resolve_demo_asset(case_id: str, asset_name: str, summary: dict[str, str]) -> Path | None:
    if asset_name == "heatmap":
        return REPORT_SCREENSHOT_DIR / "explainability" / f"{case_id}_occlusion_heatmap.png"
    if asset_name == "panel":
        return REPORT_SCREENSHOT_DIR / "cases" / f"{case_id}_case_panel.png"

    packaged_asset = PACKAGED_DEMO_DIR / case_id / f"{asset_name}.jpg"
    if packaged_asset.is_file():
        return packaged_asset

    fg_id = summary.get("fg_id")
    bg_id = summary.get("bg_id")
    foreground_category = summary.get("foreground_category")
    background_category = summary.get("background_category")
    if not all((fg_id, bg_id, foreground_category, background_category)):
        return None

    if asset_name == "background":
        return OPA_DATASET_DIR / "background" / background_category / f"{bg_id}.jpg"
    if asset_name == "foreground":
        return OPA_DATASET_DIR / "foreground" / foreground_category / f"{fg_id}.jpg"
    if asset_name == "mask":
        return OPA_DATASET_DIR / "foreground" / foreground_category / f"mask_{fg_id}.jpg"
    return None
