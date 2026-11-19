
from sqlalchemy import text
from db_connection import engine

try:
    with engine.connect() as connection:
        version = connection.execute(
            text("SELECT version();")
        ).scalar()

        print("Connected successfully!")
        print(version)

finally:
    engine.dispose()
