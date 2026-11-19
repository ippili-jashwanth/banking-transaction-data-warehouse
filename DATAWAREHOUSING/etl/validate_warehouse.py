
from sqlalchemy import text
from db_connection import engine

expected_counts = {
    "dim_customer": 1100,
    "dim_account": 1651,
    "dim_branch": 50,
    "dim_transaction_type": 4,
    "dim_loan_status": 3,
    "dim_date": 2935,
    "fact_transaction": 49500,
    "fact_loan": 330,
}

try:
    with engine.connect() as connection:
        print("Warehouse validation started:\n")

        all_passed = True

        for table_name, expected in expected_counts.items():
            query = text(
                f"SELECT COUNT(*) FROM warehouse.{table_name}"
            )
            actual = connection.execute(query).scalar()

            passed = actual == expected
            status = "PASS" if passed else "CHECK"

            if not passed:
                all_passed = False

            print(
                f"{table_name}: {actual} rows "
                f"(expected {expected}) - {status}"
            )

        print(
            "\nAll warehouse checks passed!"
            if all_passed
            else "\nSome warehouse checks need attention."
        )

except Exception as e:
    print("Validation failed:", e)

finally:
    engine.dispose()
