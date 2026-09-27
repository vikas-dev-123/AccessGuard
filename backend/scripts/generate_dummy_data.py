"""
Generates synthetic HR + banking-system user data for "Apex Bank" (a fictional
bank) so that AccessGuard's audit checks have realistic data to run against.

Produces, in backend/data/:
    hr_employees.csv
    core_banking_users.csv
    loan_system_users.csv
    database_users.csv

Every run is deterministic (seeded) and deliberately plants 15-25 exceptions
of each type the Phase 2 audit checks look for. See the EXCEPTION SUMMARY
printed at the end of the run for exact counts.

Note on schema: alongside the columns requested in the spec
(user_id, employee_id, username, role, account_status, created_date,
last_login_date), each system CSV also carries a `status_last_updated`
column. It records when `account_status` last changed, which is what the
"late revocation" check needs to measure how long after termination an
account was actually disabled.
"""
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

SEED = 42
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

TODAY = date(2026, 9, 27)

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
SOD_RULES_PATH = BACKEND_DIR / "config" / "sod_rules.json"

N_EMPLOYEES = 200

DEPARTMENTS = ["Retail Banking", "Loans", "Treasury", "IT", "Operations", "Finance"]

DESIGNATIONS_BY_DEPT = {
    "Retail Banking": ["Teller", "Customer Service Officer", "Relationship Manager", "Branch Operations Manager", "Branch Manager"],
    "Loans": ["Loan Officer", "Credit Analyst", "Underwriter", "Loan Processing Manager", "Loans Manager"],
    "Treasury": ["Treasury Analyst", "Treasury Manager", "Fund Manager", "Investment Officer"],
    "IT": ["Software Engineer", "System Administrator", "Database Administrator", "IT Support Specialist", "Network Engineer", "IT Manager"],
    "Operations": ["Operations Officer", "Back Office Executive", "Reconciliation Officer", "Operations Manager"],
    "Finance": ["Financial Analyst", "Accountant", "Finance Manager", "Controller"],
}

CORE_BANKING_ROLES = ["Teller", "Branch Manager", "Account Opener", "Transaction Approver", "Admin"]
LOAN_SYSTEM_ROLES = ["Loan Creator", "Loan Approver", "Credit Analyst", "Disbursement Officer", "Admin"]
DATABASE_ROLES = ["Read Only", "Developer", "DBA"]

GENERIC_USERNAMES = [
    "admin", "test", "temp", "teller01", "shared", "admin2", "testuser",
    "temp_user", "shared_acct", "backup_admin", "training", "demo",
]

PRIVILEGED_ROLES = {"Admin", "DBA"}

DORMANT_DAYS_THRESHOLD = 90


def rand_date(start: date, end: date) -> date:
    if end <= start:
        return start
    delta_days = (end - start).days
    return start + timedelta(days=random.randint(0, delta_days))


def recent_login(created: date) -> date:
    return rand_date(max(created, TODAY - timedelta(days=45)), TODAY)


def make_username(name: str, taken: set) -> str:
    parts = name.lower().replace(".", "").replace("'", "").split()
    base = f"{parts[0]}.{parts[-1]}" if len(parts) > 1 else parts[0]
    username = base
    suffix = 1
    while username in taken:
        suffix += 1
        username = f"{base}{suffix}"
    taken.add(username)
    return username


class Employee:
    def __init__(self, employee_id, name, department, designation, status, joining_date, termination_date):
        self.employee_id = employee_id
        self.name = name
        self.department = department
        self.designation = designation
        self.status = status
        self.joining_date = joining_date
        self.termination_date = termination_date

    def to_row(self):
        return {
            "employee_id": self.employee_id,
            "name": self.name,
            "department": self.department,
            "designation": self.designation,
            "status": self.status,
            "joining_date": self.joining_date.isoformat(),
            "termination_date": self.termination_date.isoformat() if self.termination_date else "",
        }


