from __future__ import annotations

import csv
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

from src.application.catalog_service import CatalogService
from src.application.dto import CsvImportResult, ExpenseFilter
from src.application.expense_service import ExpenseService
from src.domain.errors import DomainError, ValidationError
from src.domain.money import Money
from src.i18n import t

_CSV_HEADER = ("spent_on", "amount_rub", "person", "category", "merchant", "note")


class ExportService:
    def __init__(
        self,
        expense_service: ExpenseService,
        catalog_service: CatalogService,
        db_path: Path,
        backups_dir: Path,
    ) -> None:
        self._expenses = expense_service
        self._catalogs = catalog_service
        self._db_path = db_path
        self._backups_dir = backups_dir

    def export_csv(self, filt: ExpenseFilter, target: Path) -> Path:
        items = self._expenses.list_expenses(filt)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.writer(fh, delimiter=";")
            writer.writerow(list(_CSV_HEADER))
            for item in items:
                writer.writerow(
                    [
                        item.spent_on.isoformat(),
                        Money.from_cents(item.amount_cents).format_rub(),
                        item.person_name,
                        item.category_name,
                        item.merchant_name,
                        item.note,
                    ]
                )
        return target

    def import_csv(self, source: Path) -> CsvImportResult:
        if not source.exists():
            raise ValidationError(t("export.err.file_not_found"))
        with source.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.reader(fh, delimiter=";")
            try:
                header = next(reader)
            except StopIteration as exc:
                raise ValidationError(t("export.err.csv_empty")) from exc
            normalized = tuple(cell.strip().casefold() for cell in header)
            if normalized != _CSV_HEADER:
                raise ValidationError(
                    t("export.err.csv_header", header=";".join(_CSV_HEADER))
                )
            rows = list(reader)

        # Header OK → replace current DB contents, then load CSV.
        self._catalogs.clear_all_business_data()

        imported = 0
        errors: list[tuple[int, str]] = []
        for row_number, row in enumerate(rows, start=2):
            if not row or all(not str(cell).strip() for cell in row):
                continue
            while len(row) < 6:
                row.append("")
            try:
                self._import_row(row)
                imported += 1
            except DomainError as exc:
                errors.append((row_number, str(exc)))
            except ValueError as exc:
                errors.append((row_number, str(exc)))
        return CsvImportResult(imported=imported, errors=tuple(errors))

    def _import_row(self, row: list[str]) -> None:
        spent_raw, amount_raw, person_raw, category_raw, merchant_raw, note_raw = (
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
        )
        try:
            spent_on = date.fromisoformat(spent_raw.strip())
        except ValueError as exc:
            raise ValidationError(t("export.err.bad_date")) from exc
        amount = Money.from_rubles_str(amount_raw)
        person = self._catalogs.ensure_person(person_raw)
        category = self._catalogs.ensure_category(category_raw)
        self._expenses.add_expense(
            amount=amount,
            spent_on=spent_on,
            person_id=person.id,
            category_id=category.id,
            merchant_input=merchant_raw,
            note=note_raw,
        )

    def backup_database(self) -> Path:
        self._backups_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        target = self._backups_dir / f"budget-{stamp}.db"
        shutil.copy2(self._db_path, target)
        return target
