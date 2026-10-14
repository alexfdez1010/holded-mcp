# API coverage

Official API snapshot: **2026-10-14**.

The bundled catalog exposes **360 operations** from Holded's current public API (`/api/v2/...`). Holded's legacy v1 API is intentionally not supported.

| API | Operations |
| --- | ---: |
| accounting | 32 |
| treasury | 24 |
| sales | 104 |
| inventory | 78 |
| contacts | 20 |
| crm | 17 |
| projects | 17 |
| team | 37 |
| calendar | 12 |
| inbox | 9 |
| developers | 10 |
| **total** | **360** |

## Source

Holded publishes its API as one OpenAPI 3.1 document: [https://api.holded.com/openapi/api2.json](https://api.holded.com/openapi/api2.json). A copy is committed as [`specs/api2.json`](../specs/api2.json) (minified JSON, otherwise unchanged) so the catalog can be rebuilt offline. Paths are `/api/v2/...` and requests authenticate with `Authorization: Bearer <api key>`. Each operation declares the permission scope it needs (for example `sales:invoices.read`); the API key must have that scope. The reference is at [https://www.holded.com/developers/api-reference](https://www.holded.com/developers/api-reference).

Coverage means every HTTP operation in this definition is callable. Holded plan limits, permissions, scopes and account features still apply. Response schemas are not bundled; responses are returned as received. Undocumented endpoints are not claimed as supported.

## Normalizations and limitations

- Operation IDs are the source `operationId` unchanged (for example `list_invoices`).
- `api` is the slug of the operation's `x-tagGroups` group: `accounting`, `treasury`, `sales`, `inventory`, `contacts`, `crm`, `projects`, `team` (Team & HR), `calendar`, `inbox`, `developers`. `tags` keep the single source tag (for example `Invoices`). Paths are full paths (`/api/v2/...`).
- `doc_url` is `https://www.holded.com/developers/api-reference/<tag>/<summary>` (both slugified), the URL pattern of Holded's reference pages.
- Local `$ref`s are expanded (siblings retained). Recursive positions, if any appear in future definitions, are left unconstrained and marked with `x-holded-recursive-reference`.
- A schema declaring `properties` without `type` is normalized to `type: object`.
- OpenAPI 3.1 type arrays (`["string", "null"]`) and `null` enum members are kept; validation uses JSON Schema 2020-12.
- Holded's `x-ai-*` extensions (presentation and assistant hints such as `x-ai-presentation`, `x-ai-hidden`, `x-ai-grounded`, `x-ai-format`) are removed from parameter and body schemas. They are not input constraints.
- Operation-level parameters override path-level parameters with the same name and location. Path parameters are always `required: true`. Parameters without a schema default to `type: string`; parameters without a description get an empty one. A parameter-level `example` moves into its schema.
- The `Authorization` header is excluded: the client adds it to every request. No operation declares any other header, cookie or path-level parameter; the generator fails if one appears, because the transport only sends path and query parameters.
- `body_required` and `required` flags are kept from the source.
- Source descriptions already start with `**Required permission:** <scope>`. Where they omit any scope from the operation's `security` requirement, the full list is appended as `Required permission scopes: ...` (for example, `export_inbox` also needs `accounting:purchases.write`).
- Pagination follows each endpoint's declared parameters; none are added. At snapshot time, paginated list operations take `limit` and an opaque `cursor` returned by the previous response (with `has_more`). The document's general introduction also mentions `page`/`limit`, but no operation declares `page`.
- File uploads use `multipart/form-data` with binary fields as `{"type": "string", "format": "binary"}`; OpenAPI 3.1 `contentMediaType` file fields (none at snapshot time) are normalized to the same form. Multipart uploads (`attach_contact_file`, `attach_credit_note_file`, `attach_estimate_file`, `attach_invoice_file`, `attach_proforma_file`, `attach_purchase_file`, `attach_purchase_order_file`, `attach_receipt_note_file`, `attach_sales_order_file`, `attach_sales_receipt_file`, `attach_waybill_file`, `upload_inbox`, `upload_product_image`) take one binary field (`file`, or `document` for `upload_inbox`).

## Regenerate

Fetch the official definition, refresh `specs/api2.json`, and rebuild:

```sh
uv sync --group dev
uv run python scripts/update_catalog.py --snapshot-date YYYY-MM-DD
```

Rebuild offline from the committed copy:

```sh
uv run python scripts/update_catalog.py --snapshot-date YYYY-MM-DD --from-specs
```

Another local snapshot can be passed with `--spec PATH`; it is copied to `specs/api2.json`. Add `--verify-docs` to fetch every reference page and check that it documents the same method and path. If Holded adds a tag group, add it to `TAG_GROUPS` in `scripts/update_catalog.py`. The generator rejects duplicate operation IDs, duplicate method/path pairs, unresolved references, missing or extra path parameters, unsupported parameter locations, unexpected servers and unsupported body content types before writing anything.

## Operations

| Operation ID | API | Method | Path | API reference |
| --- | --- | --- | --- | --- |
| `accept_estimate` | sales | POST | `/api/v2/estimates/{estimateId}/accept` | [Accept an estimate](https://www.holded.com/developers/api-reference/estimates/accept-an-estimate) |
| `approve_credit_note` | sales | POST | `/api/v2/credit-notes/{creditNoteId}/approve` | [Approve a credit note](https://www.holded.com/developers/api-reference/credit-notes/approve-a-credit-note) |
| `approve_estimate` | sales | POST | `/api/v2/estimates/{estimateId}/approve` | [Approve an estimate](https://www.holded.com/developers/api-reference/estimates/approve-an-estimate) |
| `approve_invoice` | sales | POST | `/api/v2/invoices/{invoiceId}/approve` | [Approve an invoice](https://www.holded.com/developers/api-reference/invoices/approve-an-invoice) |
| `approve_payslip` | team | POST | `/api/v2/payslips/{payslipId}/approve` | [Approve a payslip](https://www.holded.com/developers/api-reference/payslips/approve-a-payslip) |
| `approve_proforma` | sales | POST | `/api/v2/proformas/{proformaId}/approve` | [Approve a proforma](https://www.holded.com/developers/api-reference/proformas/approve-a-proforma) |
| `approve_purchase` | accounting | POST | `/api/v2/purchases/{purchaseId}/approve` | [Approve a purchase](https://www.holded.com/developers/api-reference/purchases/approve-a-purchase) |
| `approve_purchase_order` | inventory | POST | `/api/v2/purchase-orders/{purchaseOrderId}/approve` | [Approve a purchase order](https://www.holded.com/developers/api-reference/purchase-orders/approve-a-purchase-order) |
| `approve_purchase_shipment` | inventory | POST | `/api/v2/purchase-shipments/{purchaseShipmentId}/approve` | [Approve a purchase shipment](https://www.holded.com/developers/api-reference/purchase-shipments/approve-a-purchase-shipment) |
| `approve_receipt_note` | sales | POST | `/api/v2/receipt-notes/{receiptNoteId}/approve` | [Approve a receipt note](https://www.holded.com/developers/api-reference/receipt-notes/approve-a-receipt-note) |
| `approve_sales_order` | inventory | POST | `/api/v2/sales-orders/{salesOrderId}/approve` | [Approve a sales order](https://www.holded.com/developers/api-reference/sales-orders/approve-a-sales-order) |
| `approve_sales_receipt` | sales | POST | `/api/v2/sales-receipts/{salesReceiptId}/approve` | [Approve a sales receipt](https://www.holded.com/developers/api-reference/sales-receipts/approve-a-sales-receipt) |
| `approve_waybill` | inventory | POST | `/api/v2/waybills/{waybillId}/approve` | [Approve a waybill](https://www.holded.com/developers/api-reference/waybills/approve-a-waybill) |
| `archive_banking_account` | treasury | POST | `/api/v2/treasury/accounts/{id}/archive` | [Archive a banking account](https://www.holded.com/developers/api-reference/banking-accounts/archive-a-banking-account) |
| `attach_contact_file` | contacts | POST | `/api/v2/contacts/{contactId}/attachments` | [Attach a file to a contact](https://www.holded.com/developers/api-reference/contact/attach-a-file-to-a-contact) |
| `attach_credit_note_file` | sales | POST | `/api/v2/credit-notes/{creditNoteId}/attachments` | [Attach a file to a credit note](https://www.holded.com/developers/api-reference/credit-notes/attach-a-file-to-a-credit-note) |
| `attach_estimate_file` | sales | POST | `/api/v2/estimates/{estimateId}/attachments` | [Attach a file to an estimate](https://www.holded.com/developers/api-reference/estimates/attach-a-file-to-an-estimate) |
| `attach_inbox` | inbox | POST | `/api/v2/inbox/{incomingDocumentId}/attach` | [Attach incoming document to a document](https://www.holded.com/developers/api-reference/inbox/attach-incoming-document-to-a-document) |
| `attach_invoice_file` | sales | POST | `/api/v2/invoices/{invoiceId}/attachments` | [Attach a file to an invoice](https://www.holded.com/developers/api-reference/invoices/attach-a-file-to-an-invoice) |
| `attach_proforma_file` | sales | POST | `/api/v2/proformas/{proformaId}/attachments` | [Attach a file to a proforma](https://www.holded.com/developers/api-reference/proformas/attach-a-file-to-a-proforma) |
| `attach_purchase_file` | accounting | POST | `/api/v2/purchases/{purchaseId}/attachments` | [Attach a file to a purchase](https://www.holded.com/developers/api-reference/purchases/attach-a-file-to-a-purchase) |
| `attach_purchase_order_file` | inventory | POST | `/api/v2/purchase-orders/{purchaseOrderId}/attachments` | [Attach a file to a purchase order](https://www.holded.com/developers/api-reference/purchase-orders/attach-a-file-to-a-purchase-order) |
| `attach_receipt_note_file` | sales | POST | `/api/v2/receipt-notes/{receiptNoteId}/attachments` | [Attach a file to a receipt note](https://www.holded.com/developers/api-reference/receipt-notes/attach-a-file-to-a-receipt-note) |
| `attach_sales_order_file` | inventory | POST | `/api/v2/sales-orders/{salesOrderId}/attachments` | [Attach a file to a sales order](https://www.holded.com/developers/api-reference/sales-orders/attach-a-file-to-a-sales-order) |
| `attach_sales_receipt_file` | sales | POST | `/api/v2/sales-receipts/{salesReceiptId}/attachments` | [Attach a file to a sales receipt](https://www.holded.com/developers/api-reference/sales-receipts/attach-a-file-to-a-sales-receipt) |
| `attach_waybill_file` | inventory | POST | `/api/v2/waybills/{waybillId}/attachments` | [Attach a file to a waybill](https://www.holded.com/developers/api-reference/waybills/attach-a-file-to-a-waybill) |
| `bulk_approve_invoices` | sales | POST | `/api/v2/invoices/bulk/approve` | [Bulk approve invoices](https://www.holded.com/developers/api-reference/invoices/bulk-approve-invoices) |
| `bulk_archive_contacts` | contacts | POST | `/api/v2/contacts/bulk-archive` | [Bulk archive contacts](https://www.holded.com/developers/api-reference/contact/bulk-archive-contacts) |
| `bulk_cancel_invoices` | sales | POST | `/api/v2/invoices/bulk/cancel` | [Bulk cancel invoices](https://www.holded.com/developers/api-reference/invoices/bulk-cancel-invoices) |
| `bulk_delete_contacts` | contacts | POST | `/api/v2/contacts/bulk-delete` | [Bulk delete contacts](https://www.holded.com/developers/api-reference/contact/bulk-delete-contacts) |
| `bulk_delete_invoices` | sales | DELETE | `/api/v2/invoices` | [Bulk delete invoices](https://www.holded.com/developers/api-reference/invoices/bulk-delete-invoices) |
| `cancel_invoice` | sales | POST | `/api/v2/invoices/{invoiceId}/cancel` | [Cancel an invoice](https://www.holded.com/developers/api-reference/invoices/cancel-an-invoice) |
| `clock_in` | team | POST | `/api/v2/employees/{employeeId}/clock-in` | [Clock in an employee](https://www.holded.com/developers/api-reference/employee-time-tracking/clock-in-an-employee) |
| `clock_out` | team | POST | `/api/v2/employees/{employeeId}/clock-out` | [Clock out an employee](https://www.holded.com/developers/api-reference/employee-time-tracking/clock-out-an-employee) |
| `convert_document` | inventory | POST | `/api/v2/documents/convert` | [Convert a document to another type](https://www.holded.com/developers/api-reference/documents/convert-a-document-to-another-type) |
| `create_accounting_account` | accounting | POST | `/api/v2/accounting-accounts` | [Create an accounting account](https://www.holded.com/developers/api-reference/accounting/create-an-accounting-account) |
| `create_bank_movement` | treasury | POST | `/api/v2/treasury/accounts/{bankingAccountId}/bank-movements` | [Create one or multiple manual bank movements](https://www.holded.com/developers/api-reference/banking-accounts/create-one-or-multiple-manual-bank-movements) |
| `create_banking_account` | treasury | POST | `/api/v2/treasury/accounts` | [Create a banking account](https://www.holded.com/developers/api-reference/banking-accounts/create-a-banking-account) |
| `create_booking` | calendar | POST | `/api/v2/bookings` | [Create a booking](https://www.holded.com/developers/api-reference/bookings/create-a-booking) |
| `create_contact` | contacts | POST | `/api/v2/contacts` | [Create a contact](https://www.holded.com/developers/api-reference/contact/create-a-contact) |
| `create_contact_group` | contacts | POST | `/api/v2/contact-groups` | [Create a contact group](https://www.holded.com/developers/api-reference/contact-group/create-a-contact-group) |
| `create_credit_note` | sales | POST | `/api/v2/credit-notes` | [Create a credit note](https://www.holded.com/developers/api-reference/credit-notes/create-a-credit-note) |
| `create_credit_note_payment` | sales | POST | `/api/v2/credit-notes/{creditNoteId}/payments` | [Create a payment for a credit note](https://www.holded.com/developers/api-reference/credit-notes/create-a-payment-for-a-credit-note) |
| `create_employee` | team | POST | `/api/v2/employees` | [Create an employee](https://www.holded.com/developers/api-reference/employees/create-an-employee) |
| `create_employee_time` | team | POST | `/api/v2/employees/{employeeId}/times` | [Create a time entry for an employee](https://www.holded.com/developers/api-reference/employee-time-tracking/create-a-time-entry-for-an-employee) |
| `create_estimate` | sales | POST | `/api/v2/estimates` | [Create an estimate](https://www.holded.com/developers/api-reference/estimates/create-an-estimate) |
| `create_event` | calendar | POST | `/api/v2/events` | [Create an event](https://www.holded.com/developers/api-reference/events/create-an-event) |
| `create_expenses_account` | accounting | POST | `/api/v2/expenses-accounts` | [Create an expenses account](https://www.holded.com/developers/api-reference/expenses-accounts/create-an-expenses-account) |
| `create_funnel` | crm | POST | `/api/v2/funnels` | [Create a funnel](https://www.holded.com/developers/api-reference/funnels/create-a-funnel) |
| `create_invoice` | sales | POST | `/api/v2/invoices` | [Create an invoice](https://www.holded.com/developers/api-reference/invoices/create-an-invoice) |
| `create_invoice_payment` | sales | POST | `/api/v2/invoices/{invoiceId}/payments` | [Create a payment for an invoice](https://www.holded.com/developers/api-reference/invoices/create-a-payment-for-an-invoice) |
| `create_invoice_recurring` | sales | POST | `/api/v2/recurring-invoices` | [Create a recurring invoice](https://www.holded.com/developers/api-reference/recurring-invoices/create-a-recurring-invoice) |
| `create_invoicing_forecast` | treasury | POST | `/api/v2/treasury/cashflow/invoicing-forecasts` | [Create an invoicing forecast](https://www.holded.com/developers/api-reference/invoicing-forecast/create-an-invoicing-forecast) |
| `create_lead` | crm | POST | `/api/v2/leads` | [Create a lead](https://www.holded.com/developers/api-reference/leads/create-a-lead) |
| `create_lead_note` | crm | POST | `/api/v2/leads/{leadId}/notes` | [Create a lead note](https://www.holded.com/developers/api-reference/leads/create-a-lead-note) |
| `create_lead_task` | crm | POST | `/api/v2/leads/{leadId}/tasks` | [Create a lead task](https://www.holded.com/developers/api-reference/leads/create-a-lead-task) |
| `create_ledger_entry` | accounting | POST | `/api/v2/ledger-entries` | [Create a ledger entry](https://www.holded.com/developers/api-reference/accounting/create-a-ledger-entry) |
| `create_numbering_series` | sales | POST | `/api/v2/numbering-series/{type}` | [Create a numbering series](https://www.holded.com/developers/api-reference/numbering-series/create-a-numbering-series) |
| `create_payment` | accounting | POST | `/api/v2/payments` | [Create a payment](https://www.holded.com/developers/api-reference/payment/create-a-payment) |
| `create_payment_method` | treasury | POST | `/api/v2/payment-methods` | [Create a payment method](https://www.holded.com/developers/api-reference/payment-methods/create-a-payment-method) |
| `create_payslip` | team | POST | `/api/v2/payslips` | [Create payslips in bulk](https://www.holded.com/developers/api-reference/payslips/create-payslips-in-bulk) |
| `create_payslip_payment` | team | POST | `/api/v2/payslips/{payslipId}/payments` | [Create a payment for a payslip](https://www.holded.com/developers/api-reference/payslips/create-a-payment-for-a-payslip) |
| `create_price_list` | inventory | POST | `/api/v2/price-lists` | [Create a price list](https://www.holded.com/developers/api-reference/price-lists/create-a-price-list) |
| `create_product` | inventory | POST | `/api/v2/products` | [Create a product](https://www.holded.com/developers/api-reference/products/create-a-product) |
| `create_production_order` | inventory | POST | `/api/v2/production-orders` | [Create a production order](https://www.holded.com/developers/api-reference/production-orders/create-a-production-order) |
| `create_proforma` | sales | POST | `/api/v2/proformas` | [Create a proforma](https://www.holded.com/developers/api-reference/proformas/create-a-proforma) |
| `create_project` | projects | POST | `/api/v2/projects` | [Create a project](https://www.holded.com/developers/api-reference/projects/create-a-project) |
| `create_project_time` | projects | POST | `/api/v2/projects/{projectId}/times` | [Create a time entry for a project](https://www.holded.com/developers/api-reference/project-time-tracking/create-a-time-entry-for-a-project) |
| `create_purchase` | accounting | POST | `/api/v2/purchases` | [Create a purchase](https://www.holded.com/developers/api-reference/purchases/create-a-purchase) |
| `create_purchase_order` | inventory | POST | `/api/v2/purchase-orders` | [Create a purchase order](https://www.holded.com/developers/api-reference/purchase-orders/create-a-purchase-order) |
| `create_purchase_payment` | accounting | POST | `/api/v2/purchases/{purchaseId}/payments` | [Create a payment for a purchase](https://www.holded.com/developers/api-reference/purchases/create-a-payment-for-a-purchase) |
| `create_purchase_refund` | accounting | POST | `/api/v2/purchases/refund` | [Create a purchase refund](https://www.holded.com/developers/api-reference/purchases/create-a-purchase-refund) |
| `create_purchase_shipment` | inventory | POST | `/api/v2/purchase-shipments` | [Create a purchase shipment](https://www.holded.com/developers/api-reference/purchase-shipments/create-a-purchase-shipment) |
| `create_receipt_note` | sales | POST | `/api/v2/receipt-notes` | [Create a receipt note](https://www.holded.com/developers/api-reference/receipt-notes/create-a-receipt-note) |
| `create_receipt_note_payment` | sales | POST | `/api/v2/receipt-notes/{receiptNoteId}/payments` | [Create a payment for a receipt note](https://www.holded.com/developers/api-reference/receipt-notes/create-a-payment-for-a-receipt-note) |
| `create_salary_record` | team | POST | `/api/v2/salary-records` | [Create a salary record](https://www.holded.com/developers/api-reference/salary-records/create-a-salary-record) |
| `create_sales_channel` | sales | POST | `/api/v2/sales-channels` | [Create a sales channel](https://www.holded.com/developers/api-reference/sales-channels/create-a-sales-channel) |
| `create_sales_order` | inventory | POST | `/api/v2/sales-orders` | [Create a sales order](https://www.holded.com/developers/api-reference/sales-orders/create-a-sales-order) |
| `create_sales_receipt` | sales | POST | `/api/v2/sales-receipts` | [Create a sales receipt](https://www.holded.com/developers/api-reference/sales-receipts/create-a-sales-receipt) |
| `create_sales_receipt_payment` | sales | POST | `/api/v2/sales-receipts/{salesReceiptId}/payments` | [Create a payment for a sales receipt](https://www.holded.com/developers/api-reference/sales-receipts/create-a-payment-for-a-sales-receipt) |
| `create_service` | sales | POST | `/api/v2/services` | [Create a service](https://www.holded.com/developers/api-reference/services/create-a-service) |
| `create_tag` | contacts | POST | `/api/v2/tags` | [Create a tag](https://www.holded.com/developers/api-reference/tags/create-a-tag) |
| `create_task` | projects | POST | `/api/v2/tasks` | [Create a task](https://www.holded.com/developers/api-reference/tasks/create-a-task) |
| `create_time_off` | team | POST | `/api/v2/employees/{employeeId}/time-offs` | [Create a time off request (absence / holiday)](https://www.holded.com/developers/api-reference/time-off/create-a-time-off-request-absence-holiday) |
| `create_warehouse` | inventory | POST | `/api/v2/warehouses` | [Create a warehouse](https://www.holded.com/developers/api-reference/warehouses/create-a-warehouse) |
| `create_waybill` | inventory | POST | `/api/v2/waybills` | [Create a waybill](https://www.holded.com/developers/api-reference/waybills/create-a-waybill) |
| `create_webhook` | developers | POST | `/api/v2/webhooks` | [Create a webhook](https://www.holded.com/developers/api-reference/webhooks/create-a-webhook) |
| `delete_banking_account` | treasury | DELETE | `/api/v2/treasury/accounts/{id}` | [Delete a banking account](https://www.holded.com/developers/api-reference/banking-accounts/delete-a-banking-account) |
| `delete_booking` | calendar | DELETE | `/api/v2/bookings/{bookingId}` | [Cancel a booking](https://www.holded.com/developers/api-reference/bookings/cancel-a-booking) |
| `delete_contact` | contacts | DELETE | `/api/v2/contacts/{contactId}` | [Delete a contact](https://www.holded.com/developers/api-reference/contact/delete-a-contact) |
| `delete_contact_group` | contacts | DELETE | `/api/v2/contact-groups/{contactGroupId}` | [Delete a contact group](https://www.holded.com/developers/api-reference/contact-group/delete-a-contact-group) |
| `delete_credit_note` | sales | DELETE | `/api/v2/credit-notes/{creditNoteId}` | [Delete a credit note](https://www.holded.com/developers/api-reference/credit-notes/delete-a-credit-note) |
| `delete_employee` | team | DELETE | `/api/v2/employees/{employeeId}` | [Delete an employee](https://www.holded.com/developers/api-reference/employees/delete-an-employee) |
| `delete_employee_time` | team | DELETE | `/api/v2/employee-times/{timeId}` | [Delete an employee time entry](https://www.holded.com/developers/api-reference/employee-time-tracking/delete-an-employee-time-entry) |
| `delete_estimate` | sales | DELETE | `/api/v2/estimates/{estimateId}` | [Delete an estimate](https://www.holded.com/developers/api-reference/estimates/delete-an-estimate) |
| `delete_event` | calendar | DELETE | `/api/v2/events/{eventId}` | [Delete an event](https://www.holded.com/developers/api-reference/events/delete-an-event) |
| `delete_expenses_account` | accounting | DELETE | `/api/v2/expenses-accounts/{expensesAccountId}` | [Delete an expenses account](https://www.holded.com/developers/api-reference/expenses-accounts/delete-an-expenses-account) |
| `delete_funnel` | crm | DELETE | `/api/v2/funnels/{funnelId}` | [Delete a funnel](https://www.holded.com/developers/api-reference/funnels/delete-a-funnel) |
| `delete_inbox` | inbox | DELETE | `/api/v2/inbox/{incomingDocumentId}` | [Delete an incoming document](https://www.holded.com/developers/api-reference/inbox/delete-an-incoming-document) |
| `delete_invoice` | sales | DELETE | `/api/v2/invoices/{invoiceId}` | [Delete an invoice](https://www.holded.com/developers/api-reference/invoices/delete-an-invoice) |
| `delete_invoice_recurring` | sales | DELETE | `/api/v2/recurring-invoices/{invoiceRecurringId}` | [Delete a recurring invoice](https://www.holded.com/developers/api-reference/recurring-invoices/delete-a-recurring-invoice) |
| `delete_invoicing_forecast` | treasury | DELETE | `/api/v2/treasury/cashflow/invoicing-forecasts/{forecastId}` | [Delete an invoicing forecast](https://www.holded.com/developers/api-reference/invoicing-forecast/delete-an-invoicing-forecast) |
| `delete_lead` | crm | DELETE | `/api/v2/leads/{leadId}` | [Delete a lead](https://www.holded.com/developers/api-reference/leads/delete-a-lead) |
| `delete_lead_task` | crm | DELETE | `/api/v2/leads/{leadId}/tasks` | [Delete a lead task](https://www.holded.com/developers/api-reference/leads/delete-a-lead-task) |
| `delete_ledger_entry` | accounting | DELETE | `/api/v2/ledger-entries/{ledgerEntryId}` | [Delete a ledger entry](https://www.holded.com/developers/api-reference/accounting/delete-a-ledger-entry) |
| `delete_numbering_series` | sales | DELETE | `/api/v2/numbering-series/{type}/{numberingSeriesId}` | [Delete a numbering series](https://www.holded.com/developers/api-reference/numbering-series/delete-a-numbering-series) |
| `delete_payment` | accounting | DELETE | `/api/v2/payments/{paymentId}` | [Delete a payment](https://www.holded.com/developers/api-reference/payment/delete-a-payment) |
| `delete_payment_method` | treasury | DELETE | `/api/v2/payment-methods/{paymentMethodId}` | [Delete a payment method](https://www.holded.com/developers/api-reference/payment-methods/delete-a-payment-method) |
| `delete_payslip` | team | DELETE | `/api/v2/payslips/{payslipId}` | [Delete a payslip](https://www.holded.com/developers/api-reference/payslips/delete-a-payslip) |
| `delete_payslip_payment` | team | DELETE | `/api/v2/payslips/{payslipId}/payments/{paymentId}` | [Delete a payment from a payslip](https://www.holded.com/developers/api-reference/payslips/delete-a-payment-from-a-payslip) |
| `delete_price_list` | inventory | DELETE | `/api/v2/price-lists/{priceListId}` | [Delete a price list](https://www.holded.com/developers/api-reference/price-lists/delete-a-price-list) |
| `delete_product` | inventory | DELETE | `/api/v2/products/{productId}` | [Delete a product](https://www.holded.com/developers/api-reference/products/delete-a-product) |
| `delete_production_order` | inventory | DELETE | `/api/v2/production-orders/{productionOrderId}` | [Delete a production order](https://www.holded.com/developers/api-reference/production-orders/delete-a-production-order) |
| `delete_proforma` | sales | DELETE | `/api/v2/proformas/{proformaId}` | [Delete a proforma](https://www.holded.com/developers/api-reference/proformas/delete-a-proforma) |
| `delete_project` | projects | DELETE | `/api/v2/projects/{projectId}` | [Delete a project](https://www.holded.com/developers/api-reference/projects/delete-a-project) |
| `delete_project_time` | projects | DELETE | `/api/v2/projects/{projectId}/times/{timeId}` | [Delete a project time entry](https://www.holded.com/developers/api-reference/project-time-tracking/delete-a-project-time-entry) |
| `delete_purchase` | accounting | DELETE | `/api/v2/purchases/{purchaseId}` | [Delete a purchase](https://www.holded.com/developers/api-reference/purchases/delete-a-purchase) |
| `delete_purchase_order` | inventory | DELETE | `/api/v2/purchase-orders/{purchaseOrderId}` | [Delete a purchase order](https://www.holded.com/developers/api-reference/purchase-orders/delete-a-purchase-order) |
| `delete_purchase_shipment` | inventory | DELETE | `/api/v2/purchase-shipments/{purchaseShipmentId}` | [Delete a purchase shipment](https://www.holded.com/developers/api-reference/purchase-shipments/delete-a-purchase-shipment) |
| `delete_receipt_note` | sales | DELETE | `/api/v2/receipt-notes/{receiptNoteId}` | [Delete a receipt note](https://www.holded.com/developers/api-reference/receipt-notes/delete-a-receipt-note) |
| `delete_salary_record` | team | DELETE | `/api/v2/salary-records/{salaryRecordId}` | [Delete a salary record](https://www.holded.com/developers/api-reference/salary-records/delete-a-salary-record) |
| `delete_sales_channel` | sales | DELETE | `/api/v2/sales-channels/{salesChannelId}` | [Delete a sales channel](https://www.holded.com/developers/api-reference/sales-channels/delete-a-sales-channel) |
| `delete_sales_order` | inventory | DELETE | `/api/v2/sales-orders/{salesOrderId}` | [Delete a sales order](https://www.holded.com/developers/api-reference/sales-orders/delete-a-sales-order) |
| `delete_sales_receipt` | sales | DELETE | `/api/v2/sales-receipts/{salesReceiptId}` | [Delete a sales receipt](https://www.holded.com/developers/api-reference/sales-receipts/delete-a-sales-receipt) |
| `delete_service` | sales | DELETE | `/api/v2/services/{serviceId}` | [Delete a service](https://www.holded.com/developers/api-reference/services/delete-a-service) |
| `delete_tag` | contacts | DELETE | `/api/v2/tags/{tag}` | [Delete a tag](https://www.holded.com/developers/api-reference/tags/delete-a-tag) |
| `delete_task` | projects | DELETE | `/api/v2/tasks/{taskId}` | [Delete a task](https://www.holded.com/developers/api-reference/tasks/delete-a-task) |
| `delete_warehouse` | inventory | DELETE | `/api/v2/warehouses/{warehouseId}` | [Delete a warehouse](https://www.holded.com/developers/api-reference/warehouses/delete-a-warehouse) |
| `delete_waybill` | inventory | DELETE | `/api/v2/waybills/{waybillId}` | [Delete a waybill](https://www.holded.com/developers/api-reference/waybills/delete-a-waybill) |
| `delete_webhook` | developers | DELETE | `/api/v2/webhooks/{webhookId}` | [Delete a webhook](https://www.holded.com/developers/api-reference/webhooks/delete-a-webhook) |
| `disable_webhook` | developers | POST | `/api/v2/webhooks/{webhookId}/disable` | [Disable a webhook](https://www.holded.com/developers/api-reference/webhooks/disable-a-webhook) |
| `download_inbox_file` | inbox | GET | `/api/v2/inbox/{incomingDocumentId}/files/{filename}/download` | [Download a file from an inbox document](https://www.holded.com/developers/api-reference/inbox/download-a-file-from-an-inbox-document) |
| `edit_invoicing_forecast` | treasury | PUT | `/api/v2/treasury/cashflow/invoicing-forecasts/{forecastId}` | [Edit an invoicing forecast](https://www.holded.com/developers/api-reference/invoicing-forecast/edit-an-invoicing-forecast) |
| `enable_webhook` | developers | POST | `/api/v2/webhooks/{webhookId}/enable` | [Enable a webhook](https://www.holded.com/developers/api-reference/webhooks/enable-a-webhook) |
| `export_inbox` | inbox | POST | `/api/v2/inbox/{incomingDocumentId}/export` | [Convert incoming document into a purchase document](https://www.holded.com/developers/api-reference/inbox/convert-incoming-document-into-a-purchase-document) |
| `find_invoices_by_document_number` | sales | GET | `/api/v2/invoices/find-by-number` | [Find invoices by document number](https://www.holded.com/developers/api-reference/invoices/find-invoices-by-document-number) |
| `get_banking_account` | treasury | GET | `/api/v2/treasury/accounts/{id}` | [Get a banking account by ID](https://www.holded.com/developers/api-reference/banking-accounts/get-a-banking-account-by-id) |
| `get_booking` | calendar | GET | `/api/v2/bookings/{bookingId}` | [Get a booking by ID](https://www.holded.com/developers/api-reference/bookings/get-a-booking-by-id) |
| `get_booking_location_slots` | calendar | GET | `/api/v2/booking-locations/{locationId}/slots` | [Get available slots for a location](https://www.holded.com/developers/api-reference/bookings/get-available-slots-for-a-location) |
| `get_contact` | contacts | GET | `/api/v2/contacts/{contactId}` | [Get a contact by ID](https://www.holded.com/developers/api-reference/contact/get-a-contact-by-id) |
| `get_contact_attachment` | contacts | GET | `/api/v2/contacts/{contactId}/attachments/{filename}` | [Get a contact attachment](https://www.holded.com/developers/api-reference/contact/get-a-contact-attachment) |
| `get_contact_group` | contacts | GET | `/api/v2/contact-groups/{contactGroupId}` | [Get a contact group](https://www.holded.com/developers/api-reference/contact-group/get-a-contact-group) |
| `get_contact_portal_link` | contacts | GET | `/api/v2/contacts/{contactId}/portal-link` | [Get client portal link for a contact](https://www.holded.com/developers/api-reference/contact/get-client-portal-link-for-a-contact) |
| `get_credit_note` | sales | GET | `/api/v2/credit-notes/{creditNoteId}` | [Get a credit note](https://www.holded.com/developers/api-reference/credit-notes/get-a-credit-note) |
| `get_credit_note_attachment` | sales | GET | `/api/v2/credit-notes/{creditNoteId}/attachments/{attachmentId}` | [Get credit note attachment](https://www.holded.com/developers/api-reference/credit-notes/get-credit-note-attachment) |
| `get_credit_note_pdf` | sales | GET | `/api/v2/credit-notes/{creditNoteId}/pdf` | [Get credit note PDF](https://www.holded.com/developers/api-reference/credit-notes/get-credit-note-pdf) |
| `get_employee` | team | GET | `/api/v2/employees/{employeeId}` | [Get an employee](https://www.holded.com/developers/api-reference/employees/get-an-employee) |
| `get_employee_contract` | team | GET | `/api/v2/employees/{employeeId}/contract` | [Get active contract](https://www.holded.com/developers/api-reference/employees/get-active-contract) |
| `get_employee_time` | team | GET | `/api/v2/employee-times/{timeId}` | [Get an employee time entry](https://www.holded.com/developers/api-reference/employee-time-tracking/get-an-employee-time-entry) |
| `get_estimate` | sales | GET | `/api/v2/estimates/{estimateId}` | [Get an estimate](https://www.holded.com/developers/api-reference/estimates/get-an-estimate) |
| `get_estimate_attachment` | sales | GET | `/api/v2/estimates/{estimateId}/attachments/{attachmentId}` | [Get estimate attachment](https://www.holded.com/developers/api-reference/estimates/get-estimate-attachment) |
| `get_estimate_pdf` | sales | GET | `/api/v2/estimates/{estimateId}/pdf` | [Get estimate PDF](https://www.holded.com/developers/api-reference/estimates/get-estimate-pdf) |
| `get_event` | calendar | GET | `/api/v2/events/{eventId}` | [Get an event by ID](https://www.holded.com/developers/api-reference/events/get-an-event-by-id) |
| `get_expenses_account` | accounting | GET | `/api/v2/expenses-accounts/{expensesAccountId}` | [Get an expenses account by ID](https://www.holded.com/developers/api-reference/expenses-accounts/get-an-expenses-account-by-id) |
| `get_funnel` | crm | GET | `/api/v2/funnels/{funnelId}` | [Get a funnel](https://www.holded.com/developers/api-reference/funnels/get-a-funnel) |
| `get_inbox` | inbox | GET | `/api/v2/inbox/{incomingDocumentId}` | [Get an incoming document by ID](https://www.holded.com/developers/api-reference/inbox/get-an-incoming-document-by-id) |
| `get_invoice` | sales | GET | `/api/v2/invoices/{invoiceId}` | [Get an invoice](https://www.holded.com/developers/api-reference/invoices/get-an-invoice) |
| `get_invoice_attachment` | sales | GET | `/api/v2/invoices/{invoiceId}/attachments/{attachmentId}` | [Get invoice attachment](https://www.holded.com/developers/api-reference/invoices/get-invoice-attachment) |
| `get_invoice_pdf` | sales | GET | `/api/v2/invoices/{invoiceId}/pdf` | [Get invoice PDF](https://www.holded.com/developers/api-reference/invoices/get-invoice-pdf) |
| `get_invoice_recurring` | sales | GET | `/api/v2/recurring-invoices/{invoiceRecurringId}` | [Get a recurring invoice](https://www.holded.com/developers/api-reference/recurring-invoices/get-a-recurring-invoice) |
| `get_invoicing_forecast` | treasury | GET | `/api/v2/treasury/cashflow/invoicing-forecasts/{forecastId}` | [Get an invoicing forecast](https://www.holded.com/developers/api-reference/invoicing-forecast/get-an-invoicing-forecast) |
| `get_lead` | crm | GET | `/api/v2/leads/{leadId}` | [Get a lead](https://www.holded.com/developers/api-reference/leads/get-a-lead) |
| `get_ledger_entry` | accounting | GET | `/api/v2/ledger-entries/{ledgerEntryId}` | [Get a ledger entry](https://www.holded.com/developers/api-reference/accounting/get-a-ledger-entry) |
| `get_payment` | accounting | GET | `/api/v2/payments/{paymentId}` | [Get a payment by ID](https://www.holded.com/developers/api-reference/payment/get-a-payment-by-id) |
| `get_payment_method` | treasury | GET | `/api/v2/payment-methods/{paymentMethodId}` | [Get a payment method by ID](https://www.holded.com/developers/api-reference/payment-methods/get-a-payment-method-by-id) |
| `get_payslip` | team | GET | `/api/v2/payslips/{payslipId}` | [Get a payslip](https://www.holded.com/developers/api-reference/payslips/get-a-payslip) |
| `get_payslip_pdf` | team | GET | `/api/v2/payslips/{payslipId}/pdf` | [Download a payslip PDF](https://www.holded.com/developers/api-reference/payslips/download-a-payslip-pdf) |
| `get_price_list` | inventory | GET | `/api/v2/price-lists/{priceListId}` | [Get a price list by ID](https://www.holded.com/developers/api-reference/price-lists/get-a-price-list-by-id) |
| `get_product` | inventory | GET | `/api/v2/products/{productId}` | [Get a product by ID](https://www.holded.com/developers/api-reference/products/get-a-product-by-id) |
| `get_product_image` | inventory | GET | `/api/v2/products/{productId}/images/{imageId}` | [Get a product image by ID](https://www.holded.com/developers/api-reference/products/get-a-product-image-by-id) |
| `get_product_main_image` | inventory | GET | `/api/v2/products/{productId}/image` | [Get the main product image](https://www.holded.com/developers/api-reference/products/get-the-main-product-image) |
| `get_product_stock` | inventory | GET | `/api/v2/products/{productId}/stock` | [Get stock availability for a product](https://www.holded.com/developers/api-reference/products/get-stock-availability-for-a-product) |
| `get_product_stock_transit` | inventory | GET | `/api/v2/products/{productId}/stock/transit` | [Get stock in transit for a product](https://www.holded.com/developers/api-reference/products/get-stock-in-transit-for-a-product) |
| `get_production_order` | inventory | GET | `/api/v2/production-orders/{productionOrderId}` | [Get a production order](https://www.holded.com/developers/api-reference/production-orders/get-a-production-order) |
| `get_proforma` | sales | GET | `/api/v2/proformas/{proformaId}` | [Get a proforma](https://www.holded.com/developers/api-reference/proformas/get-a-proforma) |
| `get_proforma_attachment` | sales | GET | `/api/v2/proformas/{proformaId}/attachments/{attachmentId}` | [Get proforma attachment](https://www.holded.com/developers/api-reference/proformas/get-proforma-attachment) |
| `get_proforma_pdf` | sales | GET | `/api/v2/proformas/{proformaId}/pdf` | [Get proforma PDF](https://www.holded.com/developers/api-reference/proformas/get-proforma-pdf) |
| `get_project` | projects | GET | `/api/v2/projects/{projectId}` | [Get a project](https://www.holded.com/developers/api-reference/projects/get-a-project) |
| `get_project_summary` | projects | GET | `/api/v2/projects/{projectId}/summary` | [Get a project summary](https://www.holded.com/developers/api-reference/projects/get-a-project-summary) |
| `get_project_time` | projects | GET | `/api/v2/projects/{projectId}/times/{timeId}` | [Get a project time entry](https://www.holded.com/developers/api-reference/project-time-tracking/get-a-project-time-entry) |
| `get_purchase` | accounting | GET | `/api/v2/purchases/{purchaseId}` | [Get a purchase](https://www.holded.com/developers/api-reference/purchases/get-a-purchase) |
| `get_purchase_attachment` | accounting | GET | `/api/v2/purchases/{purchaseId}/attachments/{attachmentId}` | [Get purchase attachment](https://www.holded.com/developers/api-reference/purchases/get-purchase-attachment) |
| `get_purchase_order` | inventory | GET | `/api/v2/purchase-orders/{purchaseOrderId}` | [Get a purchase order](https://www.holded.com/developers/api-reference/purchase-orders/get-a-purchase-order) |
| `get_purchase_order_attachment` | inventory | GET | `/api/v2/purchase-orders/{purchaseOrderId}/attachments/{attachmentId}` | [Get purchase order attachment](https://www.holded.com/developers/api-reference/purchase-orders/get-purchase-order-attachment) |
| `get_purchase_order_pdf` | inventory | GET | `/api/v2/purchase-orders/{purchaseOrderId}/pdf` | [Get purchase order PDF](https://www.holded.com/developers/api-reference/purchase-orders/get-purchase-order-pdf) |
| `get_purchase_order_received_items` | inventory | GET | `/api/v2/purchase-orders/{purchaseOrderId}/received-items` | [Get received items for a purchase order](https://www.holded.com/developers/api-reference/purchase-orders/get-received-items-for-a-purchase-order) |
| `get_purchase_refund` | accounting | GET | `/api/v2/purchases/refund/{purchaseRefundId}` | [Get a purchase refund](https://www.holded.com/developers/api-reference/purchases/get-a-purchase-refund) |
| `get_purchase_shipment` | inventory | GET | `/api/v2/purchase-shipments/{purchaseShipmentId}` | [Get a purchase shipment](https://www.holded.com/developers/api-reference/purchase-shipments/get-a-purchase-shipment) |
| `get_receipt_note` | sales | GET | `/api/v2/receipt-notes/{receiptNoteId}` | [Get a receipt note](https://www.holded.com/developers/api-reference/receipt-notes/get-a-receipt-note) |
| `get_receipt_note_attachment` | sales | GET | `/api/v2/receipt-notes/{receiptNoteId}/attachments/{attachmentId}` | [Get receipt note attachment](https://www.holded.com/developers/api-reference/receipt-notes/get-receipt-note-attachment) |
| `get_receipt_note_pdf` | sales | GET | `/api/v2/receipt-notes/{receiptNoteId}/pdf` | [Get receipt note PDF](https://www.holded.com/developers/api-reference/receipt-notes/get-receipt-note-pdf) |
| `get_recurring_schedule` | sales | GET | `/api/v2/recurring-invoices/{invoiceRecurringId}/schedule` | [Get recurring invoice schedule](https://www.holded.com/developers/api-reference/recurring-invoices/get-recurring-invoice-schedule) |
| `get_remittance` | treasury | GET | `/api/v2/treasury/remittances/{remittanceId}` | [Get a remittance](https://www.holded.com/developers/api-reference/remittances/get-a-remittance) |
| `get_salary_record` | team | GET | `/api/v2/salary-records/{salaryRecordId}` | [Get a salary record](https://www.holded.com/developers/api-reference/salary-records/get-a-salary-record) |
| `get_salary_record_form_data` | team | GET | `/api/v2/salary-records/form-data` | [Get salary record form data](https://www.holded.com/developers/api-reference/salary-records/get-salary-record-form-data) |
| `get_salary_record_pdf` | team | GET | `/api/v2/salary-records/{salaryRecordId}/pdf` | [Download a salary record PDF](https://www.holded.com/developers/api-reference/salary-records/download-a-salary-record-pdf) |
| `get_sales_channel` | sales | GET | `/api/v2/sales-channels/{salesChannelId}` | [Get a sales channel by ID](https://www.holded.com/developers/api-reference/sales-channels/get-a-sales-channel-by-id) |
| `get_sales_order` | inventory | GET | `/api/v2/sales-orders/{salesOrderId}` | [Get a sales order](https://www.holded.com/developers/api-reference/sales-orders/get-a-sales-order) |
| `get_sales_order_attachment` | inventory | GET | `/api/v2/sales-orders/{salesOrderId}/attachments/{attachmentId}` | [Get sales order attachment](https://www.holded.com/developers/api-reference/sales-orders/get-sales-order-attachment) |
| `get_sales_order_pdf` | inventory | GET | `/api/v2/sales-orders/{salesOrderId}/pdf` | [Get sales order PDF](https://www.holded.com/developers/api-reference/sales-orders/get-sales-order-pdf) |
| `get_sales_order_shipped_items` | inventory | GET | `/api/v2/sales-orders/{salesOrderId}/shipped-items` | [Get shipped items for a sales order](https://www.holded.com/developers/api-reference/sales-orders/get-shipped-items-for-a-sales-order) |
| `get_sales_receipt` | sales | GET | `/api/v2/sales-receipts/{salesReceiptId}` | [Get a sales receipt](https://www.holded.com/developers/api-reference/sales-receipts/get-a-sales-receipt) |
| `get_sales_receipt_attachment` | sales | GET | `/api/v2/sales-receipts/{salesReceiptId}/attachments/{attachmentId}` | [Get sales receipt attachment](https://www.holded.com/developers/api-reference/sales-receipts/get-sales-receipt-attachment) |
| `get_sales_receipt_pdf` | sales | GET | `/api/v2/sales-receipts/{salesReceiptId}/pdf` | [Get sales receipt PDF](https://www.holded.com/developers/api-reference/sales-receipts/get-sales-receipt-pdf) |
| `get_service` | sales | GET | `/api/v2/services/{serviceId}` | [Get a service](https://www.holded.com/developers/api-reference/services/get-a-service) |
| `get_task` | projects | GET | `/api/v2/tasks/{taskId}` | [Get a task](https://www.holded.com/developers/api-reference/tasks/get-a-task) |
| `get_tax_per_country_sorted_keys` | accounting | GET | `/api/v2/taxes/keys-by-country` | [Get sorted tax keys by country and section](https://www.holded.com/developers/api-reference/tax/get-sorted-tax-keys-by-country-and-section) |
| `get_time_off` | team | GET | `/api/v2/employees/{employeeId}/time-offs/{timeOffId}` | [Get a time off request (absence / holiday)](https://www.holded.com/developers/api-reference/time-off/get-a-time-off-request-absence-holiday) |
| `get_usage` | developers | GET | `/api/v2/usage` | [Get API usage (automation token)](https://www.holded.com/developers/api-reference/developers/get-api-usage-automation-token) |
| `get_usage_by_type` | developers | GET | `/api/v2/usage/{type}` | [Get API usage by type](https://www.holded.com/developers/api-reference/developers/get-api-usage-by-type) |
| `get_warehouse` | inventory | GET | `/api/v2/warehouses/{warehouseId}` | [Get a warehouse by ID](https://www.holded.com/developers/api-reference/warehouses/get-a-warehouse-by-id) |
| `get_warehouse_stock` | inventory | GET | `/api/v2/warehouses/{warehouseId}/stock` | [Get stock levels for a warehouse](https://www.holded.com/developers/api-reference/warehouses/get-stock-levels-for-a-warehouse) |
| `get_waybill` | inventory | GET | `/api/v2/waybills/{waybillId}` | [Get a waybill](https://www.holded.com/developers/api-reference/waybills/get-a-waybill) |
| `get_waybill_attachment` | inventory | GET | `/api/v2/waybills/{waybillId}/attachments/{attachmentId}` | [Get waybill attachment](https://www.holded.com/developers/api-reference/waybills/get-waybill-attachment) |
| `get_waybill_pdf` | inventory | GET | `/api/v2/waybills/{waybillId}/pdf` | [Get waybill PDF](https://www.holded.com/developers/api-reference/waybills/get-waybill-pdf) |
| `get_webhook` | developers | GET | `/api/v2/webhooks/{webhookId}` | [Get a webhook](https://www.holded.com/developers/api-reference/webhooks/get-a-webhook) |
| `get_webhook_events` | developers | GET | `/api/v2/webhooks/events` | [List supported webhook event types](https://www.holded.com/developers/api-reference/webhooks/list-supported-webhook-event-types) |
| `list_accounting_accounts` | accounting | GET | `/api/v2/accounting-accounts` | [List chart of accounts](https://www.holded.com/developers/api-reference/accounting/list-chart-of-accounts) |
| `list_all_employee_times` | team | GET | `/api/v2/employee-times` | [List all employee time entries](https://www.holded.com/developers/api-reference/employee-time-tracking/list-all-employee-time-entries) |
| `list_all_project_times` | projects | GET | `/api/v2/project-times` | [List all project time entries](https://www.holded.com/developers/api-reference/project-time-tracking/list-all-project-time-entries) |
| `list_all_time_offs` | team | GET | `/api/v2/employees/time-offs` | [List all time off requests (absences / holidays)](https://www.holded.com/developers/api-reference/time-off/list-all-time-off-requests-absences-holidays) |
| `list_banking_account_bank_movements` | treasury | GET | `/api/v2/treasury/accounts/{id}/bank-movements` | [List banking account movements](https://www.holded.com/developers/api-reference/banking-accounts/list-banking-account-movements) |
| `list_banking_account_cash_movements` | treasury | GET | `/api/v2/treasury/accounts/{id}/cash-movements` | [List banking account cash movements](https://www.holded.com/developers/api-reference/banking-accounts/list-banking-account-cash-movements) |
| `list_banking_accounts` | treasury | GET | `/api/v2/treasury/accounts` | [List banking accounts](https://www.holded.com/developers/api-reference/banking-accounts/list-banking-accounts) |
| `list_booking_locations` | calendar | GET | `/api/v2/booking-locations` | [List all booking locations](https://www.holded.com/developers/api-reference/bookings/list-all-booking-locations) |
| `list_bookings` | calendar | GET | `/api/v2/bookings` | [List all bookings](https://www.holded.com/developers/api-reference/bookings/list-all-bookings) |
| `list_business_plan_goals` | treasury | GET | `/api/v2/business-plan/goals` | [List business plan goals vs actuals](https://www.holded.com/developers/api-reference/business-plan/list-business-plan-goals-vs-actuals) |
| `list_business_plan_scenarios` | treasury | GET | `/api/v2/business-plan/scenarios` | [List business plan scenarios](https://www.holded.com/developers/api-reference/business-plan/list-business-plan-scenarios) |
| `list_contact_attachments` | contacts | GET | `/api/v2/contacts/{contactId}/attachments` | [List contact attachments](https://www.holded.com/developers/api-reference/contact/list-contact-attachments) |
| `list_contact_groups` | contacts | GET | `/api/v2/contact-groups` | [List contact groups](https://www.holded.com/developers/api-reference/contact-group/list-contact-groups) |
| `list_contacts` | contacts | GET | `/api/v2/contacts` | [List contacts](https://www.holded.com/developers/api-reference/contact/list-contacts) |
| `list_credit_note_attachments` | sales | GET | `/api/v2/credit-notes/{creditNoteId}/attachments` | [List credit note attachments](https://www.holded.com/developers/api-reference/credit-notes/list-credit-note-attachments) |
| `list_credit_notes` | sales | GET | `/api/v2/credit-notes` | [List credit notes](https://www.holded.com/developers/api-reference/credit-notes/list-credit-notes) |
| `list_employee_time_offs` | team | GET | `/api/v2/employees/{employeeId}/time-offs` | [List time off requests for an employee (absences / holidays)](https://www.holded.com/developers/api-reference/time-off/list-time-off-requests-for-an-employee-absences-holidays) |
| `list_employee_times` | team | GET | `/api/v2/employees/{employeeId}/times` | [List time entries for an employee](https://www.holded.com/developers/api-reference/employee-time-tracking/list-time-entries-for-an-employee) |
| `list_employees` | team | GET | `/api/v2/employees` | [List all employees](https://www.holded.com/developers/api-reference/employees/list-all-employees) |
| `list_estimate_attachments` | sales | GET | `/api/v2/estimates/{estimateId}/attachments` | [List estimate attachments](https://www.holded.com/developers/api-reference/estimates/list-estimate-attachments) |
| `list_estimates` | sales | GET | `/api/v2/estimates` | [List estimates](https://www.holded.com/developers/api-reference/estimates/list-estimates) |
| `list_events` | calendar | GET | `/api/v2/events` | [List all events](https://www.holded.com/developers/api-reference/events/list-all-events) |
| `list_expenses_accounts` | accounting | GET | `/api/v2/expenses-accounts` | [List all expenses accounts](https://www.holded.com/developers/api-reference/expenses-accounts/list-all-expenses-accounts) |
| `list_funnels` | crm | GET | `/api/v2/funnels` | [List all funnels](https://www.holded.com/developers/api-reference/funnels/list-all-funnels) |
| `list_inbox` | inbox | GET | `/api/v2/inbox` | [List inbox incoming documents](https://www.holded.com/developers/api-reference/inbox/list-inbox-incoming-documents) |
| `list_invoice_attachments` | sales | GET | `/api/v2/invoices/{invoiceId}/attachments` | [List invoice attachments](https://www.holded.com/developers/api-reference/invoices/list-invoice-attachments) |
| `list_invoice_recurrings` | sales | GET | `/api/v2/recurring-invoices` | [List recurring invoices](https://www.holded.com/developers/api-reference/recurring-invoices/list-recurring-invoices) |
| `list_invoices` | sales | GET | `/api/v2/invoices` | [List invoices](https://www.holded.com/developers/api-reference/invoices/list-invoices) |
| `list_invoicing_forecasts` | treasury | GET | `/api/v2/treasury/cashflow/invoicing-forecasts` | [List invoicing forecasts](https://www.holded.com/developers/api-reference/invoicing-forecast/list-invoicing-forecasts) |
| `list_leads` | crm | GET | `/api/v2/leads` | [List all leads](https://www.holded.com/developers/api-reference/leads/list-all-leads) |
| `list_ledger_entries` | accounting | GET | `/api/v2/ledger-entries` | [List ledger entries](https://www.holded.com/developers/api-reference/accounting/list-ledger-entries) |
| `list_numbering_series` | sales | GET | `/api/v2/numbering-series/{type}` | [List numbering series by document type](https://www.holded.com/developers/api-reference/numbering-series/list-numbering-series-by-document-type) |
| `list_payment_methods` | treasury | GET | `/api/v2/payment-methods` | [List payment methods](https://www.holded.com/developers/api-reference/payment-methods/list-payment-methods) |
| `list_payments` | accounting | GET | `/api/v2/payments` | [List payments](https://www.holded.com/developers/api-reference/payment/list-payments) |
| `list_payslips` | team | GET | `/api/v2/payslips` | [List payslips](https://www.holded.com/developers/api-reference/payslips/list-payslips) |
| `list_price_lists` | inventory | GET | `/api/v2/price-lists` | [List price lists](https://www.holded.com/developers/api-reference/price-lists/list-price-lists) |
| `list_product_images` | inventory | GET | `/api/v2/products/{productId}/images` | [List product images](https://www.holded.com/developers/api-reference/products/list-product-images) |
| `list_production_orders` | inventory | GET | `/api/v2/production-orders` | [List production orders](https://www.holded.com/developers/api-reference/production-orders/list-production-orders) |
| `list_products` | inventory | GET | `/api/v2/products` | [List all products](https://www.holded.com/developers/api-reference/products/list-all-products) |
| `list_proforma_attachments` | sales | GET | `/api/v2/proformas/{proformaId}/attachments` | [List proforma attachments](https://www.holded.com/developers/api-reference/proformas/list-proforma-attachments) |
| `list_proformas` | sales | GET | `/api/v2/proformas` | [List proformas](https://www.holded.com/developers/api-reference/proformas/list-proformas) |
| `list_project_times` | projects | GET | `/api/v2/projects/{projectId}/times` | [List time entries for a project](https://www.holded.com/developers/api-reference/project-time-tracking/list-time-entries-for-a-project) |
| `list_projects` | projects | GET | `/api/v2/projects` | [List projects](https://www.holded.com/developers/api-reference/projects/list-projects) |
| `list_purchase_attachments` | accounting | GET | `/api/v2/purchases/{purchaseId}/attachments` | [List purchase attachments](https://www.holded.com/developers/api-reference/purchases/list-purchase-attachments) |
| `list_purchase_order_attachments` | inventory | GET | `/api/v2/purchase-orders/{purchaseOrderId}/attachments` | [List purchase order attachments](https://www.holded.com/developers/api-reference/purchase-orders/list-purchase-order-attachments) |
| `list_purchase_orders` | inventory | GET | `/api/v2/purchase-orders` | [List purchase orders](https://www.holded.com/developers/api-reference/purchase-orders/list-purchase-orders) |
| `list_purchase_refunds` | accounting | GET | `/api/v2/purchase-refunds` | [List purchase refunds](https://www.holded.com/developers/api-reference/purchases/list-purchase-refunds) |
| `list_purchase_shipments` | inventory | GET | `/api/v2/purchase-shipments` | [List purchase shipments](https://www.holded.com/developers/api-reference/purchase-shipments/list-purchase-shipments) |
| `list_purchases` | accounting | GET | `/api/v2/purchases` | [List purchases](https://www.holded.com/developers/api-reference/purchases/list-purchases) |
| `list_receipt_note_attachments` | sales | GET | `/api/v2/receipt-notes/{receiptNoteId}/attachments` | [List receipt note attachments](https://www.holded.com/developers/api-reference/receipt-notes/list-receipt-note-attachments) |
| `list_receipt_notes` | sales | GET | `/api/v2/receipt-notes` | [List receipt notes](https://www.holded.com/developers/api-reference/receipt-notes/list-receipt-notes) |
| `list_remittances` | treasury | GET | `/api/v2/treasury/remittances` | [List remittances](https://www.holded.com/developers/api-reference/remittances/list-remittances) |
| `list_salary_records` | team | GET | `/api/v2/salary-records` | [List salary records](https://www.holded.com/developers/api-reference/salary-records/list-salary-records) |
| `list_sales_channels` | sales | GET | `/api/v2/sales-channels` | [List all sales channels](https://www.holded.com/developers/api-reference/sales-channels/list-all-sales-channels) |
| `list_sales_order_attachments` | inventory | GET | `/api/v2/sales-orders/{salesOrderId}/attachments` | [List sales order attachments](https://www.holded.com/developers/api-reference/sales-orders/list-sales-order-attachments) |
| `list_sales_orders` | inventory | GET | `/api/v2/sales-orders` | [List sales orders](https://www.holded.com/developers/api-reference/sales-orders/list-sales-orders) |
| `list_sales_receipt_attachments` | sales | GET | `/api/v2/sales-receipts/{salesReceiptId}/attachments` | [List sales receipt attachments](https://www.holded.com/developers/api-reference/sales-receipts/list-sales-receipt-attachments) |
| `list_sales_receipts` | sales | GET | `/api/v2/sales-receipts` | [List sales receipts](https://www.holded.com/developers/api-reference/sales-receipts/list-sales-receipts) |
| `list_services` | sales | GET | `/api/v2/services` | [List services](https://www.holded.com/developers/api-reference/services/list-services) |
| `list_tags` | contacts | GET | `/api/v2/tags` | [List all tags](https://www.holded.com/developers/api-reference/tags/list-all-tags) |
| `list_tasks` | projects | GET | `/api/v2/tasks` | [List all tasks](https://www.holded.com/developers/api-reference/tasks/list-all-tasks) |
| `list_taxes` | accounting | GET | `/api/v2/taxes` | [List all taxes](https://www.holded.com/developers/api-reference/tax/list-all-taxes) |
| `list_warehouses` | inventory | GET | `/api/v2/warehouses` | [List all warehouses](https://www.holded.com/developers/api-reference/warehouses/list-all-warehouses) |
| `list_waybill_attachments` | inventory | GET | `/api/v2/waybills/{waybillId}/attachments` | [List waybill attachments](https://www.holded.com/developers/api-reference/waybills/list-waybill-attachments) |
| `list_waybills` | inventory | GET | `/api/v2/waybills` | [List waybills](https://www.holded.com/developers/api-reference/waybills/list-waybills) |
| `list_webhooks` | developers | GET | `/api/v2/webhooks` | [List webhooks](https://www.holded.com/developers/api-reference/webhooks/list-webhooks) |
| `pause` | team | POST | `/api/v2/employees/{employeeId}/pause` | [Pause an employee time session](https://www.holded.com/developers/api-reference/employee-time-tracking/pause-an-employee-time-session) |
| `preview_inbox_file` | inbox | GET | `/api/v2/inbox/{incomingDocumentId}/files/{filename}/preview` | [Get a processed thumbnail of a file from an inbox document](https://www.holded.com/developers/api-reference/inbox/get-a-processed-thumbnail-of-a-file-from-an-inbox-document) |
| `receive_purchase_order` | inventory | POST | `/api/v2/purchase-orders/{purchaseOrderId}/receive` | [Receive units of a purchase order](https://www.holded.com/developers/api-reference/purchase-orders/receive-units-of-a-purchase-order) |
| `reconcile_transaction_with_document` | treasury | POST | `/api/v2/treasury/accounts/{bankingAccountId}/bank-movements/{movementId}/reconcile` | [Reconcile a bank movement](https://www.holded.com/developers/api-reference/banking-accounts/reconcile-a-bank-movement) |
| `reject_estimate` | sales | POST | `/api/v2/estimates/{estimateId}/reject` | [Reject an estimate](https://www.holded.com/developers/api-reference/estimates/reject-an-estimate) |
| `search_contacts` | contacts | GET | `/api/v2/contacts/search` | [Search contacts by name](https://www.holded.com/developers/api-reference/contact/search-contacts-by-name) |
| `send_credit_note` | sales | POST | `/api/v2/credit-notes/{creditNoteId}/send` | [Send a credit note by email](https://www.holded.com/developers/api-reference/credit-notes/send-a-credit-note-by-email) |
| `send_estimate` | sales | POST | `/api/v2/estimates/{estimateId}/send` | [Send an estimate by email](https://www.holded.com/developers/api-reference/estimates/send-an-estimate-by-email) |
| `send_invoice` | sales | POST | `/api/v2/invoices/{invoiceId}/send` | [Send an invoice by email](https://www.holded.com/developers/api-reference/invoices/send-an-invoice-by-email) |
| `send_proforma` | sales | POST | `/api/v2/proformas/{proformaId}/send` | [Send a proforma by email](https://www.holded.com/developers/api-reference/proformas/send-a-proforma-by-email) |
| `send_purchase_order` | inventory | POST | `/api/v2/purchase-orders/{purchaseOrderId}/send` | [Send a purchase order by email](https://www.holded.com/developers/api-reference/purchase-orders/send-a-purchase-order-by-email) |
| `send_receipt_note` | sales | POST | `/api/v2/receipt-notes/{receiptNoteId}/send` | [Send a receipt note by email](https://www.holded.com/developers/api-reference/receipt-notes/send-a-receipt-note-by-email) |
| `send_sales_order` | inventory | POST | `/api/v2/sales-orders/{salesOrderId}/send` | [Send a sales order by email](https://www.holded.com/developers/api-reference/sales-orders/send-a-sales-order-by-email) |
| `send_sales_receipt` | sales | POST | `/api/v2/sales-receipts/{salesReceiptId}/send` | [Send a sales receipt by email](https://www.holded.com/developers/api-reference/sales-receipts/send-a-sales-receipt-by-email) |
| `send_waybill` | inventory | POST | `/api/v2/waybills/{waybillId}/send` | [Send a waybill by email](https://www.holded.com/developers/api-reference/waybills/send-a-waybill-by-email) |
| `set_credit_note_pipeline` | sales | PUT | `/api/v2/credit-notes/{creditNoteId}/pipeline` | [Set credit note pipeline](https://www.holded.com/developers/api-reference/credit-notes/set-credit-note-pipeline) |
| `set_estimate_pipeline` | sales | PUT | `/api/v2/estimates/{estimateId}/pipeline` | [Set estimate pipeline](https://www.holded.com/developers/api-reference/estimates/set-estimate-pipeline) |
| `set_invoice_pipeline` | sales | PUT | `/api/v2/invoices/{invoiceId}/pipeline` | [Set invoice pipeline](https://www.holded.com/developers/api-reference/invoices/set-invoice-pipeline) |
| `set_proforma_pipeline` | sales | PUT | `/api/v2/proformas/{proformaId}/pipeline` | [Set proforma pipeline](https://www.holded.com/developers/api-reference/proformas/set-proforma-pipeline) |
| `set_purchase_order_pipeline` | inventory | PUT | `/api/v2/purchase-orders/{purchaseOrderId}/pipeline` | [Set purchase order pipeline](https://www.holded.com/developers/api-reference/purchase-orders/set-purchase-order-pipeline) |
| `set_purchase_pipeline` | accounting | PUT | `/api/v2/purchases/{purchaseId}/pipeline` | [Set purchase pipeline](https://www.holded.com/developers/api-reference/purchases/set-purchase-pipeline) |
| `set_receipt_note_pipeline` | sales | PUT | `/api/v2/receipt-notes/{receiptNoteId}/pipeline` | [Set receipt note pipeline](https://www.holded.com/developers/api-reference/receipt-notes/set-receipt-note-pipeline) |
| `set_sales_order_pipeline` | inventory | PUT | `/api/v2/sales-orders/{salesOrderId}/pipeline` | [Set sales order pipeline](https://www.holded.com/developers/api-reference/sales-orders/set-sales-order-pipeline) |
| `set_sales_receipt_pipeline` | sales | PUT | `/api/v2/sales-receipts/{salesReceiptId}/pipeline` | [Set sales receipt pipeline](https://www.holded.com/developers/api-reference/sales-receipts/set-sales-receipt-pipeline) |
| `set_waybill_pipeline` | inventory | PUT | `/api/v2/waybills/{waybillId}/pipeline` | [Set waybill pipeline](https://www.holded.com/developers/api-reference/waybills/set-waybill-pipeline) |
| `ship_sales_order` | inventory | POST | `/api/v2/sales-orders/{salesOrderId}/ship` | [Ship all items in a sales order](https://www.holded.com/developers/api-reference/sales-orders/ship-all-items-in-a-sales-order) |
| `ship_sales_order_by_lines` | inventory | POST | `/api/v2/sales-orders/{salesOrderId}/ship-by-lines` | [Ship specific lines in a sales order](https://www.holded.com/developers/api-reference/sales-orders/ship-specific-lines-in-a-sales-order) |
| `skip_recurring_occurrence` | sales | POST | `/api/v2/recurring-invoices/{invoiceRecurringId}/skip` | [Skip a recurring invoice occurrence](https://www.holded.com/developers/api-reference/recurring-invoices/skip-a-recurring-invoice-occurrence) |
| `unpause` | team | POST | `/api/v2/employees/{employeeId}/unpause` | [Resume an employee time session](https://www.holded.com/developers/api-reference/employee-time-tracking/resume-an-employee-time-session) |
| `update_banking_account` | treasury | PUT | `/api/v2/treasury/accounts/{id}` | [Update a banking account](https://www.holded.com/developers/api-reference/banking-accounts/update-a-banking-account) |
| `update_booking` | calendar | PUT | `/api/v2/bookings/{bookingId}` | [Update a booking](https://www.holded.com/developers/api-reference/bookings/update-a-booking) |
| `update_contact` | contacts | PUT | `/api/v2/contacts/{contactId}` | [Update a contact](https://www.holded.com/developers/api-reference/contact/update-a-contact) |
| `update_contact_group` | contacts | PUT | `/api/v2/contact-groups/{contactGroupId}` | [Update a contact group](https://www.holded.com/developers/api-reference/contact-group/update-a-contact-group) |
| `update_credit_note` | sales | PUT | `/api/v2/credit-notes/{creditNoteId}` | [Update a credit note](https://www.holded.com/developers/api-reference/credit-notes/update-a-credit-note) |
| `update_employee` | team | PUT | `/api/v2/employees/{employeeId}` | [Update an employee](https://www.holded.com/developers/api-reference/employees/update-an-employee) |
| `update_employee_contract` | team | PUT | `/api/v2/employees/{employeeId}/contract` | [Update active contract](https://www.holded.com/developers/api-reference/employees/update-active-contract) |
| `update_employee_time` | team | PUT | `/api/v2/employee-times/{timeId}` | [Update an employee time entry](https://www.holded.com/developers/api-reference/employee-time-tracking/update-an-employee-time-entry) |
| `update_estimate` | sales | PUT | `/api/v2/estimates/{estimateId}` | [Update an estimate](https://www.holded.com/developers/api-reference/estimates/update-an-estimate) |
| `update_event` | calendar | PUT | `/api/v2/events/{eventId}` | [Update an event](https://www.holded.com/developers/api-reference/events/update-an-event) |
| `update_expenses_account` | accounting | PUT | `/api/v2/expenses-accounts/{expensesAccountId}` | [Update an expenses account](https://www.holded.com/developers/api-reference/expenses-accounts/update-an-expenses-account) |
| `update_funnel` | crm | PUT | `/api/v2/funnels/{funnelId}` | [Update a funnel](https://www.holded.com/developers/api-reference/funnels/update-a-funnel) |
| `update_inbox` | inbox | PUT | `/api/v2/inbox/{incomingDocumentId}` | [Update an incoming document](https://www.holded.com/developers/api-reference/inbox/update-an-incoming-document) |
| `update_invoice` | sales | PUT | `/api/v2/invoices/{invoiceId}` | [Update an invoice](https://www.holded.com/developers/api-reference/invoices/update-an-invoice) |
| `update_invoice_recurring` | sales | PUT | `/api/v2/recurring-invoices/{invoiceRecurringId}` | [Update a recurring invoice](https://www.holded.com/developers/api-reference/recurring-invoices/update-a-recurring-invoice) |
| `update_lead` | crm | PUT | `/api/v2/leads/{leadId}` | [Update a lead](https://www.holded.com/developers/api-reference/leads/update-a-lead) |
| `update_lead_dates` | crm | PUT | `/api/v2/leads/{leadId}/dates` | [Update lead dates](https://www.holded.com/developers/api-reference/leads/update-lead-dates) |
| `update_lead_note` | crm | PUT | `/api/v2/leads/{leadId}/notes` | [Update a lead note](https://www.holded.com/developers/api-reference/leads/update-a-lead-note) |
| `update_lead_stage` | crm | PUT | `/api/v2/leads/{leadId}/stage` | [Update a lead stage](https://www.holded.com/developers/api-reference/leads/update-a-lead-stage) |
| `update_lead_task` | crm | PUT | `/api/v2/leads/{leadId}/tasks` | [Update a lead task](https://www.holded.com/developers/api-reference/leads/update-a-lead-task) |
| `update_numbering_series` | sales | PUT | `/api/v2/numbering-series/{type}/{numberingSeriesId}` | [Update a numbering series](https://www.holded.com/developers/api-reference/numbering-series/update-a-numbering-series) |
| `update_payment` | accounting | PUT | `/api/v2/payments/{paymentId}` | [Update a payment](https://www.holded.com/developers/api-reference/payment/update-a-payment) |
| `update_payment_method` | treasury | PUT | `/api/v2/payment-methods/{paymentMethodId}` | [Update a payment method](https://www.holded.com/developers/api-reference/payment-methods/update-a-payment-method) |
| `update_price_list` | inventory | PATCH | `/api/v2/price-lists/{priceListId}` | [Update a price list](https://www.holded.com/developers/api-reference/price-lists/update-a-price-list) |
| `update_product` | inventory | PUT | `/api/v2/products/{productId}` | [Update a product](https://www.holded.com/developers/api-reference/products/update-a-product) |
| `update_product_stock` | inventory | PUT | `/api/v2/products/{productId}/stock` | [Update stock for a product](https://www.holded.com/developers/api-reference/products/update-stock-for-a-product) |
| `update_production_order` | inventory | PUT | `/api/v2/production-orders/{productionOrderId}` | [Update a production order](https://www.holded.com/developers/api-reference/production-orders/update-a-production-order) |
| `update_proforma` | sales | PUT | `/api/v2/proformas/{proformaId}` | [Update a proforma](https://www.holded.com/developers/api-reference/proformas/update-a-proforma) |
| `update_project` | projects | PUT | `/api/v2/projects/{projectId}` | [Update a project](https://www.holded.com/developers/api-reference/projects/update-a-project) |
| `update_project_time` | projects | PUT | `/api/v2/projects/{projectId}/times/{timeId}` | [Update a project time entry](https://www.holded.com/developers/api-reference/project-time-tracking/update-a-project-time-entry) |
| `update_purchase` | accounting | PUT | `/api/v2/purchases/{purchaseId}` | [Update a purchase](https://www.holded.com/developers/api-reference/purchases/update-a-purchase) |
| `update_purchase_order` | inventory | PUT | `/api/v2/purchase-orders/{purchaseOrderId}` | [Update a purchase order](https://www.holded.com/developers/api-reference/purchase-orders/update-a-purchase-order) |
| `update_purchase_shipment` | inventory | PUT | `/api/v2/purchase-shipments/{purchaseShipmentId}` | [Update a purchase shipment](https://www.holded.com/developers/api-reference/purchase-shipments/update-a-purchase-shipment) |
| `update_receipt_note` | sales | PUT | `/api/v2/receipt-notes/{receiptNoteId}` | [Update a receipt note](https://www.holded.com/developers/api-reference/receipt-notes/update-a-receipt-note) |
| `update_salary_record` | team | PUT | `/api/v2/salary-records/{salaryRecordId}` | [Update a salary record](https://www.holded.com/developers/api-reference/salary-records/update-a-salary-record) |
| `update_sales_channel` | sales | PUT | `/api/v2/sales-channels/{salesChannelId}` | [Update a sales channel](https://www.holded.com/developers/api-reference/sales-channels/update-a-sales-channel) |
| `update_sales_order` | inventory | PUT | `/api/v2/sales-orders/{salesOrderId}` | [Update a sales order](https://www.holded.com/developers/api-reference/sales-orders/update-a-sales-order) |
| `update_sales_order_tracking` | inventory | PUT | `/api/v2/sales-orders/{salesOrderId}/tracking` | [Update sales order tracking information](https://www.holded.com/developers/api-reference/sales-orders/update-sales-order-tracking-information) |
| `update_sales_receipt` | sales | PUT | `/api/v2/sales-receipts/{salesReceiptId}` | [Update a sales receipt](https://www.holded.com/developers/api-reference/sales-receipts/update-a-sales-receipt) |
| `update_service` | sales | PUT | `/api/v2/services/{serviceId}` | [Update a service](https://www.holded.com/developers/api-reference/services/update-a-service) |
| `update_task` | projects | PUT | `/api/v2/tasks/{taskId}` | [Update a task](https://www.holded.com/developers/api-reference/tasks/update-a-task) |
| `update_time_off` | team | PUT | `/api/v2/employees/{employeeId}/time-offs/{timeOffId}` | [Update time off end date (absence / holiday)](https://www.holded.com/developers/api-reference/time-off/update-time-off-end-date-absence-holiday) |
| `update_warehouse` | inventory | PATCH | `/api/v2/warehouses/{warehouseId}` | [Update a warehouse](https://www.holded.com/developers/api-reference/warehouses/update-a-warehouse) |
| `update_waybill` | inventory | PUT | `/api/v2/waybills/{waybillId}` | [Update a waybill](https://www.holded.com/developers/api-reference/waybills/update-a-waybill) |
| `update_waybill_tracking` | inventory | PUT | `/api/v2/waybills/{waybillId}/tracking` | [Update waybill tracking information](https://www.holded.com/developers/api-reference/waybills/update-waybill-tracking-information) |
| `update_webhook` | developers | PUT | `/api/v2/webhooks/{webhookId}` | [Update a webhook](https://www.holded.com/developers/api-reference/webhooks/update-a-webhook) |
| `upload_inbox` | inbox | POST | `/api/v2/inbox` | [Upload a document](https://www.holded.com/developers/api-reference/inbox/upload-a-document) |
| `upload_product_image` | inventory | POST | `/api/v2/products/{productId}/images` | [Upload a product image](https://www.holded.com/developers/api-reference/products/upload-a-product-image) |