def generate_employees(n: int) -> list:
    employees = []
    for i in range(1, n + 1):
        employee_id = f"EMP{i:04d}"
        name = fake.name()
        department = random.choice(DEPARTMENTS)
        designation = random.choice(DESIGNATIONS_BY_DEPT[department])

        joining_date = rand_date(TODAY - timedelta(days=8 * 365), TODAY - timedelta(days=30))

        is_terminated = random.random() < 0.30
        if is_terminated:
            status = "Terminated"
            earliest_term = joining_date + timedelta(days=60)
            termination_date = rand_date(min(earliest_term, TODAY - timedelta(days=1)), TODAY - timedelta(days=1))
        else:
            status = "Active"
            termination_date = None

        employees.append(Employee(employee_id, name, department, designation, status, joining_date, termination_date))
    return employees


class Account:
    _counters = {}

    def __init__(self, system_prefix, employee_id, username, role, account_status,
                 created_date, last_login_date, status_last_updated):
        cls = type(self)
        cls._counters[system_prefix] = cls._counters.get(system_prefix, 0) + 1
        self.user_id = f"{system_prefix}-{cls._counters[system_prefix]:04d}"
        self.employee_id = employee_id
        self.username = username
        self.role = role
        self.account_status = account_status
        self.created_date = created_date
        self.last_login_date = last_login_date
        self.status_last_updated = status_last_updated

    def to_row(self):
        return {
            "user_id": self.user_id,
            "employee_id": self.employee_id or "",
            "username": self.username,
            "role": self.role,
            "account_status": self.account_status,
            "created_date": self.created_date.isoformat() if self.created_date else "",
            "last_login_date": self.last_login_date.isoformat() if self.last_login_date else "",
            "status_last_updated": self.status_last_updated.isoformat() if self.status_last_updated else "",
        }


def build_baseline_account(system_prefix, employee: Employee, role: str, taken_usernames: set) -> Account:
    username = make_username(employee.name, taken_usernames)
    created_date = employee.joining_date + timedelta(days=random.randint(0, 5))

    if employee.status == "Terminated":
        account_status = "Disabled"
        status_last_updated = employee.termination_date + timedelta(days=random.randint(0, 1))
        last_login_date = rand_date(created_date, employee.termination_date)
    else:
        account_status = "Active"
        status_last_updated = created_date
        last_login_date = recent_login(created_date)

    return Account(system_prefix, employee.employee_id, username, role, account_status,
                    created_date, last_login_date, status_last_updated)


def build_baseline_accounts(system_prefix, eligible_employees, role_for_employee_fn, taken_usernames):
    return [
        build_baseline_account(system_prefix, emp, role_for_employee_fn(emp), taken_usernames)
        for emp in eligible_employees
    ]


def add_extra_account(system_prefix, employee: Employee, role: str, taken_usernames: set,
                       account_status="Active", last_login_date=None) -> Account:
    username = make_username(employee.name, taken_usernames)
    created_date = employee.joining_date + timedelta(days=random.randint(5, 60))
    if last_login_date is None:
        last_login_date = recent_login(created_date)
    return Account(system_prefix, employee.employee_id, username, role, account_status,
                    created_date, last_login_date, created_date)


def non_privileged(roles):
    return [r for r in roles if r not in PRIVILEGED_ROLES]


