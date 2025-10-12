def set_attr_if_cond(new_value, cond, instance, field_name):
    old_value = getattr(instance, field_name)
    if old_value is None and (cond == ">" or cond == "<"):
        old_value = 0
    match cond:
        case ">":
            if new_value <= old_value:
                return False
        case "<":
            if new_value >= old_value:
                return False
        case "!=":
            if new_value == old_value:
                return False
        case _:
            raise ValueError(f"Unknown condition: {cond}")
    setattr(instance, field_name, new_value)
    instance.update_fields.add(field_name)
    return True
