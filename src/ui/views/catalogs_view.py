from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.application.catalog_service import CatalogService
from src.domain.errors import DomainError
from src.i18n import t


class CatalogsView(QWidget):
    def __init__(self, catalogs: CatalogService, parent=None) -> None:
        super().__init__(parent)
        self._catalogs = catalogs
        self._button_refs: list[tuple[QPushButton, str]] = []
        self._section_labels: list[tuple[QLabel, str]] = []

        self._show_archived = QCheckBox()
        self._show_archived.stateChanged.connect(self.refresh)

        self._people = QListWidget()
        self._categories = QListWidget()
        self._merchants = QListWidget()
        self._merchants.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)

        header = QHBoxLayout()
        header.setSpacing(10)
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 0, 0, 0)
        self._title = QLabel()
        self._title.setObjectName("emptyTitle")
        self._subtitle = QLabel()
        self._subtitle.setObjectName("subtitle")
        title_box.addWidget(self._title)
        title_box.addWidget(self._subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        header.addWidget(self._show_archived)

        cols = QHBoxLayout()
        cols.setSpacing(16)
        cols.addLayout(
            self._column(
                "catalogs.section.people",
                self._people,
                primary=[("catalogs.btn.add", self._add_person, False)],
                footer=[
                    ("catalogs.btn.rename", self._rename_person, True),
                    ("catalogs.btn.archive", self._archive_person, True),
                    ("catalogs.btn.unarchive", self._unarchive_person, True),
                    ("catalogs.btn.delete", self._delete_person, True),
                ],
            ),
            stretch=1,
        )
        cols.addLayout(
            self._column(
                "catalogs.section.categories",
                self._categories,
                primary=[("catalogs.btn.add", self._add_category, False)],
                footer=[
                    ("catalogs.btn.rename", self._rename_category, True),
                    ("catalogs.btn.archive", self._archive_category, True),
                    ("catalogs.btn.unarchive", self._unarchive_category, True),
                    ("catalogs.btn.delete", self._delete_category, True),
                ],
            ),
            stretch=1,
        )
        cols.addLayout(
            self._column(
                "catalogs.section.merchants",
                self._merchants,
                primary=[
                    ("catalogs.btn.add", self._add_merchant, False),
                    ("catalogs.btn.merge", self._merge_merchants, True),
                ],
                footer=[
                    ("catalogs.btn.rename", self._rename_merchant, True),
                    ("catalogs.btn.archive", self._archive_merchant, True),
                    ("catalogs.btn.unarchive", self._unarchive_merchant, True),
                    ("catalogs.btn.delete", self._delete_merchant, True),
                ],
            ),
            stretch=1,
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)
        root.addLayout(header)
        root.addLayout(cols, stretch=1)
        self.retranslate()
        self.refresh()

    def retranslate(self) -> None:
        self._title.setText(t("catalogs.title"))
        self._subtitle.setText(t("catalogs.subtitle"))
        self._show_archived.setText(t("catalogs.show_archived"))
        for label, key in self._section_labels:
            label.setText(t(key))
        for btn, key in self._button_refs:
            btn.setText(t(key))

    def _column(
        self,
        title_key: str,
        list_widget: QListWidget,
        *,
        primary: list,
        footer: list,
    ) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(8)
        label = QLabel()
        label.setObjectName("sectionTitle")
        self._section_labels.append((label, title_key))
        box.addWidget(label)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        for key, slot, secondary in primary:
            btn = QPushButton()
            if secondary:
                btn.setObjectName("secondary")
            btn.clicked.connect(slot)
            self._button_refs.append((btn, key))
            toolbar.addWidget(btn)
        toolbar.addStretch(1)
        box.addLayout(toolbar)
        box.addWidget(list_widget, stretch=1)

        more = QHBoxLayout()
        more.setSpacing(6)
        for key, slot, secondary in footer:
            btn = QPushButton()
            btn.setObjectName(
                "danger" if key == "catalogs.btn.delete" else "secondary"
            )
            btn.clicked.connect(slot)
            self._button_refs.append((btn, key))
            more.addWidget(btn)
        more.addStretch(1)
        box.addLayout(more)
        return box

    def refresh(self) -> None:
        include = self._show_archived.isChecked()
        archived = t("catalogs.suffix.archived")
        self._fill(
            self._people,
            self._catalogs.list_people(include),
            lambda p: f"{p.name}{archived}" if p.is_archived else p.name,
            lambda p: p.id,
        )
        self._fill(
            self._categories,
            self._catalogs.list_categories(include),
            lambda c: f"{c.name}{archived}" if c.is_archived else c.name,
            lambda c: c.id,
        )
        self._fill(
            self._merchants,
            self._catalogs.list_merchants(include),
            lambda m: (
                f"{m.display_name} · {m.category_name}"
                + (archived if m.is_archived else "")
            ),
            lambda m: m.id,
        )

    def _fill(self, widget: QListWidget, items, label_fn, id_fn) -> None:
        widget.clear()
        for item in items:
            row = QListWidgetItem(label_fn(item))
            row.setData(Qt.ItemDataRole.UserRole, id_fn(item))
            widget.addItem(row)

    def _selected_id(self, widget: QListWidget) -> int | None:
        item = widget.currentItem()
        return None if item is None else int(item.data(Qt.ItemDataRole.UserRole))

    def _run(self, fn) -> None:
        try:
            fn()
            self.refresh()
        except DomainError as exc:
            QMessageBox.warning(self, t("common.app_name"), str(exc))

    def _add_person(self) -> None:
        text, ok = QInputDialog.getText(
            self,
            t("catalogs.dialog.person_title"),
            t("catalogs.dialog.person_name"),
        )
        if ok:
            self._run(lambda: self._catalogs.create_person(text))

    def _rename_person(self) -> None:
        pid = self._selected_id(self._people)
        if pid is None:
            return
        text, ok = QInputDialog.getText(
            self,
            t("catalogs.dialog.person_title"),
            t("catalogs.dialog.person_rename"),
        )
        if ok:
            self._run(lambda: self._catalogs.rename_person(pid, text))

    def _archive_person(self) -> None:
        pid = self._selected_id(self._people)
        if pid is not None:
            self._run(lambda: self._catalogs.archive_person(pid))

    def _unarchive_person(self) -> None:
        pid = self._selected_id(self._people)
        if pid is not None:
            self._run(lambda: self._catalogs.unarchive_person(pid))

    def _delete_person(self) -> None:
        pid = self._selected_id(self._people)
        if pid is not None:
            self._run(lambda: self._catalogs.delete_person(pid))

    def _add_category(self) -> None:
        text, ok = QInputDialog.getText(
            self,
            t("catalogs.dialog.category_title"),
            t("catalogs.dialog.category_name"),
        )
        if ok:
            self._run(lambda: self._catalogs.create_category(text))

    def _rename_category(self) -> None:
        cid = self._selected_id(self._categories)
        if cid is None:
            return
        text, ok = QInputDialog.getText(
            self,
            t("catalogs.dialog.category_title"),
            t("catalogs.dialog.category_rename"),
        )
        if ok:
            self._run(lambda: self._catalogs.rename_category(cid, text))

    def _archive_category(self) -> None:
        cid = self._selected_id(self._categories)
        if cid is not None:
            self._run(lambda: self._catalogs.archive_category(cid))

    def _unarchive_category(self) -> None:
        cid = self._selected_id(self._categories)
        if cid is not None:
            self._run(lambda: self._catalogs.unarchive_category(cid))

    def _delete_category(self) -> None:
        cid = self._selected_id(self._categories)
        if cid is not None:
            self._run(lambda: self._catalogs.delete_category(cid))

    def _add_merchant(self) -> None:
        categories = self._catalogs.list_categories(False)
        if not categories:
            QMessageBox.information(
                self, t("common.app_name"), t("catalogs.msg.need_category")
            )
            return
        from src.ui.views.merchant_dialog import MerchantDialog

        dialog = MerchantDialog(categories, self)
        if dialog.exec():
            name, category_id = dialog.payload()
            self._run(lambda: self._catalogs.create_merchant(name, category_id))

    def _merge_merchants(self) -> None:
        selected = self._merchants.selectedItems()
        if len(selected) < 2:
            QMessageBox.information(
                self,
                t("common.app_name"),
                t("catalogs.msg.select_two_merchants"),
            )
            return
        ids = {int(item.data(Qt.ItemDataRole.UserRole)) for item in selected}
        include = self._show_archived.isChecked()
        merchants = [m for m in self._catalogs.list_merchants(include) if m.id in ids]
        if len(merchants) < 2:
            return
        from src.ui.views.merchant_merge_dialog import MerchantMergeDialog

        dialog = MerchantMergeDialog(merchants, self)
        if dialog.exec():
            survivor_id, source_ids, display_name = dialog.payload()
            self._run(
                lambda: self._catalogs.merge_merchants(
                    survivor_id=survivor_id,
                    source_ids=source_ids,
                    display_name=display_name,
                )
            )

    def _rename_merchant(self) -> None:
        mid = self._selected_id(self._merchants)
        if mid is None:
            return
        text, ok = QInputDialog.getText(
            self,
            t("catalogs.dialog.merchant_title"),
            t("catalogs.dialog.merchant_display_name"),
        )
        if ok:
            self._run(lambda: self._catalogs.rename_merchant_display(mid, text))

    def _archive_merchant(self) -> None:
        mid = self._selected_id(self._merchants)
        if mid is not None:
            self._run(lambda: self._catalogs.archive_merchant(mid))

    def _unarchive_merchant(self) -> None:
        mid = self._selected_id(self._merchants)
        if mid is not None:
            self._run(lambda: self._catalogs.unarchive_merchant(mid))

    def _delete_merchant(self) -> None:
        mid = self._selected_id(self._merchants)
        if mid is not None:
            self._run(lambda: self._catalogs.delete_merchant(mid))
