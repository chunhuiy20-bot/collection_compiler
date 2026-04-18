from pathlib import Path

UPLOAD_DIR = Path("uploads")


class FileSearchService:

    def find_files(self, application_code: str | None, uid: str | None) -> dict[str, list[str]]:
        result = {}
        for key in filter(None, [application_code and ("application_code", application_code), uid and ("uid", uid)]):
            name, value = key
            result[name] = [
                str(f.resolve())
                for directory in UPLOAD_DIR.rglob(value)
                if directory.is_dir()
                for f in directory.rglob("*")
                if f.is_file()
            ]
        return result

    def resolve_preview_path(self, raw_path: str) -> Path:
        target_path = Path(raw_path).expanduser().resolve()
        upload_root = UPLOAD_DIR.resolve()

        if upload_root not in target_path.parents and target_path != upload_root:
            raise ValueError("仅支持预览 uploads 目录内文件")
        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError("文件不存在")
        return target_path


file_search_service = FileSearchService()
