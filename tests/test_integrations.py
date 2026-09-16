from datetime import date
from decimal import Decimal

from finance_app.integrations.backup import EncryptedBackupService
from finance_app.integrations.banking import ImportedTransaction, ManualImportConnector
from finance_app.integrations.market_data import ManualMarketDataProvider, MarketQuote
from cryptography.fernet import Fernet


def test_encrypted_backup_round_trip() -> None:
    service = EncryptedBackupService(Fernet.generate_key())
    payload = b"local-finance-database"
    encrypted = service.export_bytes(payload)
    assert encrypted != payload
    assert service.import_bytes(encrypted) == payload


def test_manual_bank_connector_is_offline() -> None:
    tx = ImportedTransaction(date(2026, 1, 2), "Courses", Decimal("-42.50"))
    connector = ManualImportConnector([tx])
    assert connector.import_transactions("account-1") == [tx]


def test_manual_market_provider_filters_date_range() -> None:
    quote = MarketQuote("TEST", date(2026, 1, 10), Decimal("100"), "EUR", "manual")
    provider = ManualMarketDataProvider([quote])
    assert provider.get_history("TEST", date(2026, 1, 1), date(2026, 1, 31)) == [quote]
    assert provider.get_history("TEST", date(2026, 2, 1), date(2026, 2, 28)) == []
