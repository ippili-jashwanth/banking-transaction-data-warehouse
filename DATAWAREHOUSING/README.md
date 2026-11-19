# Banking Transaction Analytics Data Warehouse

## Project Overview

An end-to-end Banking Transaction Analytics Data Warehouse built using Python, Pandas, PostgreSQL, and SQL.

The project transforms raw banking transaction, customer, account, and loan data into a structured analytical warehouse using Kimball dimensional modelling and a Star Schema. It supports analysis of customer behaviour, transaction trends, account activity, loan performance, and customer segmentation.

## Tech Stack

- **Programming:** Python, Pandas
- **Database:** PostgreSQL
- **ETL:** SQLAlchemy, psycopg2
- **Data Modelling:** Kimball Dimensional Modelling, Star Schema
- **Data Warehousing:** Fact and Dimension Tables, SCD Type 2, Surrogate Keys
- **Tools:** VS Code, pgAdmin, draw.io

## ETL Architecture

The pipeline follows this workflow:

1. Extract source data from CSV files.
2. Clean and transform data using Python and Pandas.
3. Remove duplicates and standardise date fields.
4. Load processed data into PostgreSQL staging tables.
5. Validate staging row counts and foreign-key references.
6. Map staging records to warehouse dimensions.
7. Incrementally load transaction and loan fact tables.
8. Validate warehouse records and prevent duplicate fact entries.

## Data Warehouse Design

The warehouse follows a **Star Schema** with two fact tables and six dimension tables.

### Fact Tables

- **fact_transaction:** Stores transaction-level information including amount, transaction date, origin and destination accounts, transaction type, and branch.
- **fact_loan:** Stores loan-level information including principal amount, interest rate, loan status, account, and relevant dates.

### Dimension Tables

- **dim_customer**
- **dim_account**
- **dim_date**
- **dim_branch**
- **dim_transaction_type**
- **dim_loan_status**

Customer history is tracked using **Slowly Changing Dimension Type 2 (SCD Type 2)**. Surrogate keys are used to connect fact records with warehouse dimensions.

## ETL Features

- Duplicate record removal
- Date cleaning and standardisation
- Staging table validation
- Foreign-key reference validation
- Warehouse dimension mapping validation
- Incremental fact loading
- Duplicate prevention using unique business-key constraints
- Post-load row-count and uniqueness checks

## Data Volume

### Staging Layer

| Table | Records |
|---|---:|
| Transactions | 49,500 |
| Customers | 1,100 |
| Accounts | 1,651 |
| Loans | 330 |
| Branches | 50 |
| **Total across 11 staging tables** | **54,642** |

### Data Warehouse

| Table | Records |
|---|---:|
| dim_customer | 1,100 |
| dim_account | 1,651 |
| dim_branch | 50 |
| dim_transaction_type | 4 |
| dim_loan_status | 3 |
| dim_date | 2,935 |
| fact_transaction | 49,500 |
| fact_loan | 330 |
| **Total across 8 warehouse tables** | **55,573** |

## Analytics Performed

The warehouse supports analytical queries covering:

- Transaction trends and transaction volumes
- Transaction amount and count by transaction type
- Customer transaction behaviour
- Account activity by account type and status
- Loan analysis by status and principal amount
- **RFM customer segmentation**
- **Customer cohort retention analysis**

## Project Structure

```text
banking-data-warehouse/
├── data/                 # Raw CSV data (excluded from Git)
├── etl/                  # Python ETL and validation scripts
├── diagrams/              # Star schema and ETL architecture
│   ├── banking_star_schema.drawio
│   ├── banking_star_schema.png
│   ├── banking_etl_architecture.drawio
│   └── banking_etl_architecture.png
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup

1. Clone the repository.
2. Navigate to the project directory.
3. Create and activate a Python virtual environment.
4. Install the required dependencies:

```bash
pip install -r requirements.txt
```

5. Create a PostgreSQL database named `banking_dw`.
6. Configure database credentials in a local `.env` file.
7. Place the required source CSV files inside the `data/` directory.
8. Run the ETL pipeline:

```bash
python etl/banking_etl.py
```

9. Validate the warehouse:

```bash
python etl/validate_warehouse.py
```

> **Note:** The ETL pipeline requires the PostgreSQL staging and warehouse schemas, dimension tables, and required database constraints to be set up beforehand.

## Data Source

[Finance Fraud & Loans Dataset – TestDataBox](https://www.kaggle.com/datasets/testdatabox/finance-fraud-and-loans-dataset-testdatabox)

## Project Status

- [x] Data cleaning and staging ETL
- [x] Staging validation
- [x] Star schema implementation
- [x] SCD Type 2 implementation
- [x] Incremental fact loading
- [x] Warehouse validation
- [x] Analytical queries
- [x] RFM segmentation
- [x] Cohort retention analysis
- [x] Star schema diagram
- [x] ETL architecture diagram
- [ ] GitHub publishing
