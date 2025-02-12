# modules/utils.py
def parse_size(size_str):
    """Convertir une chaîne de taille en Mo pour validation."""
    try:
        if size_str.endswith("GB"):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith("MB"):
            return int(size_str[:-2])
        else:
            raise ValueError("Format de taille invalide")
    except ValueError as e:
        raise e
