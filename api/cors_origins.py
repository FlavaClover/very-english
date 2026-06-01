"""Разрешённые origins для CORS (с ``allow_credentials=True`` нельзя использовать ``*``)."""

DEFAULT_CORS_ALLOW_ORIGINS: list[str] = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
    "http://95.163.244.138",
    "https://95.163.244.138",
    "http://95.163.244.138:80",
    "http://95.163.244.138:3000",
    "http://95.163.244.138:5173",
    "http://95.163.244.138:8000",
]