def pick_sample(pool, n, exclude=frozenset()):
    candidates = [x for x in pool if x not in exclude]
    n = min(n, len(candidates))
    return random.sample(candidates, n)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(SOD_RULES_PATH) as f:
        sod_rules = json.load(f)["rules"]

    employees = generate_employees(N_EMPLOYEES)
    employees_by_id = {e.employee_id: e for e in employees}
    active_employees = [e for e in employees if e.status == "Active"]
    terminated_employees = [e for e in employees if e.status == "Terminated"]

    by_dept = {}
    for e in employees:
        by_dept.setdefault(e.department, []).append(e)

    usernames = {"core_banking": set(), "loan_system": set(), "database": set()}

    # ---- Baseline accounts (no exceptions yet) -----------------------------

    core_eligible = by_dept.get("Retail Banking", []) + by_dept.get("Operations", [])

    def core_role_for(emp):
        return random.choice(["Teller", "Teller", "Teller", "Account Opener", "Transaction Approver", "Branch Manager"])

    core_accounts = build_baseline_accounts("CB", core_eligible, core_role_for, usernames["core_banking"])

    loan_eligible = by_dept.get("Loans", [])

    def loan_role_for(emp):
        return random.choice(["Loan Creator", "Loan Creator", "Credit Analyst", "Loan Approver", "Disbursement Officer"])

    loan_accounts = build_baseline_accounts("LN", loan_eligible, loan_role_for, usernames["loan_system"])

    it_employees = by_dept.get("IT", [])

    def db_role_for(emp):
        return random.choices(["Read Only", "Developer", "DBA"], weights=[3, 5, 1])[0]

    db_accounts = build_baseline_accounts("DB", it_employees, db_role_for, usernames["database"])

    # Treasury and Finance staff query the database for reporting.
    reporting_users = by_dept.get("Treasury", []) + by_dept.get("Finance", [])
    db_accounts += build_baseline_accounts("DB", reporting_users, lambda emp: "Read Only", usernames["database"])

    # A handful of IT staff legitimately hold Admin access in the business
    # systems for support purposes -- privileged, but not an exception since
    # they sit inside IT.
    for emp in pick_sample([e for e in it_employees if e.status == "Active"], 4):
        core_accounts.append(add_extra_account("CB", emp, "Admin", usernames["core_banking"]))
    for emp in pick_sample([e for e in it_employees if e.status == "Active"], 3):
        loan_accounts.append(add_extra_account("LN", emp, "Admin", usernames["loan_system"]))

    exception_counts = {}

    # ---- 1. Terminated users with active access -----------------------------
    target_n = random.randint(15, 25)
    pool = [a for a in core_accounts + loan_accounts + db_accounts
            if a.employee_id and employees_by_id[a.employee_id].status == "Terminated"
            and a.account_status == "Disabled"]
    chosen = pick_sample(pool, target_n)
    for a in chosen:
        a.account_status = "Active"
        a.status_last_updated = a.created_date
        a.last_login_date = recent_login(a.created_date)
    exception_counts["terminated_active_access"] = len(chosen)

    # ---- 2. Late revocation --------------------------------------------------
    target_n = random.randint(15, 25)
    remaining_disabled = [a for a in core_accounts + loan_accounts + db_accounts
                           if a.employee_id and employees_by_id[a.employee_id].status == "Terminated"
                           and a.account_status == "Disabled"
                           and a not in chosen]
    late_chosen = pick_sample(remaining_disabled, target_n)
    for a in late_chosen:
        emp = employees_by_id[a.employee_id]
        delay = timedelta(days=random.randint(2, 45))
        new_update = emp.termination_date + delay
        if new_update > TODAY:
            new_update = TODAY
        a.status_last_updated = new_update
    exception_counts["late_revocation"] = len(late_chosen)

    # ---- 3. Orphan accounts (no matching HR employee) ------------------------
    target_n = random.randint(15, 25)
    orphan_specs = [
        ("core_banking", core_accounts, "CB", CORE_BANKING_ROLES),
        ("loan_system", loan_accounts, "LN", LOAN_SYSTEM_ROLES),
        ("database", db_accounts, "DB", DATABASE_ROLES),
    ]
    orphan_count = 0
    for i in range(target_n):
        system_name, accounts_list, prefix, roles = random.choice(orphan_specs)
        fake_name = fake.name()
        username = make_username(fake_name, usernames[system_name])
        created_date = rand_date(TODAY - timedelta(days=5 * 365), TODAY - timedelta(days=10))
        acct = Account(prefix, None, username, random.choice(non_privileged(roles)), "Active",
                        created_date, recent_login(created_date), created_date)
        accounts_list.append(acct)
        orphan_count += 1
    exception_counts["orphan_accounts"] = orphan_count

    # ---- 4. Generic / shared accounts -----------------------------------------
    target_n = random.randint(15, 25)
    generic_specs = [
        ("core_banking", core_accounts, "CB", CORE_BANKING_ROLES),
        ("loan_system", loan_accounts, "LN", LOAN_SYSTEM_ROLES),
        ("database", db_accounts, "DB", DATABASE_ROLES),
    ]
    generic_count = 0
    used_generic_names = set()
    for i in range(target_n):
        system_name, accounts_list, prefix, roles = random.choice(generic_specs)
        base_name = random.choice(GENERIC_USERNAMES)
        key = (system_name, base_name)
        if key in used_generic_names:
            base_name = f"{base_name}{random.randint(2, 99)}"
        used_generic_names.add(key)
        username = base_name
        suffix = 1
        while username in usernames[system_name]:
            suffix += 1
            username = f"{base_name}{suffix}"
        usernames[system_name].add(username)

        # Shared accounts usually have a named custodian in HR, so they are
        # not also orphans -- the finding is the shared username itself.
        employee_id = random.choice(active_employees).employee_id
        created_date = rand_date(TODAY - timedelta(days=4 * 365), TODAY - timedelta(days=10))
        acct = Account(prefix, employee_id, username, random.choice(non_privileged(roles)), "Active",
                        created_date, recent_login(created_date), created_date)
        accounts_list.append(acct)
        generic_count += 1
    exception_counts["generic_shared_accounts"] = generic_count

    # ---- 5. Privileged access outside IT ---------------------------------------
    target_n = random.randint(15, 25)
    non_it_active = [e for e in active_employees if e.department != "IT"]
    chosen_priv = pick_sample(non_it_active, target_n)
    priv_count = 0
    for emp in chosen_priv:
        if random.random() < 0.5:
            core_accounts.append(add_extra_account("CB", emp, "Admin", usernames["core_banking"]))
        else:
            db_accounts.append(add_extra_account("DB", emp, "DBA", usernames["database"]))
        priv_count += 1
    exception_counts["privileged_access_outside_it"] = priv_count

    # ---- 6. Segregation of Duties conflicts -------------------------------------
    target_n = random.randint(15, 25)
    sod_pool = [e for e in active_employees if e.department in ("Loans", "Retail Banking", "IT")]
    chosen_sod = pick_sample(sod_pool, target_n)
    system_map = {
        "core_banking": ("CB", core_accounts, usernames["core_banking"]),
        "loan_system": ("LN", loan_accounts, usernames["loan_system"]),
        "database": ("DB", db_accounts, usernames["database"]),
    }
    sod_count = 0
    for emp in chosen_sod:
        rule = random.choice(sod_rules)
        role_a, role_b = rule["conflicting_roles"]
        for role_spec in (role_a, role_b):
            prefix, accounts_list, taken = system_map[role_spec["system"]]
            already_has = any(a.employee_id == emp.employee_id and a.role == role_spec["role"] for a in accounts_list)
            if not already_has:
                accounts_list.append(add_extra_account(prefix, emp, role_spec["role"], taken))
        sod_count += 1
    exception_counts["sod_conflicts"] = sod_count

    # ---- 7. Dormant accounts -----------------------------------------------------
    target_n = random.randint(15, 25)
    dormant_pool = [a for a in core_accounts + loan_accounts + db_accounts if a.account_status == "Active"]
    dormant_chosen = pick_sample(dormant_pool, target_n)
    for a in dormant_chosen:
        a.last_login_date = TODAY - timedelta(days=random.randint(DORMANT_DAYS_THRESHOLD + 1, 400))
    exception_counts["dormant_accounts"] = len(dormant_chosen)

    # ---- Write CSVs ----------------------------------------------------------

    def write_csv(path, rows, fieldnames):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    write_csv(
        DATA_DIR / "hr_employees.csv",
        [e.to_row() for e in employees],
        ["employee_id", "name", "department", "designation", "status", "joining_date", "termination_date"],
    )

    account_fields = ["user_id", "employee_id", "username", "role", "account_status",
                       "created_date", "last_login_date", "status_last_updated"]
    write_csv(DATA_DIR / "core_banking_users.csv", [a.to_row() for a in core_accounts], account_fields)
    write_csv(DATA_DIR / "loan_system_users.csv", [a.to_row() for a in loan_accounts], account_fields)
    write_csv(DATA_DIR / "database_users.csv", [a.to_row() for a in db_accounts], account_fields)

    print(f"Generated {len(employees)} employees "
          f"({len(active_employees)} active, {len(terminated_employees)} terminated)")
    print(f"  core_banking_users.csv : {len(core_accounts)} accounts")
    print(f"  loan_system_users.csv  : {len(loan_accounts)} accounts")
    print(f"  database_users.csv     : {len(db_accounts)} accounts")
    print("\nPlanted exceptions:")
    for check, count in exception_counts.items():
        print(f"  {check:30s}: {count}")
    print(f"\nFiles written to {DATA_DIR}")


if __name__ == "__main__":
    main()
