def sanitize_db_output(value):
    if type(value) in (int, float):
        return value
    if type(value) is str:
        return value.strip()
