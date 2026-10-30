"""Background activity of generator v1 (PHASE-3.md 7.2.4).

Every eligible base organisation (or the share `BackgroundConfig.share` of them, chosen by a hash
of the seed and the organisation's id, so the choice draws nothing from any stream) gets an account
and the ordinary activity of a UK business for the whole period, calibrated as
`synthetic-transactions.md` section 2 describes (the values below are the defaults of
`BackgroundConfig`; every one is a documented assumption or a published figure): payroll on the
last working day (most businesses have no employees), PAYE on the 22nd of the next month, VAT a
month and seven days after each quarter, rent on the first working day, supplier payment runs,
customer receipts, card settlements and cash banking for the sectors that take them, and sometimes
a loan. Employees pay rent, shop by card and draw cash. Times follow London working hours and bank
holidays, stored in UTC.

Payments only ever join a base organisation and a synthetic counterparty, or two synthetic
counterparties: never two base entities (I16). The background of a base organisation is a plain
profile with nothing typology-shaped in it (no cash just under a threshold, no pass-through, no
cycles, no quiet gap followed by a burst), as `synthetic-transactions.md` 2.8 recommends.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from neonradar_ingest.synth.ctx import Ctx
from neonradar_ingest.synth.dates import at, last_working_day, previous_working_day, working_days

CARD_SECTORS = frozenset(
    {"retail", "hospitality", "restaurant", "tourism", "convenience store", "car wash"}
)
CASH_SECTORS = frozenset(
    {"retail", "hospitality", "restaurant", "car wash", "convenience store", "tourism"}
)
SEASONAL_SECTORS = frozenset({"tourism"})


@dataclass(frozen=True, slots=True)
class BackgroundConfig:
    banks: int = 3
    branches_per_bank: int = 4
    no_employee_share: float = 0.70  # 75 percent of UK businesses have no employees (S42)
    small_employer_share: float = 0.25  # 1 to 9 employees; the rest employ 10 to 30
    suppliers: tuple[int, int] = (2, 6)
    customers: tuple[int, int] = (1, 4)
    pool_ratio: float = 0.2
    salary_median: float = 2300.0  # net a month; full-time median net about 2,636 (S39, S48)
    salary_sigma: float = 0.35
    rent_median: float = 1500.0
    supplier_median: float = 1800.0
    customer_median: float = 3200.0
    card_settlement_median: float = 850.0
    cash_deposit_median: float = 1200.0
    cash_banking_days: tuple[int, int] = (1, 5)  # times a week a cash business banks its takings
    loan_share: float = 0.08
    refund_share: float = 0.05
    person_rent_share: float = 0.6
    person_rent_median: float = 1400.0  # UK average rent, August 2026 (S40)
    person_cards: tuple[int, int] = (2, 6)  # a month; fewer than the UK rate, to bound volume
    card_median: float = 15.0  # debit card median assumed; mean about 29 (S30)
    card_sigma: float = 1.16
    cash_withdrawal_median: float = 100.0  # Post Office mean withdrawal about 140 (S49)
    personal: bool = True
    scale: float = 1.0
    share: float = (
        1.0  # of eligible organisations with an account and activity (7.11: real profiles)
    )
    spend_share: tuple[float, float] = (
        0.85,
        0.97,
    )  # outflows over inflows for a business (assumption)


@dataclass(frozen=True, slots=True)
class BaseOrg:
    id: str
    sector: str
    incorporated: str
    accounts_category: str


def _amount(rng: np.random.Generator, median: float, sigma: float) -> float:
    return round(max(1.0, float(median * np.exp(sigma * rng.standard_normal()))), 2)


def _opened(rng: np.random.Generator, period_start: date, incorporated: str) -> date:
    opened = period_start - timedelta(days=int(rng.integers(90, 3650)))
    if len(incorporated) == 10:
        inc = date.fromisoformat(incorporated)
        if inc + timedelta(days=60) > opened:
            opened = inc + timedelta(
                days=int(rng.integers(0, 61))
            )  # 0 to 60 days after incorporation
    return opened


def setup_banks(ctx: Ctx, cfg: BackgroundConfig) -> None:
    """Synthetic banks with cash ledger accounts at their branches (C1 `cash_ledger`)."""
    opened = ctx.period.start.date() - timedelta(days=5000)
    words = ("One", "Two", "Three", "Four", "Five")
    for b in range(cfg.banks):
        bank = ctx.organization(f"bank|{b}", f"Synthetic Bank {words[b % 5]} plc")
        for k in range(cfg.branches_per_bank):
            ctx.branches.append(
                ctx.account(
                    f"branch|{b}|{k}",
                    bank,
                    opened=opened,
                    kind="cash_ledger",
                    bank=f"Synthetic Bank {words[b % 5]}",
                )
            )


class Pools:
    """Synthetic counterparties shared by the base organisations, each with one account."""

    def __init__(self, ctx: Ctx, n_orgs: int, cfg: BackgroundConfig) -> None:
        rng = ctx.rng("pools")
        start = ctx.period.start.date()
        size = max(5, int(n_orgs * cfg.pool_ratio))

        def company_account(kind: str, i: int, sector: str) -> str:
            address = ctx.address(f"pool|{kind}|{i}")
            co = ctx.company(
                f"pool|{kind}|{i}",
                incorporated=start - timedelta(days=int(rng.integers(400, 9000))),
                sector=sector,
                address=address,
            )
            director = ctx.person(f"pool|{kind}|{i}|director")
            ctx.director(
                f"pool|{kind}|{i}",
                director,
                co,
                start=start - timedelta(days=int(rng.integers(100, 6000))),
            )
            return ctx.account(
                f"pool|{kind}|{i}", co, opened=start - timedelta(days=int(rng.integers(100, 5000)))
            )

        self.suppliers = [company_account("supplier", i, "wholesale") for i in range(size)]
        self.customers = [company_account("customer", i, "services") for i in range(size)]
        self.landlords = [
            company_account("landlord", i, "real estate") for i in range(max(3, size // 4))
        ]
        self.merchants = [
            company_account("merchant", i, "retail") for i in range(max(3, size // 3))
        ]
        opened = start - timedelta(days=6000)
        self.acquirer = ctx.account(
            "pool|acquirer",
            ctx.organization("pool|acquirer", "Synthetic Card Acquiring Ltd"),
            opened=opened,
        )
        self.lender = ctx.account(
            "pool|lender",
            ctx.organization("pool|lender", "Synthetic Business Lending plc"),
            opened=opened,
        )
        self.tax = ctx.account(
            "pool|tax", ctx.organization("pool|tax", "Synthetic Revenue Office"), opened=opened
        )

    @staticmethod
    def pick(rng: np.random.Generator, items: list[str], k: int) -> list[str]:
        """`k` distinct items; earlier items are more popular (heavy-tailed, S15 S20)."""
        k = min(k, len(items))
        weights = 1.0 / np.arange(1, len(items) + 1) ** 0.8
        idx = rng.choice(len(items), size=k, replace=False, p=weights / weights.sum())
        return [items[int(i)] for i in sorted(idx)]


def _employees(rng: np.random.Generator, cfg: BackgroundConfig) -> int:
    r = rng.random()
    if r < cfg.no_employee_share:
        return 0
    if r < cfg.no_employee_share + cfg.small_employer_share:
        return int(rng.integers(1, 10))
    return int(rng.integers(10, 31))


@dataclass(slots=True)
class _Planned:
    src: str
    dst: str
    amount: float
    day: date
    first_hour: int
    last_hour: int
    kind: str  # in | fixed | supplier
    channel: str = "wire"
    purpose: str = ""


def selected(seed: int, org_id: str, share: float) -> bool:
    """Whether an organisation is in the active share: a uniform number from SHA-256 of the seed
    and the id, below `share`."""
    digest = hashlib.sha256(f"{seed}|{org_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64 < share


def generate(ctx: Ctx, orgs: list[BaseOrg], cfg: BackgroundConfig) -> dict[str, int]:
    """Accounts and activity for `orgs`, which are already the eligible ones, in id order.

    Each business keeps a working balance: its outflows over the period come to `spend_share` of
    its inflows (drawn per business), so the money it pays out is not, first in first out, the
    money it has just received. Supplier payments take up what fixed costs leave; when fixed costs
    alone would exceed that share, the business's receipts are scaled up instead."""
    if cfg.share < 1.0:
        orgs = [o for o in orgs if selected(ctx.seed, o.id, cfg.share)]
    if not ctx.branches:
        setup_banks(ctx, cfg)
    pools = Pools(ctx, len(orgs), cfg)
    months = ctx.period.months()
    start, end = ctx.period.start.date(), ctx.period.end.date()
    days_all = working_days(start, end)
    counts = {"organisations": 0, "employees": 0}
    for org in orgs:
        counts["organisations"] += 1
        counts["employees"] += _organisation(ctx, org, pools, cfg, months, days_all)
    return counts


