import importlib.resources as resources

def load_theme_qss(theme_name: str) -> str:
    try:
        fname = f"{theme_name}.qss"
        with resources.files(__package__).joinpath(fname).open("r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""
