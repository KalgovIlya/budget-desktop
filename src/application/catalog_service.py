from __future__ import annotations

from src.application.dto import Category, Merchant, Person
from src.domain.clock import Clock
from src.domain.errors import AlreadyExists, ArchivedEntity, InUse, NotFound, ValidationError
from src.domain.merchant import canonical_key
from src.i18n import t
from src.infrastructure.sqlite_repos import SqliteCatalogs


class CatalogService:
    def __init__(self, catalogs: SqliteCatalogs, clock: Clock) -> None:
        self._c = catalogs
        self._clock = clock

    def clear_all_business_data(self) -> None:
        self._c.clear_all_business_data()

    # people
    def list_people(self, include_archived: bool = False) -> list[Person]:
        return self._c.list_people(include_archived)

    def create_person(self, name: str) -> Person:
        cleaned = name.strip()
        if not cleaned:
            raise ValidationError(t("catalog.err.person_name_empty"))
        if self._c.find_person_by_name_folded(cleaned.casefold()):
            raise AlreadyExists(t("catalog.err.person_exists"))
        return self._c.create_person(cleaned, self._clock.now_iso())

    def ensure_person(self, name: str) -> Person:
        cleaned = name.strip()
        if not cleaned:
            raise ValidationError(t("catalog.err.person_name_empty"))
        existing = self._c.find_person_by_name_folded(cleaned.casefold())
        if existing is None:
            return self._c.create_person(cleaned, self._clock.now_iso())
        if existing.is_archived:
            raise ArchivedEntity(t("catalog.err.person_archived_use"))
        return existing

    def rename_person(self, person_id: int, name: str) -> Person:
        person = self._require_person(person_id)
        cleaned = name.strip()
        if not cleaned:
            raise ValidationError(t("catalog.err.person_name_empty"))
        other = self._c.find_person_by_name_folded(cleaned.casefold())
        if other and other.id != person.id:
            raise AlreadyExists(t("catalog.err.person_exists"))
        return self._c.rename_person(person_id, cleaned)

    def archive_person(self, person_id: int) -> Person:
        self._require_person(person_id)
        return self._c.set_person_archived(person_id, True)

    def unarchive_person(self, person_id: int) -> Person:
        self._require_person(person_id)
        return self._c.set_person_archived(person_id, False)

    def delete_person(self, person_id: int) -> None:
        self._require_person(person_id)
        if self._c.person_expense_count(person_id) > 0:
            raise InUse(t("catalog.err.delete_in_use_expenses"))
        self._c.delete_person(person_id)

    # categories
    def list_categories(self, include_archived: bool = False) -> list[Category]:
        return self._c.list_categories(include_archived)

    def create_category(self, name: str) -> Category:
        cleaned = name.strip()
        if not cleaned:
            raise ValidationError(t("catalog.err.category_name_empty"))
        if self._c.find_category_by_name_folded(cleaned.casefold()):
            raise AlreadyExists(t("catalog.err.category_exists"))
        return self._c.create_category(cleaned, self._clock.now_iso())

    def ensure_category(self, name: str) -> Category:
        cleaned = name.strip()
        if not cleaned:
            raise ValidationError(t("catalog.err.category_name_empty"))
        existing = self._c.find_category_by_name_folded(cleaned.casefold())
        if existing is None:
            return self._c.create_category(cleaned, self._clock.now_iso())
        if existing.is_archived:
            raise ArchivedEntity(t("catalog.err.category_archived_use"))
        return existing

    def rename_category(self, category_id: int, name: str) -> Category:
        cat = self._require_category(category_id)
        cleaned = name.strip()
        if not cleaned:
            raise ValidationError(t("catalog.err.category_name_empty"))
        other = self._c.find_category_by_name_folded(cleaned.casefold())
        if other and other.id != cat.id:
            raise AlreadyExists(t("catalog.err.category_exists"))
        return self._c.rename_category(category_id, cleaned)

    def archive_category(self, category_id: int) -> Category:
        self._require_category(category_id)
        return self._c.set_category_archived(category_id, True)

    def unarchive_category(self, category_id: int) -> Category:
        self._require_category(category_id)
        return self._c.set_category_archived(category_id, False)

    def delete_category(self, category_id: int) -> None:
        self._require_category(category_id)
        if self._c.category_expense_count(category_id) > 0:
            raise InUse(t("catalog.err.delete_in_use_expenses"))
        if self._c.category_merchant_count(category_id) > 0:
            raise InUse(t("catalog.err.delete_category_has_merchants"))
        self._c.delete_category(category_id)

    # merchants
    def list_merchants(
        self, include_archived: bool = False, category_id: int | None = None
    ) -> list[Merchant]:
        return self._c.list_merchants(include_archived, category_id)

    def create_merchant(self, display_name: str, category_id: int) -> Merchant:
        cleaned = display_name.strip()
        if not cleaned:
            raise ValidationError(t("catalog.err.merchant_name_empty"))
        self._require_category(category_id)
        key = canonical_key(cleaned)
        existing = self._c.get_merchant_by_canonical(key)
        if existing:
            raise AlreadyExists(t("catalog.err.merchant_exists"))
        return self._c.create_merchant(key, cleaned, category_id, self._clock.now_iso())

    def rename_merchant_display(self, merchant_id: int, display_name: str) -> Merchant:
        self._require_merchant(merchant_id)
        cleaned = display_name.strip()
        if not cleaned:
            raise ValidationError(t("catalog.err.merchant_name_empty"))
        return self._c.rename_merchant_display(merchant_id, cleaned)

    def archive_merchant(self, merchant_id: int) -> Merchant:
        self._require_merchant(merchant_id)
        return self._c.set_merchant_archived(merchant_id, True)

    def unarchive_merchant(self, merchant_id: int) -> Merchant:
        self._require_merchant(merchant_id)
        return self._c.set_merchant_archived(merchant_id, False)

    def delete_merchant(self, merchant_id: int) -> None:
        self._require_merchant(merchant_id)
        if self._c.merchant_expense_count(merchant_id) > 0:
            raise InUse(t("catalog.err.delete_in_use_expenses"))
        self._c.delete_merchant(merchant_id)

    def merge_merchants(
        self,
        *,
        survivor_id: int,
        source_ids: list[int],
        display_name: str | None = None,
    ) -> Merchant:
        survivor = self._require_merchant(survivor_id)
        sources = [sid for sid in dict.fromkeys(source_ids) if sid != survivor_id]
        if not sources:
            raise ValidationError(t("catalog.err.merge_need_sources"))
        for sid in sources:
            other = self._c.get_merchant(sid)
            if other is None:
                raise NotFound(t("err.merchant_not_found"))
            if other.category_id != survivor.category_id:
                raise ValidationError(t("catalog.err.merge_same_category"))
        for sid in sources:
            self._c.reassign_expenses_merchant(sid, survivor_id)
            self._c.delete_merchant(sid)
        if display_name is not None:
            cleaned = display_name.strip()
            if cleaned and cleaned != survivor.display_name:
                survivor = self._c.rename_merchant_display(survivor_id, cleaned)
        return self._require_merchant(survivor_id)

    def resolve_merchant_for_expense(self, display_name: str, category_id: int) -> Merchant:
        cleaned = display_name.strip()
        if not cleaned:
            raise ValidationError(t("catalog.err.merchant_required"))
        self._require_category(category_id)
        key = canonical_key(cleaned)
        existing = self._c.get_merchant_by_canonical(key)
        if existing is None:
            return self._c.create_merchant(key, cleaned, category_id, self._clock.now_iso())
        if existing.is_archived:
            raise ArchivedEntity(t("catalog.err.merchant_archived_use"))
        if existing.category_id != category_id:
            raise ValidationError(
                t(
                    "catalog.err.merchant_wrong_category",
                    display_name=existing.display_name,
                    category_name=existing.category_name,
                )
            )
        return existing

    def suggest_merchants(self, text: str, category_id: int | None = None) -> list[Merchant]:
        from src.domain.merchant import suggest_keys

        cleaned = text.strip()
        active = self._c.list_merchants(False, category_id)
        if not cleaned:
            return active[:20]
        try:
            key = canonical_key(cleaned)
        except ValidationError:
            key = cleaned.casefold()
        pairs = [(m.canonical_key, m.display_name) for m in active]
        matched = suggest_keys(key, pairs)
        by_key = {m.canonical_key: m for m in active}
        return [by_key[k] for k, _ in matched if k in by_key]

    def _require_person(self, person_id: int) -> Person:
        person = self._c.get_person(person_id)
        if not person:
            raise NotFound(t("err.person_not_found"))
        return person

    def _require_category(self, category_id: int) -> Category:
        cat = self._c.get_category(category_id)
        if not cat:
            raise NotFound(t("err.category_not_found"))
        return cat

    def _require_merchant(self, merchant_id: int) -> Merchant:
        m = self._c.get_merchant(merchant_id)
        if not m:
            raise NotFound(t("err.merchant_not_found"))
        return m
