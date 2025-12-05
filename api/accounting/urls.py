from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    FiscalYearViewSet, AccountingPeriodViewSet, CurrencyViewSet, TaxRateViewSet,
    AccountViewSet, JournalEntryViewSet, ContactViewSet, InvoiceViewSet,
    PaymentViewSet, ExpenseViewSet, ReportViewSet
)

router = DefaultRouter()
router.register(r'accounting/fiscal-years', FiscalYearViewSet, basename='fiscal-year')
router.register(r'accounting/periods', AccountingPeriodViewSet, basename='accounting-period')
router.register(r'accounting/currencies', CurrencyViewSet, basename='currency')
router.register(r'accounting/tax-rates', TaxRateViewSet, basename='tax-rate')
router.register(r'accounting/accounts', AccountViewSet, basename='account')
router.register(r'accounting/journal-entries', JournalEntryViewSet, basename='journal-entry')
router.register(r'accounting/contacts', ContactViewSet, basename='contact')
router.register(r'accounting/invoices', InvoiceViewSet, basename='invoice')
router.register(r'accounting/payments', PaymentViewSet, basename='payment')
router.register(r'accounting/expenses', ExpenseViewSet, basename='expense')
router.register(r'accounting/reports', ReportViewSet, basename='report')

urlpatterns = router.urls
