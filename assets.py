from pathlib import Path

SUPPORTED_IMAGE_SUFFIXES = {".apng", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".webp"}


class AssetCatalog:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def list_assets(self):
        if not self.root.is_dir():
            return []
        assets = []
        for path in sorted(self.root.rglob("*")):
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES:
                assets.append({"id": path.relative_to(self.root).as_posix(), "name": path.name})
        return assets

    def resolve(self, asset_id):
        if not isinstance(asset_id, str) or not asset_id:
            raise ValueError("An image asset must be selected.")
        candidate = (self.root / asset_id).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as error:
            raise ValueError("The selected image asset is outside the approved asset directory.") from error
        if not candidate.is_file() or candidate.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
            raise ValueError("The selected image asset is unavailable.")
        return candidate
