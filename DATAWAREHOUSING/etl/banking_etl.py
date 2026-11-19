
from pathlib import Path
import pandas as pd
from sqlalchemy import text
from db_connection import engine

# ============================================================
# 1. CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

EXPECTED_COUNTS = {
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


# ============================================================
# 2. COMMON FUNCTIONS
# ============================================================

def read_csv(file_name):
    path = DATA_DIR / file_name

    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    return pd.read_csv(path)


def standardize_columns(df):
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower()
    return df


def remove_duplicates(df, file_name):
    original = len(df)
    df = df.drop_duplicates().copy()

    print(
        f"{file_name}: original={original}, "
        f"duplicates removed={original - len(df)}, "
        f"remaining={len(df)}"
    )

    return df


def load_to_staging(df, table_name):
    # This replaces a staging table, NOT a warehouse table.
    df.to_sql(
        table_name,
        con=engine,
        schema="staging",
        if_exists="replace",
        index=False,
        chunksize=5000,
        method="multi",
    )

    print(f"{table_name} loaded: {len(df)} rows")


def load_simple_table(file_name, table_name):
    df = read_csv(file_name)
    df = remove_duplicates(df, file_name)
    df = standardize_columns(df)
    load_to_staging(df, table_name)


# ============================================================
# 3. TRANSACTION ETL
# ============================================================

def load_transactions():
    print("\n========== TRANSACTION ETL ==========")

    df = read_csv("transactions.csv")
    print("Original rows:", len(df))

    df = remove_duplicates(df, "transactions.csv")

    required = [
        "TransactionID",
        "AccountOriginID",
        "AccountDestinationID",
        "TransactionTypeID",
        "Amount",
        "TransactionDate",
        "BranchID",
        "Description",
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(
            f"Missing transaction columns: {missing}"
        )

    df["TransactionDate"] = pd.to_datetime(
        df["TransactionDate"],
        errors="coerce"
    ).dt.date

    df = standardize_columns(df)

    print("\nTransaction validation:")

    for col in [
        "transactionid",
        "accountoriginid",
        "accountdestinationid",
        "transactiontypeid",
        "amount",
        "branchid",
    ]:
        print(f"{col}: {df[col].isna().sum()} NULL values")

    print(
        "Missing/invalid dates:",
        df["transactiondate"].isna().sum()
    )

    load_to_staging(df, "stg_transactions")


# ============================================================
# 4. CUSTOMER DOB CLEANING
# ============================================================

def clean_dob(value):
    if pd.isna(value) or str(value).strip() == "":
        return pd.NaT

    value = str(value).strip()

    # Remove time from timestamps.
    if "T" in value:
        value = value.split("T")[0]
    elif " " in value:
        value = value.split(" ")[0]

    # YYYY-MM-DD or YYYY/MM/DD.
    parts = value.replace("/", "-").split("-")

    if len(parts) == 3 and len(parts[0]) == 4:
        try:
            year, month, day = map(int, parts)

            # Repair a clearly swapped month and day.
            if month > 12 and day <= 12:
                month, day = day, month

            return pd.Timestamp(
                year=year, month=month, day=day
            )

        except (ValueError, TypeError, OverflowError):
            return pd.NaT

    # DD.MM.YYYY.
    if "." in value:
        parts = value.split(".")

        if len(parts) == 3:
            try:
                day, month, year = map(int, parts)

                return pd.Timestamp(
                    year=year, month=month, day=day
                )

            except (ValueError, TypeError, OverflowError):
                return pd.NaT

    # DD/MM/YYYY or MM/DD/YYYY.
    if "/" in value:
        parts = value.split("/")

        if len(parts) == 3:
            try:
                first, second, year = map(int, parts)

                if first > 12 and second <= 12:
                    day, month = first, second
                elif second > 12 and first <= 12:
                    month, day = first, second
                else:
                    # Ambiguous dates are interpreted as DD/MM/YYYY.
                    day, month = first, second

                return pd.Timestamp(
                    year=year, month=month, day=day
                )

            except (ValueError, TypeError, OverflowError):
                return pd.NaT

    parsed = pd.to_datetime(value, errors="coerce")

    return parsed if not pd.isna(parsed) else pd.NaT


def load_customers():
    print("\n========== CUSTOMER ETL ==========")

    customers = read_csv("customers.csv")
    print("Original rows:", len(customers))

    customers = remove_duplicates(
        customers, "customers.csv"
    )

    customers = standardize_columns(customers)

    if "dateofbirth" not in customers.columns:
        raise ValueError("customers.csv has no dateofbirth column")

    raw_dob = customers["dateofbirth"].copy()

    customers["dateofbirth"] = raw_dob.apply(clean_dob)

    print("\nCustomer validation:")
    print("NULL customer IDs:", customers["customerid"].isna().sum())
    print("NULL first names:", customers["firstname"].isna().sum())
    print("NULL last names:", customers["lastname"].isna().sum())
    print(
        "Missing/invalid DOB values:",
        customers["dateofbirth"].isna().sum()
    )

    invalid = customers["dateofbirth"].isna()

    if invalid.any():
        print("\nExamples of missing/invalid DOB values:")

        print(
            pd.DataFrame({
                "customerid": customers.loc[
                    invalid, "customerid"
                ],
                "dateofbirth_raw": raw_dob.loc[invalid],
            }).head(10).to_string(index=False)
        )

    load_to_staging(customers, "stg_customers")


# ============================================================
# 5. ACCOUNT ETL
# ============================================================

def load_accounts():
    print("\n========== ACCOUNT ETL ==========")

    accounts = read_csv("accounts.csv")
    print("Original rows:", len(accounts))

    accounts = remove_duplicates(accounts, "accounts.csv")
    accounts = standardize_columns(accounts)

    accounts["openingdate"] = pd.to_datetime(
        accounts["openingdate"],
        errors="coerce"
    ).dt.date

    print("\nAccount validation:")

    for col, label in [
        ("accountid", "NULL account IDs"),
        ("customerid", "NULL customer IDs"),
        ("accounttypeid", "NULL account type IDs"),
        ("accountstatusid", "NULL account status IDs"),
        ("balance", "NULL balances"),
        ("openingdate", "NULL opening dates"),
    ]:
        print(f"{label}: {accounts[col].isna().sum()}")

    load_to_staging(accounts, "stg_accounts")


# ============================================================
# 6. LOAN ETL
# ============================================================

def load_loans():
    print("\n========== LOAN ETL ==========")

    loans = read_csv("loans.csv")
    print("Original rows:", len(loans))

    loans = remove_duplicates(loans, "loans.csv")
    loans = standardize_columns(loans)

    for col in ["startdate", "estimatedenddate"]:
        loans[col] = pd.to_datetime(
            loans[col], errors="coerce"
        ).dt.date

    print("\nLoan validation:")

    for col, label in [
        ("loanid", "NULL loan IDs"),
        ("accountid", "NULL account IDs"),
        ("loanstatusid", "NULL loan status IDs"),
        ("startdate", "NULL start dates"),
        ("estimatedenddate", "NULL estimated end dates"),
        ("principalamount", "NULL principal amounts"),
        ("interestrate", "NULL interest rates"),
    ]:
        print(f"{label}: {loans[col].isna().sum()}")

    load_to_staging(loans, "stg_loans")


# ============================================================
# 7. STAGING ROW-COUNT VALIDATION
# ============================================================

def validate_staging_row_counts():
    print("\n========== STAGING ROW-COUNT VALIDATION ==========")

    all_passed = True

    with engine.connect() as connection:
        for table, expected in EXPECTED_COUNTS.items():
            query = text(
                f"SELECT COUNT(*) FROM staging.{table}"
            )

            actual = connection.execute(query).scalar()

            # Fact-source CSVs may grow as new records arrive. Require at least
            # the known baseline for these two tables; keep exact checks for
            # the current lookup/dimension staging inputs.
            if table in {"stg_transactions", "stg_loans"}:
                passed = actual >= expected
                expectation = f"expected at least {expected}"
            else:
                passed = actual == expected
                expectation = f"expected {expected}"

            all_passed = all_passed and passed
            status = "PASS" if passed else "CHECK"

            print(
                f"{table}: {actual} rows "
                f"({expectation}) - {status}"
            )

    print(
        "\nAll staging row counts passed."
        if all_passed
        else "\nSome staging row counts need attention."
    )

    return all_passed


# ============================================================
# 8. FOREIGN-KEY VALIDATION
# ============================================================

def validate_staging_foreign_keys():
    checks = {
        "Accounts -> Customers": """
            SELECT COUNT(*)
            FROM staging.stg_accounts a
            LEFT JOIN staging.stg_customers c
                ON a.customerid = c.customerid
            WHERE c.customerid IS NULL
        """,

        "Accounts -> Account Types": """
            SELECT COUNT(*)
            FROM staging.stg_accounts a
            LEFT JOIN staging.stg_account_types t
                ON a.accounttypeid = t.accounttypeid
            WHERE t.accounttypeid IS NULL
        """,

        "Accounts -> Account Statuses": """
            SELECT COUNT(*)
            FROM staging.stg_accounts a
            LEFT JOIN staging.stg_account_statuses s
                ON a.accountstatusid = s.accountstatusid
            WHERE s.accountstatusid IS NULL
        """,

        "Loans -> Accounts": """
            SELECT COUNT(*)
            FROM staging.stg_loans l
            LEFT JOIN staging.stg_accounts a
                ON l.accountid = a.accountid
            WHERE a.accountid IS NULL
        """,

        "Loans -> Loan Statuses": """
            SELECT COUNT(*)
            FROM staging.stg_loans l
            LEFT JOIN staging.stg_loan_statuses s
                ON l.loanstatusid = s.loanstatusid
            WHERE s.loanstatusid IS NULL
        """,

        "Transactions -> Origin Accounts": """
            SELECT COUNT(*)
            FROM staging.stg_transactions t
            LEFT JOIN staging.stg_accounts a
                ON t.accountoriginid = a.accountid
            WHERE a.accountid IS NULL
        """,

        "Transactions -> Destination Accounts": """
            SELECT COUNT(*)
            FROM staging.stg_transactions t
            LEFT JOIN staging.stg_accounts a
                ON t.accountdestinationid = a.accountid
            WHERE a.accountid IS NULL
        """,

        "Transactions -> Transaction Types": """
            SELECT COUNT(*)
            FROM staging.stg_transactions t
            LEFT JOIN staging.stg_transaction_types tt
                ON t.transactiontypeid = tt.transactiontypeid
            WHERE tt.transactiontypeid IS NULL
        """,

        "Transactions -> Branches": """
            SELECT COUNT(*)
            FROM staging.stg_transactions t
            LEFT JOIN staging.stg_branches b
                ON t.branchid = b.branchid
            WHERE b.branchid IS NULL
        """,
    }

    print("\n========== STAGING FOREIGN-KEY VALIDATION ==========")

    all_passed = True

    with engine.connect() as connection:
        for label, sql in checks.items():
            invalid = connection.execute(text(sql)).scalar()
            passed = invalid == 0
            all_passed = all_passed and passed

            print(
                f"{label}: {invalid} invalid references - "
                f"{'PASS' if passed else 'CHECK'}"
            )

    return all_passed




# ============================================================
# 9. WAREHOUSE INCREMENTAL FACT LOADING
# ============================================================

TRANSACTION_INSERT_SQL = """
    INSERT INTO warehouse.fact_transaction (
        transaction_id,
        date_key,
        origin_account_key,
        destination_account_key,
        transaction_type_key,
        branch_key,
        amount
    )
    SELECT
        st.transactionid,
        CASE
            WHEN st.transactiondate IS NULL THEN 0
            ELSE TO_CHAR(st.transactiondate, 'YYYYMMDD')::INT
        END,
        da_origin.account_key,
        da_dest.account_key,
        dtt.transaction_type_key,
        db.branch_key,
        st.amount::NUMERIC(15,2)
    FROM staging.stg_transactions st
    JOIN warehouse.dim_account da_origin
        ON da_origin.account_id = st.accountoriginid
    JOIN warehouse.dim_account da_dest
        ON da_dest.account_id = st.accountdestinationid
    JOIN warehouse.dim_transaction_type dtt
        ON dtt.transaction_type_id = st.transactiontypeid
    JOIN warehouse.dim_branch db
        ON db.branch_id = st.branchid
    ON CONFLICT (transaction_id) DO NOTHING
"""

LOAN_INSERT_SQL = """
    INSERT INTO warehouse.fact_loan (
        loan_id,
        account_key,
        loan_status_key,
        start_date_key,
        estimated_end_date_key,
        principal_amount,
        interest_rate
    )
    SELECT
        sl.loanid,
        da.account_key,
        dls.loan_status_key,
        CASE
            WHEN sl.startdate IS NULL THEN 0
            ELSE TO_CHAR(sl.startdate, 'YYYYMMDD')::INT
        END,
        CASE
            WHEN sl.estimatedenddate IS NULL THEN 0
            ELSE TO_CHAR(sl.estimatedenddate, 'YYYYMMDD')::INT
        END,
        sl.principalamount::NUMERIC(15,2),
        sl.interestrate::NUMERIC(8,6)
    FROM staging.stg_loans sl
    JOIN warehouse.dim_account da
        ON da.account_id = sl.accountid
    JOIN warehouse.dim_loan_status dls
        ON dls.loan_status_id = sl.loanstatusid
    ON CONFLICT (loan_id) DO NOTHING
"""


def validate_warehouse_mappings(connection):
    """Fail before inserting if staging rows cannot map to warehouse dimensions."""
    checks = {
        "transactions -> origin account": """
            SELECT COUNT(*)
            FROM staging.stg_transactions st
            LEFT JOIN warehouse.dim_account d
                ON d.account_id = st.accountoriginid
            WHERE d.account_key IS NULL
        """,
        "transactions -> destination account": """
            SELECT COUNT(*)
            FROM staging.stg_transactions st
            LEFT JOIN warehouse.dim_account d
                ON d.account_id = st.accountdestinationid
            WHERE d.account_key IS NULL
        """,
        "transactions -> transaction type": """
            SELECT COUNT(*)
            FROM staging.stg_transactions st
            LEFT JOIN warehouse.dim_transaction_type d
                ON d.transaction_type_id = st.transactiontypeid
            WHERE d.transaction_type_key IS NULL
        """,
        "transactions -> branch": """
            SELECT COUNT(*)
            FROM staging.stg_transactions st
            LEFT JOIN warehouse.dim_branch d
                ON d.branch_id = st.branchid
            WHERE d.branch_key IS NULL
        """,
        "transactions -> date dimension": """
            SELECT COUNT(*)
            FROM staging.stg_transactions st
            LEFT JOIN warehouse.dim_date d
                ON d.date_key = CASE
                    WHEN st.transactiondate IS NULL THEN 0
                    ELSE TO_CHAR(st.transactiondate, 'YYYYMMDD')::INT
                END
            WHERE d.date_key IS NULL
        """,
        "loans -> account": """
            SELECT COUNT(*)
            FROM staging.stg_loans sl
            LEFT JOIN warehouse.dim_account d
                ON d.account_id = sl.accountid
            WHERE d.account_key IS NULL
        """,
        "loans -> loan status": """
            SELECT COUNT(*)
            FROM staging.stg_loans sl
            LEFT JOIN warehouse.dim_loan_status d
                ON d.loan_status_id = sl.loanstatusid
            WHERE d.loan_status_key IS NULL
        """,
        "loans -> start date dimension": """
            SELECT COUNT(*)
            FROM staging.stg_loans sl
            LEFT JOIN warehouse.dim_date d
                ON d.date_key = CASE
                    WHEN sl.startdate IS NULL THEN 0
                    ELSE TO_CHAR(sl.startdate, 'YYYYMMDD')::INT
                END
            WHERE d.date_key IS NULL
        """,
        "loans -> estimated end date dimension": """
            SELECT COUNT(*)
            FROM staging.stg_loans sl
            LEFT JOIN warehouse.dim_date d
                ON d.date_key = CASE
                    WHEN sl.estimatedenddate IS NULL THEN 0
                    ELSE TO_CHAR(sl.estimatedenddate, 'YYYYMMDD')::INT
                END
            WHERE d.date_key IS NULL
        """,
    }

    print("\\n========== WAREHOUSE DIMENSION-MAPPING VALIDATION ==========")
    all_passed = True
    for label, sql in checks.items():
        invalid = connection.execute(text(sql)).scalar()
        passed = invalid == 0
        all_passed = all_passed and passed
        print(f"{label}: {invalid} invalid references - {'PASS' if passed else 'CHECK'}")

    if not all_passed:
        raise RuntimeError(
            "Warehouse dimension mapping validation failed. "
            "No fact-table inserts were attempted. Fix the missing mappings first."
        )


def load_warehouse_facts_incrementally():
    """Append new transaction and loan facts; never truncate warehouse fact tables."""
    print("\\n========== WAREHOUSE INCREMENTAL FACT LOAD ==========")

    with engine.begin() as connection:
        # ON CONFLICT requires these unique indexes, created and tested in pgAdmin.
        required_indexes = {
            "ux_fact_transaction_transaction_id",
            "ux_fact_loan_loan_id",
        }
        found_indexes = set(connection.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'warehouse'
              AND indexname IN (
                  'ux_fact_transaction_transaction_id',
                  'ux_fact_loan_loan_id'
              )
        """)).scalars().all())
        missing_indexes = required_indexes - found_indexes
        if missing_indexes:
            raise RuntimeError(
                "Required unique index(es) missing: "
                + ", ".join(sorted(missing_indexes))
                + ". Create them in PostgreSQL before running the warehouse load."
            )

        validate_warehouse_mappings(connection)

        transaction_result = connection.execute(text(TRANSACTION_INSERT_SQL))
        loan_result = connection.execute(text(LOAN_INSERT_SQL))

        print(f"New transactions inserted: {transaction_result.rowcount}")
        print(f"New loans inserted: {loan_result.rowcount}")

        # Confirm counts and business-key uniqueness in the same transaction.
        transaction_count = connection.execute(text("""
            SELECT COUNT(*) FROM warehouse.fact_transaction
        """)).scalar_one()
        transaction_unique = connection.execute(text("""
            SELECT COUNT(DISTINCT transaction_id)
            FROM warehouse.fact_transaction
        """)).scalar_one()
        loan_count = connection.execute(text("""
            SELECT COUNT(*) FROM warehouse.fact_loan
        """)).scalar_one()
        loan_unique = connection.execute(text("""
            SELECT COUNT(DISTINCT loan_id)
            FROM warehouse.fact_loan
        """)).scalar_one()

        print(f"Transactions: total={transaction_count}, unique IDs={transaction_unique}")
        print(f"Loans: total={loan_count}, unique IDs={loan_unique}")

        if transaction_count != transaction_unique:
            raise RuntimeError("Duplicate transaction IDs detected after loading.")
        if loan_count != loan_unique:
            raise RuntimeError("Duplicate loan IDs detected after loading.")

    print("Warehouse incremental fact load completed successfully.")


# ============================================================
# 10. MAIN PIPELINE
# ============================================================

def main():
    print("=" * 60)
    print("BANKING DATA WAREHOUSE - STAGING + INCREMENTAL FACT ETL")
    print("=" * 60)

    with engine.connect() as connection:
        version = connection.execute(
            text("SELECT version()")
        ).scalar()

        schema_exists = connection.execute(text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.schemata
                WHERE schema_name = 'staging'
            )
        """)).scalar()

    print("\nConnected successfully!")
    print(version)

    if not schema_exists:
        raise RuntimeError(
            "The staging schema does not exist. "
            "Create it in PostgreSQL before running this ETL."
        )

    print(
        "\nNOTE: Staging tables are refreshed from CSVs. "
        "Warehouse fact tables are append-only and use conflict-safe incremental loading."
    )

    # Lookup tables and other simple tables.
    load_simple_table("branches.csv", "stg_branches")
    load_simple_table("customer_types.csv", "stg_customer_types")
    load_simple_table("account_types.csv", "stg_account_types")
    load_simple_table("account_statuses.csv", "stg_account_statuses")
    load_simple_table("transaction_types.csv", "stg_transaction_types")
    load_simple_table("loan_statuses.csv", "stg_loan_statuses")
    load_simple_table("addresses.csv", "stg_addresses")

    # Main source tables.
    load_customers()
    load_accounts()
    load_loans()
    load_transactions()

    counts_ok = validate_staging_row_counts()
    foreign_keys_ok = validate_staging_foreign_keys()

    if not counts_ok or not foreign_keys_ok:
        raise RuntimeError(
            "Staging validation failed. Warehouse fact loading was skipped."
        )

    # Only append new facts after all staging validations pass.
    load_warehouse_facts_incrementally()

    print("\n" + "=" * 60)
    print("BANKING DATA WAREHOUSE ETL COMPLETED: ALL CHECKS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("\nSTAGING ETL FAILED:", exc)
        raise
    finally:
        engine.dispose()
