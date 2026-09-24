# iBAKE

A web-based management system for **iBAKE Cakes & Pastries**. It covers the full bakery workflow, from buying raw materials to production, sales and accounting. Business transactions post their own double-entry journal entries.

## Features

- **Inventory**
  - Raw materials with unit conversion (for example kg to g)
  - Stock-in purchases with expiry dates
  - Movement history, plus low-stock and out-of-stock alerts
- **Recipes & Products**
  - Per-product recipes that define the raw materials each unit uses
- **Production**
  - Single-product or mixed batches, with a check that enough materials are on hand
  - Raw materials consumed first-expiry-first-out (FEFO)
  - Completed batches go into finished goods with an expiry date
  - Cancelled batches can return unused materials to stock or record them as waste
- **Finished Goods**
  - Batch tracking, FEFO sales deduction, and write-off of expired goods
- **Sales**
  - Sales orders with inventory checks and partial payments (New → Open → Paid)
- **Customers & Employees**
  - Records for customers and employees, with a role for each employee
- **Accounting**
  - Chart of accounts and journal entries
  - Payroll, utilities and cash transactions
  - Trial balance, with CSV export
- **Dashboard**
  - Key metrics, expiring goods, recent activity, and a CSV export of items that need restocking

## Tech Stack

- Python 3 / Django 5
- PostgreSQL
- Bootstrap 5, jQuery
- django-crispy-forms, django-filter, django-tables2, django-select2, django-import-export

## Project Structure

```
backend/
├── ibake/                # Project settings and root URLs
├── core/                 # Dashboard, home page, date/time utilities
├── inventory/            # Materials, stock-in, recipes, production, finished goods
├── sales_management/     # Sales orders and payments
├── customer_management/  # Customers
├── employee/             # Employees and roles
├── accounting/           # Accounts, journal entries, payroll, utilities, reports
├── templates/            # HTML templates
├── static/               # CSS and JavaScript
└── manage.py
```

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL

### Installation

1. Clone the repository and enter the backend folder:
   ```bash
   git clone https://github.com/<your-username>/IBAKE.git
   cd IBAKE/backend
   ```

2. Create and activate a virtual environment, then install the dependencies:
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS / Linux
   pip install -r requirements.txt
   ```

3. Create a PostgreSQL database named `ibake`. Then update the `DATABASES` settings in `ibake/settings.py` to match your PostgreSQL user and password.

4. Apply migrations and seed the chart of accounts:
   ```bash
   python manage.py migrate
   python manage.py setup_chart_of_accounts
   python manage.py setup_accounts
   ```

5. Create an admin account and start the server:
   ```bash
   python manage.py createsuperuser
   python manage.py runserver
   ```

6. Open http://127.0.0.1:8000 and log in.

## Management Commands

| Command | Description |
|---|---|
| `setup_chart_of_accounts` | Creates the default chart of accounts |
| `setup_accounts` | Creates or updates additional system accounts |
| `check_expired_goods` | Writes off expired finished goods and records the loss |
| `reset_transactional_data --confirm` | Deletes all transactions but keeps master data (products, materials, employees, customers, accounts) |

## Configuration Notes

`ibake/settings.py` is configured for local development (`DEBUG = True`, local database credentials). Before deploying to production:

- Set a new `SECRET_KEY`
- Set `DEBUG = False`
- Configure `ALLOWED_HOSTS`
- Keep credentials out of source control, for example in environment variables
