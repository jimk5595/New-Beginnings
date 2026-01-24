def require_fields(data: dict, fields: list):
    missing = [f for f in fields if f not in data]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