def _organisation(
    ctx: Ctx,
    org: BaseOrg,
    pools: Pools,
    cfg: BackgroundConfig,
    months: list[date],
    days_all: list[date],
) -> int:
    """One base organisation's account and activity; returns its number of employees."""
    start, end = ctx.period.start.date(), ctx.period.end.date()
    rng = ctx.rng("background", org.id)
    opened = _opened(rng, start, org.incorporated)
    acct = ctx.account(f"base|{org.id}", org.id, opened=opened)
    if org.accounts_category.upper() == "DORMANT":
        return 0  # a company that files dormant accounts has no activity
    first_day = max(start, opened + timedelta(days=1))
    closed = (10, 11, 12, 1, 2, 3) if org.sector in SEASONAL_SECTORS else ()

    def open_on(day: date) -> bool:
        return day >= first_day and day.month not in closed

    plan: list[_Planned] = []

    def add(
        src: str,
        dst: str,
        amount: float,
        day: date,
        kind: str,
        first_hour: int = 8,
        last_hour: int = 18,
        channel: str = "wire",
        purpose: str = "",
    ) -> None:
        if start <= day < end and amount > 0:
            plan.append(
                _Planned(src, dst, amount, day, first_hour, last_hour, kind, channel, purpose)
            )

    employees = []
    for e in range(int(_employees(rng, cfg) * cfg.scale + 0.5)):
        person = ctx.person(f"emp|{org.id}|{e}", born=(1955, 2006))
        emp_acct = ctx.account(
            f"emp|{org.id}|{e}",
            person,
            opened=start - timedelta(days=int(rng.integers(60, 9000))),
        )
        employees.append((emp_acct, _amount(rng, cfg.salary_median, cfg.salary_sigma)))
    suppliers = Pools.pick(
        rng, pools.suppliers, int(rng.integers(cfg.suppliers[0], cfg.suppliers[1] + 1))
    )
    customers = Pools.pick(
        rng, pools.customers, int(rng.integers(cfg.customers[0], cfg.customers[1] + 1))
    )
    landlord = pools.landlords[int(rng.integers(len(pools.landlords)))]
    rent = _amount(rng, cfg.rent_median, 0.6)
    spend_share = float(rng.uniform(*cfg.spend_share))
    # receipts
    for customer in customers:
        every = int(rng.choice([10, 20, 30]))
        median = _amount(rng, cfg.customer_median, 0.8)
        for day in days_all[int(rng.integers(0, every)) :: every]:
            if open_on(day):
                amount = _amount(rng, median, 0.3)
                add(customer, acct, amount, day, "in", purpose="Invoice")
                if rng.random() < cfg.refund_share:
                    add(
                        acct,
                        customer,
                        _amount(rng, amount * 0.2, 0.5),
                        day + timedelta(days=int(rng.integers(3, 20))),
                        "fixed",
                        purpose="Credit note",
                    )
    if org.sector in CARD_SECTORS:
        median = _amount(rng, cfg.card_settlement_median, 0.6)
        for day in days_all:
            if open_on(day):
                add(
                    pools.acquirer,
                    acct,
                    _amount(rng, median, 0.4),
                    day,
                    "in",
                    5,
                    7,
                    purpose="Card settlement",
                )
    if org.sector in CASH_SECTORS:
        per_week = int(rng.integers(cfg.cash_banking_days[0], cfg.cash_banking_days[1] + 1))
        median = _amount(rng, cfg.cash_deposit_median * 5 / per_week, 0.4)
        d = start
        while d < end:
            if open_on(d) and d.weekday() < 6 and rng.random() < per_week / 6 * cfg.scale:
                branch = ctx.branches[int(rng.integers(len(ctx.branches)))]
                add(
                    branch,
                    acct,
                    _amount(rng, median, 0.45),
                    d,
                    "in",
                    9,
                    17,
                    channel="cash_deposit",
                    purpose="Takings",
                )
            d += timedelta(days=1)
    # fixed costs
    for month in months:
        payday = last_working_day(month)
        if open_on(payday):
            for emp_acct, salary in employees:
                add(
                    acct,
                    emp_acct,
                    round(salary * float(rng.uniform(0.97, 1.03)), 2),
                    payday,
                    "fixed",
                    6,
                    8,
                    purpose="Salary",
                )
            if employees:
                due = previous_working_day(
                    date(month.year + month.month // 12, month.month % 12 + 1, 22)
                )
                add(
                    acct,
                    pools.tax,
                    round(sum(s for _, s in employees) * 0.32, 2),
                    due,
                    "fixed",
                    purpose="PAYE",
                )
        rent_day = next((d for d in days_all if d >= month), None)
        if rent_day and open_on(rent_day):
            add(acct, landlord, rent, rent_day, "fixed", purpose="Rent")
    if rng.random() < cfg.loan_share and len(days_all) > 60:
        principal = _amount(rng, 25000, 0.7)
        draw = days_all[int(rng.integers(0, len(days_all) // 2))]
        if open_on(draw):
            add(pools.lender, acct, principal, draw, "loan", purpose="Loan drawdown")
            for k in range(1, 13):
                add(
                    acct,
                    pools.lender,
                    round(principal / 12 * 1.06, 2),
                    previous_working_day(draw + timedelta(days=30 * k)),
                    "loan",
                    purpose="Loan repayment",
                )
    # supplier runs, scaled to what the business can spend
    raw: list[_Planned] = []
    for supplier in suppliers:
        every = int(rng.choice([5, 10, 20]))  # working days between payment runs
        median = _amount(rng, cfg.supplier_median, 0.8)
        for day in days_all[int(rng.integers(0, every)) :: every]:
            if open_on(day):
                raw.append(
                    _Planned(
                        acct,
                        supplier,
                        _amount(rng, median, 0.3),
                        day,
                        8,
                        18,
                        "supplier",
                        purpose="Invoice",
                    )
                )
    receipts = sum(x.amount for x in plan if x.kind == "in")
    fixed = sum(x.amount for x in plan if x.kind == "fixed") + 0.09 * receipts  # VAT, below
    if receipts > 0 and fixed > spend_share * receipts * 0.9:
        boost = fixed / (spend_share * receipts * 0.6)
        for x in plan:
            if x.kind == "in":
                x.amount = round(x.amount * boost, 2)
        receipts *= boost
        fixed = sum(x.amount for x in plan if x.kind == "fixed") + 0.09 * receipts
    budget = max(0.0, spend_share * receipts - fixed)
    total_raw = sum(x.amount for x in raw)
    for x in raw:
        x.amount = round(x.amount * budget / total_raw, 2) if total_raw else 0.0
    plan.extend(x for x in raw if x.amount >= 1.0)
    receipts_by_quarter: dict[tuple[int, int], float] = {}
    for x in plan:
        if x.kind == "in":
            q = (x.day.year, (x.day.month - 1) // 3)
            receipts_by_quarter[q] = receipts_by_quarter.get(q, 0.0) + x.amount
    for (year, quarter), received in sorted(receipts_by_quarter.items()):
        due_month = quarter * 3 + 5
        due = date(year + (due_month - 1) // 12, (due_month - 1) % 12 + 1, 7)
        add(
            acct,
            pools.tax,
            round(received * float(rng.uniform(0.07, 0.11)), 2),
            previous_working_day(due),
            "fixed",
            purpose="VAT",
        )
    for n, x in enumerate(plan, 1):
        ctx.pay(
            f"bg|{org.id}|{n}",
            x.src,
            x.dst,
            x.amount,
            at(rng, x.day, x.first_hour, x.last_hour),
            channel=x.channel,
            purpose=x.purpose,
        )
    n = len(plan)
    if cfg.personal:
        for e, (emp_acct, _salary) in enumerate(employees):
            prng = ctx.rng("personal", org.id, str(e))
            rents = prng.random() < cfg.person_rent_share
            person_rent = _amount(prng, cfg.person_rent_median, 0.4)
            for month in months:
                if rents:
                    n += 1
                    ctx.pay(
                        f"bg|{org.id}|{n}",
                        emp_acct,
                        pools.landlords[e % len(pools.landlords)],
                        person_rent,
                        at(prng, month, 7, 9),
                        purpose="Rent",
                    )
                for _ in range(int(prng.integers(cfg.person_cards[0], cfg.person_cards[1] + 1))):
                    day = month + timedelta(days=int(prng.integers(0, 28)))
                    if day < end:
                        merchant = pools.merchants[int(prng.integers(len(pools.merchants)))]
                        n += 1
                        ctx.pay(
                            f"bg|{org.id}|{n}",
                            emp_acct,
                            merchant,
                            _amount(prng, cfg.card_median, cfg.card_sigma),
                            at(prng, day, 7, 22),
                            channel="card",
                            purpose="Purchase",
                        )
                day = month + timedelta(days=int(prng.integers(0, 28)))
                if day < end and prng.random() < 0.6:
                    n += 1
                    ctx.pay(
                        f"bg|{org.id}|{n}",
                        emp_acct,
                        ctx.branches[int(prng.integers(len(ctx.branches)))],
                        _amount(prng, cfg.cash_withdrawal_median, 0.5),
                        at(prng, day, 8, 21),
                        channel="cash_withdrawal",
                    )
    return len(employees)
