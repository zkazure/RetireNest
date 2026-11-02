"""profile：把选项解析成计算画像时的错误。"""


class ProfileError(ValueError):
    """选项不存在、取值越界，或推导缺少前置字段。"""
