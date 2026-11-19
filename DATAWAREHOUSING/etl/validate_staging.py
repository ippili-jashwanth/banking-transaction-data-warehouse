
from sqlalchemy import text
from db_connection import engine

expected_counts = {
    "stg_transactions": 49500,
    "stg_customers": 1100,
    "stg_accounts": 1651,
    "stg_addresses": 1210,
    "stg_branches": 50,
    "stg_customer_types": 3,
    "stg_account_types": 5,
    "stg_account_statuses": 3,
    "stg_transaction_types": 4,
    "stg_loan_statuses": 3,
    "stg_loans": 330,
}

try:
    with engine.connect() as connection:
        print("Staging validation started:\n")

        all_passed = True

        for table_name, expected in expected_counts.items():
            query = text(
                f"SELECT COUNT(*) FROM staging.{table_name}"
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
            "\nAll staging checks passed!"
            if all_passed
            else "\nSome staging checks need attention."
        )

except Exception as e:
    print("Validation failed:", e)

finally:
    engine.dispose()
