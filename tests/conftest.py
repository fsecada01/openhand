import os

# sqlmodel_crud_utils resolves its SQL dialect at import time.
os.environ.setdefault("SQL_DIALECT", "sqlite")
