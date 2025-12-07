from pathlib import Path


def find_project_root(start: str | Path | None = None) -> Path:
    """
    Ищет вверх от start (или от текущего файла) папку,
    где есть pyproject.toml — считаем её корнем проекта.
    """
    if start is None:
        start = __file__

    path = Path(start).resolve()

    for parent in [path] + list(path.parents):
        if (parent / "pyproject.toml").is_file():
            return parent

    raise RuntimeError("Не удалось найти корень проекта (нет pyproject.toml)")
