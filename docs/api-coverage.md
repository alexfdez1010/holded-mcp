# API coverage

Official API snapshot: **2026-10-14**.

The bundled catalog exposes **496 operations**: **360** from the current Holded **v2** API and **136** from the deprecated **v1** API. Both use the same API key (`HOLDED_API_KEY`).

| Version | API | Operations |
| --- | --- | ---: |
| v2 | accounting | 32 |
| v2 | treasury | 24 |
| v2 | sales | 104 |
| v2 | inventory | 78 |
| v2 | contacts | 20 |
| v2 | crm | 17 |
| v2 | projects | 17 |
| v2 | team | 37 |
| v2 | calendar | 12 |
| v2 | inbox | 9 |
| v2 | developers | 10 |
| **v2** | **total** | **360** |
| v1 | invoicing | 72 |
| v1 | crm | 29 |
| v1 | projects | 16 |
| v1 | team | 15 |
| v1 | accounting | 4 |
| **v1** | **total** | **136** |

## Sources

Copies of every source definition are committed under [`specs/`](../specs) (minified JSON, otherwise unchanged) so the catalog can be rebuilt offline.

### v2 (current)

Holded publishes v2 as one OpenAPI 3.1 document: [https://api.holded.com/openapi/api2.json](https://api.holded.com/openapi/api2.json) (`specs/v2/api2.json`). Paths are `/api/v2/...` and requests authenticate with `Authorization: Bearer <api key>`. Each operation declares the permission scope it needs (for example `sales:invoices.read`); the API key must have that scope. The reference is at [https://www.holded.com/developers/api-reference](https://www.holded.com/developers/api-reference).

### v1 (deprecated)

Holded labels v1 as deprecated/maintenance mode; it still works with the same key, sent in the `key` header. Holded published the v1 reference with ReadMe (developers.holded.com). Each v1 API is an OpenAPI 3.0 document in ReadMe's API registry; the original ReadMe reference pages (Internet Archive captures up to 2026) identify them as `@holded/v1.0#<id>` (`specs/v1/<api>.json`):

- invoicing: [https://dash.readme.com/api/v1/api-registry/delc6k4mltcvjvk](https://dash.readme.com/api/v1/api-registry/delc6k4mltcvjvk)
- crm: [https://dash.readme.com/api/v1/api-registry/3avojom3x2i4gl](https://dash.readme.com/api/v1/api-registry/3avojom3x2i4gl)
- projects: [https://dash.readme.com/api/v1/api-registry/osa1dlwrwhirf](https://dash.readme.com/api/v1/api-registry/osa1dlwrwhirf)
- team: [https://dash.readme.com/api/v1/api-registry/apza3e5ummfnu54er](https://dash.readme.com/api/v1/api-registry/apza3e5ummfnu54er)
- accounting: [https://dash.readme.com/api/v1/api-registry/168v3gl2suxrvj](https://dash.readme.com/api/v1/api-registry/168v3gl2suxrvj)

Holded now serves the v1 reference as an archive at [https://www.holded.com/developers/v1](https://www.holded.com/developers/v1); every v1 `doc_url` points there. At the first snapshot (2026-10-14) the archive listed exactly the same 136 method/path pairs, parameters, body fields, types and required flags as these definitions (the archive renders only top-level body fields; nested schemas come from the definitions).

Coverage means every HTTP operation in these definitions is callable. Holded plan limits, permissions, scopes and account features still apply. Response schemas are not bundled; responses are returned as received. Undocumented endpoints are not claimed as supported.

## Normalizations and limitations

### Both versions

- Every operation records its `version` (`v1` or `v2`) and `api`. Paths are full paths (`/api/v2/...` or `/api/<api>/v1/...`).
- Local `$ref`s are expanded (siblings retained). Recursive positions, if any appear in future definitions, are left unconstrained and marked with `x-holded-recursive-reference`.
- A schema declaring `properties` without `type` is normalized to `type: object`.
- Operation-level parameters override path-level parameters with the same name and location. Path parameters are always `required: true`. Parameters without a schema default to `type: string`; parameters without a description get an empty one. A parameter-level `example` moves into its schema.
- Authentication headers are excluded: the client adds `key` (v1) or `Authorization: Bearer` (v2) per request, never both. No v2 operation declares any other header, cookie or path-level parameter; the generator fails if one appears, because the transport only sends path and query parameters.
- `body_required` and `required` flags are kept from the source.
- File uploads use `multipart/form-data` with binary fields as `{"type": "string", "format": "binary"}`. OpenAPI 3.1 `contentMediaType` file fields (none at snapshot time) are normalized to the same form.

### v2

- Operation IDs are `v2_<operationId>` with the source `operationId` unchanged (for example `v2_list_invoices`).
- `api` is the slug of the operation's `x-tagGroups` group: `accounting`, `treasury`, `sales`, `inventory`, `contacts`, `crm`, `projects`, `team` (Team & HR), `calendar`, `inbox`, `developers`. `tags` keep the single source tag (for example `Invoices`).
- `doc_url` is `https://www.holded.com/developers/api-reference/<tag>/<summary>` (both slugified), the URL pattern of Holded's reference pages.
- OpenAPI 3.1 type arrays (`["string", "null"]`) and `null` enum members are kept; validation uses JSON Schema 2020-12.
- Holded's `x-ai-*` extensions (presentation and assistant hints such as `x-ai-presentation`, `x-ai-hidden`, `x-ai-grounded`, `x-ai-format`) are removed from parameter and body schemas. They are not input constraints.
- Source descriptions already start with `**Required permission:** <scope>`. Where they omit any scope from the operation's `security` requirement, the full list is appended as `Required permission scopes: ...` (for example, `v2_export_inbox` also needs `accounting:purchases.write`).
- Pagination follows each endpoint's declared parameters; none are added. At snapshot time, paginated list operations take `limit` and an opaque `cursor` returned by the previous response (with `has_more`). The document's general introduction also mentions `page`/`limit`, but no operation declares `page`.
- Multipart uploads (`v2_attach_contact_file`, `v2_attach_credit_note_file`, `v2_attach_estimate_file`, `v2_attach_invoice_file`, `v2_attach_proforma_file`, `v2_attach_purchase_file`, `v2_attach_purchase_order_file`, `v2_attach_receipt_note_file`, `v2_attach_sales_order_file`, `v2_attach_sales_receipt_file`, `v2_attach_waybill_file`, `v2_upload_inbox`, `v2_upload_product_image`) take one binary field (`file`, or `document` for `v2_upload_inbox`).

### v1

- Operation IDs are `v1_<api>_<Name>`, where `Name` is the source `operationId` (or `summary` when absent) converted to PascalCase (`List Contacts` -> `ListContacts`, `getDocument` -> `GetDocument`). Explicit overrides: `v1_accounting_ListAccounts` (GET `/chartofaccounts`), `v1_projects_GetProjectSummary` (GET `/projects/{projectId}/summary`), `v1_projects_GetProjectTime` (GET `/projects/{projectId}/times/{timeTrackingId}`), `v1_team_DeleteEmployee` (DELETE `/employees/{employeeId}`), `v1_team_GetEmployee` (GET `/employees/{employeeId}`), `v1_team_ListEmployeeTimes` (GET `/employees/{employeeId}/times`). They cover missing identifiers, a collision (`GetProjectTimes` is used for both the list and the single-entry operation in the source) and all-lowercase source names.
- `docType` path parameters carry an `enum`. Where the parameter's description lists its values (`should be one of: {...}`), that list is used (e.g. `{salesorder, waybill}` for tracking and pipeline updates, `{salesorder, order}` for shipped units). Where the source gives no description, the full list from the documents reference is applied: `invoice`, `salesreceipt`, `creditnote`, `salesorder`, `proform`, `waybill`, `estimate`, `purchase`, `purchaseorder`, `purchaserefund`.
- Query parameters whose description says `Options:` followed by backticked values get an `enum` (the documents `sort` parameter: `created-asc`, `created-desc`). Other value lists that the source describes only in prose (contact `type`, `taxOperation`, languages, carrier keys) are kept as descriptions, because the source does not present them as exhaustive.
- `v1_invoicing_AttachFile` uses `multipart/form-data` with `file` (binary) and an optional `setMain` boolean, as in the source.
- The v1 source marks no request body as required, even where a body is needed in practice.
- Timestamps (`starttmp`, `endtmp`, `date`, `dueDate`, ...) are Unix timestamps; the source does not state the unit, but its examples use seconds (10 digits). The source types some as strings and some as integers, and this catalog keeps the source types. Exceptions: tracking `pickUpDate`/`deliveryDate` use `DD/MM/YYYY` strings and the CRM slots `day` uses `yyyy-mm-dd`.
- `v1_invoicing_GetDocumentPDF` returns JSON `{"status": 1, "data": "<base64>"}` rather than a binary PDF (per the official response example).
- Pagination is only declared where the source declares it: a `page` query parameter on `v1_accounting_ListDailyLedger`, `v1_team_ListEmployees` and `v1_team_ListTimes` (pages of up to 500 items).

## Regenerate

Fetch the official definitions, refresh `specs/`, and rebuild:

```sh
uv sync --group dev
uv run python scripts/update_catalog.py --snapshot-date YYYY-MM-DD
```

Rebuild offline from the committed copies under `specs/`:

```sh
uv run python scripts/update_catalog.py --snapshot-date YYYY-MM-DD --from-specs
```

Individual local snapshots can also be passed with `--v2 api2.json` and `--invoicing`, `--crm`, `--projects`, `--team`, `--accounting`; they are copied into `specs/`. Add `--verify-docs` to fetch every reference page and check that it documents the same method and path. If Holded republishes a v1 definition under a new registry id, update `REGISTRY_IDS`; if it adds a v2 tag group, add it to `V2_TAG_GROUPS` in `scripts/update_catalog.py`. The generator rejects duplicate operation IDs, duplicate method/path pairs, unresolved references, missing or extra path parameters, unsupported parameter locations, unexpected servers and unsupported body content types before writing anything.

## Operations

### v2

| Operation ID | API | Method | Path | API reference |
| --- | --- | --- | --- | --- |
| `v2_accept_estimate` | sales | POST | `/api/v2/estimates/{estimateId}/accept` | [Accept an estimate](https://www.holded.com/developers/api-reference/estimates/accept-an-estimate) |
| `v2_approve_credit_note` | sales | POST | `/api/v2/credit-notes/{creditNoteId}/approve` | [Approve a credit note](https://www.holded.com/developers/api-reference/credit-notes/approve-a-credit-note) |
| `v2_approve_estimate` | sales | POST | `/api/v2/estimates/{estimateId}/approve` | [Approve an estimate](https://www.holded.com/developers/api-reference/estimates/approve-an-estimate) |
| `v2_approve_invoice` | sales | POST | `/api/v2/invoices/{invoiceId}/approve` | [Approve an invoice](https://www.holded.com/developers/api-reference/invoices/approve-an-invoice) |
| `v2_approve_payslip` | team | POST | `/api/v2/payslips/{payslipId}/approve` | [Approve a payslip](https://www.holded.com/developers/api-reference/payslips/approve-a-payslip) |
| `v2_approve_proforma` | sales | POST | `/api/v2/proformas/{proformaId}/approve` | [Approve a proforma](https://www.holded.com/developers/api-reference/proformas/approve-a-proforma) |
| `v2_approve_purchase` | accounting | POST | `/api/v2/purchases/{purchaseId}/approve` | [Approve a purchase](https://www.holded.com/developers/api-reference/purchases/approve-a-purchase) |
| `v2_approve_purchase_order` | inventory | POST | `/api/v2/purchase-orders/{purchaseOrderId}/approve` | [Approve a purchase order](https://www.holded.com/developers/api-reference/purchase-orders/approve-a-purchase-order) |
| `v2_approve_purchase_shipment` | inventory | POST | `/api/v2/purchase-shipments/{purchaseShipmentId}/approve` | [Approve a purchase shipment](https://www.holded.com/developers/api-reference/purchase-shipments/approve-a-purchase-shipment) |
| `v2_approve_receipt_note` | sales | POST | `/api/v2/receipt-notes/{receiptNoteId}/approve` | [Approve a receipt note](https://www.holded.com/developers/api-reference/receipt-notes/approve-a-receipt-note) |
| `v2_approve_sales_order` | inventory | POST | `/api/v2/sales-orders/{salesOrderId}/approve` | [Approve a sales order](https://www.holded.com/developers/api-reference/sales-orders/approve-a-sales-order) |
| `v2_approve_sales_receipt` | sales | POST | `/api/v2/sales-receipts/{salesReceiptId}/approve` | [Approve a sales receipt](https://www.holded.com/developers/api-reference/sales-receipts/approve-a-sales-receipt) |
| `v2_approve_waybill` | inventory | POST | `/api/v2/waybills/{waybillId}/approve` | [Approve a waybill](https://www.holded.com/developers/api-reference/waybills/approve-a-waybill) |
| `v2_archive_banking_account` | treasury | POST | `/api/v2/treasury/accounts/{id}/archive` | [Archive a banking account](https://www.holded.com/developers/api-reference/banking-accounts/archive-a-banking-account) |
| `v2_attach_contact_file` | contacts | POST | `/api/v2/contacts/{contactId}/attachments` | [Attach a file to a contact](https://www.holded.com/developers/api-reference/contact/attach-a-file-to-a-contact) |
| `v2_attach_credit_note_file` | sales | POST | `/api/v2/credit-notes/{creditNoteId}/attachments` | [Attach a file to a credit note](https://www.holded.com/developers/api-reference/credit-notes/attach-a-file-to-a-credit-note) |
| `v2_attach_estimate_file` | sales | POST | `/api/v2/estimates/{estimateId}/attachments` | [Attach a file to an estimate](https://www.holded.com/developers/api-reference/estimates/attach-a-file-to-an-estimate) |
| `v2_attach_inbox` | inbox | POST | `/api/v2/inbox/{incomingDocumentId}/attach` | [Attach incoming document to a document](https://www.holded.com/developers/api-reference/inbox/attach-incoming-document-to-a-document) |
| `v2_attach_invoice_file` | sales | POST | `/api/v2/invoices/{invoiceId}/attachments` | [Attach a file to an invoice](https://www.holded.com/developers/api-reference/invoices/attach-a-file-to-an-invoice) |
| `v2_attach_proforma_file` | sales | POST | `/api/v2/proformas/{proformaId}/attachments` | [Attach a file to a proforma](https://www.holded.com/developers/api-reference/proformas/attach-a-file-to-a-proforma) |
| `v2_attach_purchase_file` | accounting | POST | `/api/v2/purchases/{purchaseId}/attachments` | [Attach a file to a purchase](https://www.holded.com/developers/api-reference/purchases/attach-a-file-to-a-purchase) |
| `v2_attach_purchase_order_file` | inventory | POST | `/api/v2/purchase-orders/{purchaseOrderId}/attachments` | [Attach a file to a purchase order](https://www.holded.com/developers/api-reference/purchase-orders/attach-a-file-to-a-purchase-order) |
| `v2_attach_receipt_note_file` | sales | POST | `/api/v2/receipt-notes/{receiptNoteId}/attachments` | [Attach a file to a receipt note](https://www.holded.com/developers/api-reference/receipt-notes/attach-a-file-to-a-receipt-note) |
| `v2_attach_sales_order_file` | inventory | POST | `/api/v2/sales-orders/{salesOrderId}/attachments` | [Attach a file to a sales order](https://www.holded.com/developers/api-reference/sales-orders/attach-a-file-to-a-sales-order) |
| `v2_attach_sales_receipt_file` | sales | POST | `/api/v2/sales-receipts/{salesReceiptId}/attachments` | [Attach a file to a sales receipt](https://www.holded.com/developers/api-reference/sales-receipts/attach-a-file-to-a-sales-receipt) |
| `v2_attach_waybill_file` | inventory | POST | `/api/v2/waybills/{waybillId}/attachments` | [Attach a file to a waybill](https://www.holded.com/developers/api-reference/waybills/attach-a-file-to-a-waybill) |
| `v2_bulk_approve_invoices` | sales | POST | `/api/v2/invoices/bulk/approve` | [Bulk approve invoices](https://www.holded.com/developers/api-reference/invoices/bulk-approve-invoices) |
| `v2_bulk_archive_contacts` | contacts | POST | `/api/v2/contacts/bulk-archive` | [Bulk archive contacts](https://www.holded.com/developers/api-reference/contact/bulk-archive-contacts) |
| `v2_bulk_cancel_invoices` | sales | POST | `/api/v2/invoices/bulk/cancel` | [Bulk cancel invoices](https://www.holded.com/developers/api-reference/invoices/bulk-cancel-invoices) |
| `v2_bulk_delete_contacts` | contacts | POST | `/api/v2/contacts/bulk-delete` | [Bulk delete contacts](https://www.holded.com/developers/api-reference/contact/bulk-delete-contacts) |
| `v2_bulk_delete_invoices` | sales | DELETE | `/api/v2/invoices` | [Bulk delete invoices](https://www.holded.com/developers/api-reference/invoices/bulk-delete-invoices) |
| `v2_cancel_invoice` | sales | POST | `/api/v2/invoices/{invoiceId}/cancel` | [Cancel an invoice](https://www.holded.com/developers/api-reference/invoices/cancel-an-invoice) |
| `v2_clock_in` | team | POST | `/api/v2/employees/{employeeId}/clock-in` | [Clock in an employee](https://www.holded.com/developers/api-reference/employee-time-tracking/clock-in-an-employee) |
| `v2_clock_out` | team | POST | `/api/v2/employees/{employeeId}/clock-out` | [Clock out an employee](https://www.holded.com/developers/api-reference/employee-time-tracking/clock-out-an-employee) |
| `v2_convert_document` | inventory | POST | `/api/v2/documents/convert` | [Convert a document to another type](https://www.holded.com/developers/api-reference/documents/convert-a-document-to-another-type) |
| `v2_create_accounting_account` | accounting | POST | `/api/v2/accounting-accounts` | [Create an accounting account](https://www.holded.com/developers/api-reference/accounting/create-an-accounting-account) |
| `v2_create_bank_movement` | treasury | POST | `/api/v2/treasury/accounts/{bankingAccountId}/bank-movements` | [Create one or multiple manual bank movements](https://www.holded.com/developers/api-reference/banking-accounts/create-one-or-multiple-manual-bank-movements) |
| `v2_create_banking_account` | treasury | POST | `/api/v2/treasury/accounts` | [Create a banking account](https://www.holded.com/developers/api-reference/banking-accounts/create-a-banking-account) |
| `v2_create_booking` | calendar | POST | `/api/v2/bookings` | [Create a booking](https://www.holded.com/developers/api-reference/bookings/create-a-booking) |
| `v2_create_contact` | contacts | POST | `/api/v2/contacts` | [Create a contact](https://www.holded.com/developers/api-reference/contact/create-a-contact) |
| `v2_create_contact_group` | contacts | POST | `/api/v2/contact-groups` | [Create a contact group](https://www.holded.com/developers/api-reference/contact-group/create-a-contact-group) |
| `v2_create_credit_note` | sales | POST | `/api/v2/credit-notes` | [Create a credit note](https://www.holded.com/developers/api-reference/credit-notes/create-a-credit-note) |
| `v2_create_credit_note_payment` | sales | POST | `/api/v2/credit-notes/{creditNoteId}/payments` | [Create a payment for a credit note](https://www.holded.com/developers/api-reference/credit-notes/create-a-payment-for-a-credit-note) |
| `v2_create_employee` | team | POST | `/api/v2/employees` | [Create an employee](https://www.holded.com/developers/api-reference/employees/create-an-employee) |
| `v2_create_employee_time` | team | POST | `/api/v2/employees/{employeeId}/times` | [Create a time entry for an employee](https://www.holded.com/developers/api-reference/employee-time-tracking/create-a-time-entry-for-an-employee) |
| `v2_create_estimate` | sales | POST | `/api/v2/estimates` | [Create an estimate](https://www.holded.com/developers/api-reference/estimates/create-an-estimate) |
| `v2_create_event` | calendar | POST | `/api/v2/events` | [Create an event](https://www.holded.com/developers/api-reference/events/create-an-event) |
| `v2_create_expenses_account` | accounting | POST | `/api/v2/expenses-accounts` | [Create an expenses account](https://www.holded.com/developers/api-reference/expenses-accounts/create-an-expenses-account) |
| `v2_create_funnel` | crm | POST | `/api/v2/funnels` | [Create a funnel](https://www.holded.com/developers/api-reference/funnels/create-a-funnel) |
| `v2_create_invoice` | sales | POST | `/api/v2/invoices` | [Create an invoice](https://www.holded.com/developers/api-reference/invoices/create-an-invoice) |
| `v2_create_invoice_payment` | sales | POST | `/api/v2/invoices/{invoiceId}/payments` | [Create a payment for an invoice](https://www.holded.com/developers/api-reference/invoices/create-a-payment-for-an-invoice) |
| `v2_create_invoice_recurring` | sales | POST | `/api/v2/recurring-invoices` | [Create a recurring invoice](https://www.holded.com/developers/api-reference/recurring-invoices/create-a-recurring-invoice) |
| `v2_create_invoicing_forecast` | treasury | POST | `/api/v2/treasury/cashflow/invoicing-forecasts` | [Create an invoicing forecast](https://www.holded.com/developers/api-reference/invoicing-forecast/create-an-invoicing-forecast) |
| `v2_create_lead` | crm | POST | `/api/v2/leads` | [Create a lead](https://www.holded.com/developers/api-reference/leads/create-a-lead) |
| `v2_create_lead_note` | crm | POST | `/api/v2/leads/{leadId}/notes` | [Create a lead note](https://www.holded.com/developers/api-reference/leads/create-a-lead-note) |
| `v2_create_lead_task` | crm | POST | `/api/v2/leads/{leadId}/tasks` | [Create a lead task](https://www.holded.com/developers/api-reference/leads/create-a-lead-task) |
| `v2_create_ledger_entry` | accounting | POST | `/api/v2/ledger-entries` | [Create a ledger entry](https://www.holded.com/developers/api-reference/accounting/create-a-ledger-entry) |
| `v2_create_numbering_series` | sales | POST | `/api/v2/numbering-series/{type}` | [Create a numbering series](https://www.holded.com/developers/api-reference/numbering-series/create-a-numbering-series) |
| `v2_create_payment` | accounting | POST | `/api/v2/payments` | [Create a payment](https://www.holded.com/developers/api-reference/payment/create-a-payment) |
| `v2_create_payment_method` | treasury | POST | `/api/v2/payment-methods` | [Create a payment method](https://www.holded.com/developers/api-reference/payment-methods/create-a-payment-method) |
| `v2_create_payslip` | team | POST | `/api/v2/payslips` | [Create payslips in bulk](https://www.holded.com/developers/api-reference/payslips/create-payslips-in-bulk) |
| `v2_create_payslip_payment` | team | POST | `/api/v2/payslips/{payslipId}/payments` | [Create a payment for a payslip](https://www.holded.com/developers/api-reference/payslips/create-a-payment-for-a-payslip) |
| `v2_create_price_list` | inventory | POST | `/api/v2/price-lists` | [Create a price list](https://www.holded.com/developers/api-reference/price-lists/create-a-price-list) |
| `v2_create_product` | inventory | POST | `/api/v2/products` | [Create a product](https://www.holded.com/developers/api-reference/products/create-a-product) |
| `v2_create_production_order` | inventory | POST | `/api/v2/production-orders` | [Create a production order](https://www.holded.com/developers/api-reference/production-orders/create-a-production-order) |
| `v2_create_proforma` | sales | POST | `/api/v2/proformas` | [Create a proforma](https://www.holded.com/developers/api-reference/proformas/create-a-proforma) |
| `v2_create_project` | projects | POST | `/api/v2/projects` | [Create a project](https://www.holded.com/developers/api-reference/projects/create-a-project) |
| `v2_create_project_time` | projects | POST | `/api/v2/projects/{projectId}/times` | [Create a time entry for a project](https://www.holded.com/developers/api-reference/project-time-tracking/create-a-time-entry-for-a-project) |
| `v2_create_purchase` | accounting | POST | `/api/v2/purchases` | [Create a purchase](https://www.holded.com/developers/api-reference/purchases/create-a-purchase) |
| `v2_create_purchase_order` | inventory | POST | `/api/v2/purchase-orders` | [Create a purchase order](https://www.holded.com/developers/api-reference/purchase-orders/create-a-purchase-order) |
| `v2_create_purchase_payment` | accounting | POST | `/api/v2/purchases/{purchaseId}/payments` | [Create a payment for a purchase](https://www.holded.com/developers/api-reference/purchases/create-a-payment-for-a-purchase) |
| `v2_create_purchase_refund` | accounting | POST | `/api/v2/purchases/refund` | [Create a purchase refund](https://www.holded.com/developers/api-reference/purchases/create-a-purchase-refund) |
| `v2_create_purchase_shipment` | inventory | POST | `/api/v2/purchase-shipments` | [Create a purchase shipment](https://www.holded.com/developers/api-reference/purchase-shipments/create-a-purchase-shipment) |
| `v2_create_receipt_note` | sales | POST | `/api/v2/receipt-notes` | [Create a receipt note](https://www.holded.com/developers/api-reference/receipt-notes/create-a-receipt-note) |
| `v2_create_receipt_note_payment` | sales | POST | `/api/v2/receipt-notes/{receiptNoteId}/payments` | [Create a payment for a receipt note](https://www.holded.com/developers/api-reference/receipt-notes/create-a-payment-for-a-receipt-note) |
| `v2_create_salary_record` | team | POST | `/api/v2/salary-records` | [Create a salary record](https://www.holded.com/developers/api-reference/salary-records/create-a-salary-record) |
| `v2_create_sales_channel` | sales | POST | `/api/v2/sales-channels` | [Create a sales channel](https://www.holded.com/developers/api-reference/sales-channels/create-a-sales-channel) |
| `v2_create_sales_order` | inventory | POST | `/api/v2/sales-orders` | [Create a sales order](https://www.holded.com/developers/api-reference/sales-orders/create-a-sales-order) |
| `v2_create_sales_receipt` | sales | POST | `/api/v2/sales-receipts` | [Create a sales receipt](https://www.holded.com/developers/api-reference/sales-receipts/create-a-sales-receipt) |
| `v2_create_sales_receipt_payment` | sales | POST | `/api/v2/sales-receipts/{salesReceiptId}/payments` | [Create a payment for a sales receipt](https://www.holded.com/developers/api-reference/sales-receipts/create-a-payment-for-a-sales-receipt) |
| `v2_create_service` | sales | POST | `/api/v2/services` | [Create a service](https://www.holded.com/developers/api-reference/services/create-a-service) |
| `v2_create_tag` | contacts | POST | `/api/v2/tags` | [Create a tag](https://www.holded.com/developers/api-reference/tags/create-a-tag) |
| `v2_create_task` | projects | POST | `/api/v2/tasks` | [Create a task](https://www.holded.com/developers/api-reference/tasks/create-a-task) |
| `v2_create_time_off` | team | POST | `/api/v2/employees/{employeeId}/time-offs` | [Create a time off request (absence / holiday)](https://www.holded.com/developers/api-reference/time-off/create-a-time-off-request-absence-holiday) |
| `v2_create_warehouse` | inventory | POST | `/api/v2/warehouses` | [Create a warehouse](https://www.holded.com/developers/api-reference/warehouses/create-a-warehouse) |
| `v2_create_waybill` | inventory | POST | `/api/v2/waybills` | [Create a waybill](https://www.holded.com/developers/api-reference/waybills/create-a-waybill) |
| `v2_create_webhook` | developers | POST | `/api/v2/webhooks` | [Create a webhook](https://www.holded.com/developers/api-reference/webhooks/create-a-webhook) |
| `v2_delete_banking_account` | treasury | DELETE | `/api/v2/treasury/accounts/{id}` | [Delete a banking account](https://www.holded.com/developers/api-reference/banking-accounts/delete-a-banking-account) |
| `v2_delete_booking` | calendar | DELETE | `/api/v2/bookings/{bookingId}` | [Cancel a booking](https://www.holded.com/developers/api-reference/bookings/cancel-a-booking) |
| `v2_delete_contact` | contacts | DELETE | `/api/v2/contacts/{contactId}` | [Delete a contact](https://www.holded.com/developers/api-reference/contact/delete-a-contact) |
| `v2_delete_contact_group` | contacts | DELETE | `/api/v2/contact-groups/{contactGroupId}` | [Delete a contact group](https://www.holded.com/developers/api-reference/contact-group/delete-a-contact-group) |
| `v2_delete_credit_note` | sales | DELETE | `/api/v2/credit-notes/{creditNoteId}` | [Delete a credit note](https://www.holded.com/developers/api-reference/credit-notes/delete-a-credit-note) |
| `v2_delete_employee` | team | DELETE | `/api/v2/employees/{employeeId}` | [Delete an employee](https://www.holded.com/developers/api-reference/employees/delete-an-employee) |
| `v2_delete_employee_time` | team | DELETE | `/api/v2/employee-times/{timeId}` | [Delete an employee time entry](https://www.holded.com/developers/api-reference/employee-time-tracking/delete-an-employee-time-entry) |
| `v2_delete_estimate` | sales | DELETE | `/api/v2/estimates/{estimateId}` | [Delete an estimate](https://www.holded.com/developers/api-reference/estimates/delete-an-estimate) |
| `v2_delete_event` | calendar | DELETE | `/api/v2/events/{eventId}` | [Delete an event](https://www.holded.com/developers/api-reference/events/delete-an-event) |
| `v2_delete_expenses_account` | accounting | DELETE | `/api/v2/expenses-accounts/{expensesAccountId}` | [Delete an expenses account](https://www.holded.com/developers/api-reference/expenses-accounts/delete-an-expenses-account) |
| `v2_delete_funnel` | crm | DELETE | `/api/v2/funnels/{funnelId}` | [Delete a funnel](https://www.holded.com/developers/api-reference/funnels/delete-a-funnel) |
| `v2_delete_inbox` | inbox | DELETE | `/api/v2/inbox/{incomingDocumentId}` | [Delete an incoming document](https://www.holded.com/developers/api-reference/inbox/delete-an-incoming-document) |
| `v2_delete_invoice` | sales | DELETE | `/api/v2/invoices/{invoiceId}` | [Delete an invoice](https://www.holded.com/developers/api-reference/invoices/delete-an-invoice) |
| `v2_delete_invoice_recurring` | sales | DELETE | `/api/v2/recurring-invoices/{invoiceRecurringId}` | [Delete a recurring invoice](https://www.holded.com/developers/api-reference/recurring-invoices/delete-a-recurring-invoice) |
| `v2_delete_invoicing_forecast` | treasury | DELETE | `/api/v2/treasury/cashflow/invoicing-forecasts/{forecastId}` | [Delete an invoicing forecast](https://www.holded.com/developers/api-reference/invoicing-forecast/delete-an-invoicing-forecast) |
| `v2_delete_lead` | crm | DELETE | `/api/v2/leads/{leadId}` | [Delete a lead](https://www.holded.com/developers/api-reference/leads/delete-a-lead) |
| `v2_delete_lead_task` | crm | DELETE | `/api/v2/leads/{leadId}/tasks` | [Delete a lead task](https://www.holded.com/developers/api-reference/leads/delete-a-lead-task) |
| `v2_delete_ledger_entry` | accounting | DELETE | `/api/v2/ledger-entries/{ledgerEntryId}` | [Delete a ledger entry](https://www.holded.com/developers/api-reference/accounting/delete-a-ledger-entry) |
| `v2_delete_numbering_series` | sales | DELETE | `/api/v2/numbering-series/{type}/{numberingSeriesId}` | [Delete a numbering series](https://www.holded.com/developers/api-reference/numbering-series/delete-a-numbering-series) |
| `v2_delete_payment` | accounting | DELETE | `/api/v2/payments/{paymentId}` | [Delete a payment](https://www.holded.com/developers/api-reference/payment/delete-a-payment) |
| `v2_delete_payment_method` | treasury | DELETE | `/api/v2/payment-methods/{paymentMethodId}` | [Delete a payment method](https://www.holded.com/developers/api-reference/payment-methods/delete-a-payment-method) |
| `v2_delete_payslip` | team | DELETE | `/api/v2/payslips/{payslipId}` | [Delete a payslip](https://www.holded.com/developers/api-reference/payslips/delete-a-payslip) |
| `v2_delete_payslip_payment` | team | DELETE | `/api/v2/payslips/{payslipId}/payments/{paymentId}` | [Delete a payment from a payslip](https://www.holded.com/developers/api-reference/payslips/delete-a-payment-from-a-payslip) |
| `v2_delete_price_list` | inventory | DELETE | `/api/v2/price-lists/{priceListId}` | [Delete a price list](https://www.holded.com/developers/api-reference/price-lists/delete-a-price-list) |
| `v2_delete_product` | inventory | DELETE | `/api/v2/products/{productId}` | [Delete a product](https://www.holded.com/developers/api-reference/products/delete-a-product) |
| `v2_delete_production_order` | inventory | DELETE | `/api/v2/production-orders/{productionOrderId}` | [Delete a production order](https://www.holded.com/developers/api-reference/production-orders/delete-a-production-order) |
| `v2_delete_proforma` | sales | DELETE | `/api/v2/proformas/{proformaId}` | [Delete a proforma](https://www.holded.com/developers/api-reference/proformas/delete-a-proforma) |
| `v2_delete_project` | projects | DELETE | `/api/v2/projects/{projectId}` | [Delete a project](https://www.holded.com/developers/api-reference/projects/delete-a-project) |
| `v2_delete_project_time` | projects | DELETE | `/api/v2/projects/{projectId}/times/{timeId}` | [Delete a project time entry](https://www.holded.com/developers/api-reference/project-time-tracking/delete-a-project-time-entry) |
| `v2_delete_purchase` | accounting | DELETE | `/api/v2/purchases/{purchaseId}` | [Delete a purchase](https://www.holded.com/developers/api-reference/purchases/delete-a-purchase) |
| `v2_delete_purchase_order` | inventory | DELETE | `/api/v2/purchase-orders/{purchaseOrderId}` | [Delete a purchase order](https://www.holded.com/developers/api-reference/purchase-orders/delete-a-purchase-order) |
| `v2_delete_purchase_shipment` | inventory | DELETE | `/api/v2/purchase-shipments/{purchaseShipmentId}` | [Delete a purchase shipment](https://www.holded.com/developers/api-reference/purchase-shipments/delete-a-purchase-shipment) |
| `v2_delete_receipt_note` | sales | DELETE | `/api/v2/receipt-notes/{receiptNoteId}` | [Delete a receipt note](https://www.holded.com/developers/api-reference/receipt-notes/delete-a-receipt-note) |
| `v2_delete_salary_record` | team | DELETE | `/api/v2/salary-records/{salaryRecordId}` | [Delete a salary record](https://www.holded.com/developers/api-reference/salary-records/delete-a-salary-record) |
| `v2_delete_sales_channel` | sales | DELETE | `/api/v2/sales-channels/{salesChannelId}` | [Delete a sales channel](https://www.holded.com/developers/api-reference/sales-channels/delete-a-sales-channel) |
| `v2_delete_sales_order` | inventory | DELETE | `/api/v2/sales-orders/{salesOrderId}` | [Delete a sales order](https://www.holded.com/developers/api-reference/sales-orders/delete-a-sales-order) |
| `v2_delete_sales_receipt` | sales | DELETE | `/api/v2/sales-receipts/{salesReceiptId}` | [Delete a sales receipt](https://www.holded.com/developers/api-reference/sales-receipts/delete-a-sales-receipt) |
| `v2_delete_service` | sales | DELETE | `/api/v2/services/{serviceId}` | [Delete a service](https://www.holded.com/developers/api-reference/services/delete-a-service) |
| `v2_delete_tag` | contacts | DELETE | `/api/v2/tags/{tag}` | [Delete a tag](https://www.holded.com/developers/api-reference/tags/delete-a-tag) |
| `v2_delete_task` | projects | DELETE | `/api/v2/tasks/{taskId}` | [Delete a task](https://www.holded.com/developers/api-reference/tasks/delete-a-task) |
| `v2_delete_warehouse` | inventory | DELETE | `/api/v2/warehouses/{warehouseId}` | [Delete a warehouse](https://www.holded.com/developers/api-reference/warehouses/delete-a-warehouse) |
| `v2_delete_waybill` | inventory | DELETE | `/api/v2/waybills/{waybillId}` | [Delete a waybill](https://www.holded.com/developers/api-reference/waybills/delete-a-waybill) |
| `v2_delete_webhook` | developers | DELETE | `/api/v2/webhooks/{webhookId}` | [Delete a webhook](https://www.holded.com/developers/api-reference/webhooks/delete-a-webhook) |
| `v2_disable_webhook` | developers | POST | `/api/v2/webhooks/{webhookId}/disable` | [Disable a webhook](https://www.holded.com/developers/api-reference/webhooks/disable-a-webhook) |
| `v2_download_inbox_file` | inbox | GET | `/api/v2/inbox/{incomingDocumentId}/files/{filename}/download` | [Download a file from an inbox document](https://www.holded.com/developers/api-reference/inbox/download-a-file-from-an-inbox-document) |
| `v2_edit_invoicing_forecast` | treasury | PUT | `/api/v2/treasury/cashflow/invoicing-forecasts/{forecastId}` | [Edit an invoicing forecast](https://www.holded.com/developers/api-reference/invoicing-forecast/edit-an-invoicing-forecast) |
| `v2_enable_webhook` | developers | POST | `/api/v2/webhooks/{webhookId}/enable` | [Enable a webhook](https://www.holded.com/developers/api-reference/webhooks/enable-a-webhook) |
| `v2_export_inbox` | inbox | POST | `/api/v2/inbox/{incomingDocumentId}/export` | [Convert incoming document into a purchase document](https://www.holded.com/developers/api-reference/inbox/convert-incoming-document-into-a-purchase-document) |
| `v2_find_invoices_by_document_number` | sales | GET | `/api/v2/invoices/find-by-number` | [Find invoices by document number](https://www.holded.com/developers/api-reference/invoices/find-invoices-by-document-number) |
| `v2_get_banking_account` | treasury | GET | `/api/v2/treasury/accounts/{id}` | [Get a banking account by ID](https://www.holded.com/developers/api-reference/banking-accounts/get-a-banking-account-by-id) |
| `v2_get_booking` | calendar | GET | `/api/v2/bookings/{bookingId}` | [Get a booking by ID](https://www.holded.com/developers/api-reference/bookings/get-a-booking-by-id) |
| `v2_get_booking_location_slots` | calendar | GET | `/api/v2/booking-locations/{locationId}/slots` | [Get available slots for a location](https://www.holded.com/developers/api-reference/bookings/get-available-slots-for-a-location) |
| `v2_get_contact` | contacts | GET | `/api/v2/contacts/{contactId}` | [Get a contact by ID](https://www.holded.com/developers/api-reference/contact/get-a-contact-by-id) |
| `v2_get_contact_attachment` | contacts | GET | `/api/v2/contacts/{contactId}/attachments/{filename}` | [Get a contact attachment](https://www.holded.com/developers/api-reference/contact/get-a-contact-attachment) |
| `v2_get_contact_group` | contacts | GET | `/api/v2/contact-groups/{contactGroupId}` | [Get a contact group](https://www.holded.com/developers/api-reference/contact-group/get-a-contact-group) |
| `v2_get_contact_portal_link` | contacts | GET | `/api/v2/contacts/{contactId}/portal-link` | [Get client portal link for a contact](https://www.holded.com/developers/api-reference/contact/get-client-portal-link-for-a-contact) |
| `v2_get_credit_note` | sales | GET | `/api/v2/credit-notes/{creditNoteId}` | [Get a credit note](https://www.holded.com/developers/api-reference/credit-notes/get-a-credit-note) |
| `v2_get_credit_note_attachment` | sales | GET | `/api/v2/credit-notes/{creditNoteId}/attachments/{attachmentId}` | [Get credit note attachment](https://www.holded.com/developers/api-reference/credit-notes/get-credit-note-attachment) |
| `v2_get_credit_note_pdf` | sales | GET | `/api/v2/credit-notes/{creditNoteId}/pdf` | [Get credit note PDF](https://www.holded.com/developers/api-reference/credit-notes/get-credit-note-pdf) |
| `v2_get_employee` | team | GET | `/api/v2/employees/{employeeId}` | [Get an employee](https://www.holded.com/developers/api-reference/employees/get-an-employee) |
| `v2_get_employee_contract` | team | GET | `/api/v2/employees/{employeeId}/contract` | [Get active contract](https://www.holded.com/developers/api-reference/employees/get-active-contract) |
| `v2_get_employee_time` | team | GET | `/api/v2/employee-times/{timeId}` | [Get an employee time entry](https://www.holded.com/developers/api-reference/employee-time-tracking/get-an-employee-time-entry) |
| `v2_get_estimate` | sales | GET | `/api/v2/estimates/{estimateId}` | [Get an estimate](https://www.holded.com/developers/api-reference/estimates/get-an-estimate) |
| `v2_get_estimate_attachment` | sales | GET | `/api/v2/estimates/{estimateId}/attachments/{attachmentId}` | [Get estimate attachment](https://www.holded.com/developers/api-reference/estimates/get-estimate-attachment) |
| `v2_get_estimate_pdf` | sales | GET | `/api/v2/estimates/{estimateId}/pdf` | [Get estimate PDF](https://www.holded.com/developers/api-reference/estimates/get-estimate-pdf) |
| `v2_get_event` | calendar | GET | `/api/v2/events/{eventId}` | [Get an event by ID](https://www.holded.com/developers/api-reference/events/get-an-event-by-id) |
| `v2_get_expenses_account` | accounting | GET | `/api/v2/expenses-accounts/{expensesAccountId}` | [Get an expenses account by ID](https://www.holded.com/developers/api-reference/expenses-accounts/get-an-expenses-account-by-id) |
| `v2_get_funnel` | crm | GET | `/api/v2/funnels/{funnelId}` | [Get a funnel](https://www.holded.com/developers/api-reference/funnels/get-a-funnel) |
| `v2_get_inbox` | inbox | GET | `/api/v2/inbox/{incomingDocumentId}` | [Get an incoming document by ID](https://www.holded.com/developers/api-reference/inbox/get-an-incoming-document-by-id) |
| `v2_get_invoice` | sales | GET | `/api/v2/invoices/{invoiceId}` | [Get an invoice](https://www.holded.com/developers/api-reference/invoices/get-an-invoice) |
| `v2_get_invoice_attachment` | sales | GET | `/api/v2/invoices/{invoiceId}/attachments/{attachmentId}` | [Get invoice attachment](https://www.holded.com/developers/api-reference/invoices/get-invoice-attachment) |
| `v2_get_invoice_pdf` | sales | GET | `/api/v2/invoices/{invoiceId}/pdf` | [Get invoice PDF](https://www.holded.com/developers/api-reference/invoices/get-invoice-pdf) |
| `v2_get_invoice_recurring` | sales | GET | `/api/v2/recurring-invoices/{invoiceRecurringId}` | [Get a recurring invoice](https://www.holded.com/developers/api-reference/recurring-invoices/get-a-recurring-invoice) |
| `v2_get_invoicing_forecast` | treasury | GET | `/api/v2/treasury/cashflow/invoicing-forecasts/{forecastId}` | [Get an invoicing forecast](https://www.holded.com/developers/api-reference/invoicing-forecast/get-an-invoicing-forecast) |
| `v2_get_lead` | crm | GET | `/api/v2/leads/{leadId}` | [Get a lead](https://www.holded.com/developers/api-reference/leads/get-a-lead) |
| `v2_get_ledger_entry` | accounting | GET | `/api/v2/ledger-entries/{ledgerEntryId}` | [Get a ledger entry](https://www.holded.com/developers/api-reference/accounting/get-a-ledger-entry) |
| `v2_get_payment` | accounting | GET | `/api/v2/payments/{paymentId}` | [Get a payment by ID](https://www.holded.com/developers/api-reference/payment/get-a-payment-by-id) |
| `v2_get_payment_method` | treasury | GET | `/api/v2/payment-methods/{paymentMethodId}` | [Get a payment method by ID](https://www.holded.com/developers/api-reference/payment-methods/get-a-payment-method-by-id) |
| `v2_get_payslip` | team | GET | `/api/v2/payslips/{payslipId}` | [Get a payslip](https://www.holded.com/developers/api-reference/payslips/get-a-payslip) |
| `v2_get_payslip_pdf` | team | GET | `/api/v2/payslips/{payslipId}/pdf` | [Download a payslip PDF](https://www.holded.com/developers/api-reference/payslips/download-a-payslip-pdf) |
| `v2_get_price_list` | inventory | GET | `/api/v2/price-lists/{priceListId}` | [Get a price list by ID](https://www.holded.com/developers/api-reference/price-lists/get-a-price-list-by-id) |
| `v2_get_product` | inventory | GET | `/api/v2/products/{productId}` | [Get a product by ID](https://www.holded.com/developers/api-reference/products/get-a-product-by-id) |
| `v2_get_product_image` | inventory | GET | `/api/v2/products/{productId}/images/{imageId}` | [Get a product image by ID](https://www.holded.com/developers/api-reference/products/get-a-product-image-by-id) |
| `v2_get_product_main_image` | inventory | GET | `/api/v2/products/{productId}/image` | [Get the main product image](https://www.holded.com/developers/api-reference/products/get-the-main-product-image) |
| `v2_get_product_stock` | inventory | GET | `/api/v2/products/{productId}/stock` | [Get stock availability for a product](https://www.holded.com/developers/api-reference/products/get-stock-availability-for-a-product) |
| `v2_get_product_stock_transit` | inventory | GET | `/api/v2/products/{productId}/stock/transit` | [Get stock in transit for a product](https://www.holded.com/developers/api-reference/products/get-stock-in-transit-for-a-product) |
| `v2_get_production_order` | inventory | GET | `/api/v2/production-orders/{productionOrderId}` | [Get a production order](https://www.holded.com/developers/api-reference/production-orders/get-a-production-order) |
| `v2_get_proforma` | sales | GET | `/api/v2/proformas/{proformaId}` | [Get a proforma](https://www.holded.com/developers/api-reference/proformas/get-a-proforma) |
| `v2_get_proforma_attachment` | sales | GET | `/api/v2/proformas/{proformaId}/attachments/{attachmentId}` | [Get proforma attachment](https://www.holded.com/developers/api-reference/proformas/get-proforma-attachment) |
| `v2_get_proforma_pdf` | sales | GET | `/api/v2/proformas/{proformaId}/pdf` | [Get proforma PDF](https://www.holded.com/developers/api-reference/proformas/get-proforma-pdf) |
| `v2_get_project` | projects | GET | `/api/v2/projects/{projectId}` | [Get a project](https://www.holded.com/developers/api-reference/projects/get-a-project) |
| `v2_get_project_summary` | projects | GET | `/api/v2/projects/{projectId}/summary` | [Get a project summary](https://www.holded.com/developers/api-reference/projects/get-a-project-summary) |
| `v2_get_project_time` | projects | GET | `/api/v2/projects/{projectId}/times/{timeId}` | [Get a project time entry](https://www.holded.com/developers/api-reference/project-time-tracking/get-a-project-time-entry) |
| `v2_get_purchase` | accounting | GET | `/api/v2/purchases/{purchaseId}` | [Get a purchase](https://www.holded.com/developers/api-reference/purchases/get-a-purchase) |
| `v2_get_purchase_attachment` | accounting | GET | `/api/v2/purchases/{purchaseId}/attachments/{attachmentId}` | [Get purchase attachment](https://www.holded.com/developers/api-reference/purchases/get-purchase-attachment) |
| `v2_get_purchase_order` | inventory | GET | `/api/v2/purchase-orders/{purchaseOrderId}` | [Get a purchase order](https://www.holded.com/developers/api-reference/purchase-orders/get-a-purchase-order) |
| `v2_get_purchase_order_attachment` | inventory | GET | `/api/v2/purchase-orders/{purchaseOrderId}/attachments/{attachmentId}` | [Get purchase order attachment](https://www.holded.com/developers/api-reference/purchase-orders/get-purchase-order-attachment) |
| `v2_get_purchase_order_pdf` | inventory | GET | `/api/v2/purchase-orders/{purchaseOrderId}/pdf` | [Get purchase order PDF](https://www.holded.com/developers/api-reference/purchase-orders/get-purchase-order-pdf) |
| `v2_get_purchase_order_received_items` | inventory | GET | `/api/v2/purchase-orders/{purchaseOrderId}/received-items` | [Get received items for a purchase order](https://www.holded.com/developers/api-reference/purchase-orders/get-received-items-for-a-purchase-order) |
| `v2_get_purchase_refund` | accounting | GET | `/api/v2/purchases/refund/{purchaseRefundId}` | [Get a purchase refund](https://www.holded.com/developers/api-reference/purchases/get-a-purchase-refund) |
| `v2_get_purchase_shipment` | inventory | GET | `/api/v2/purchase-shipments/{purchaseShipmentId}` | [Get a purchase shipment](https://www.holded.com/developers/api-reference/purchase-shipments/get-a-purchase-shipment) |
| `v2_get_receipt_note` | sales | GET | `/api/v2/receipt-notes/{receiptNoteId}` | [Get a receipt note](https://www.holded.com/developers/api-reference/receipt-notes/get-a-receipt-note) |
| `v2_get_receipt_note_attachment` | sales | GET | `/api/v2/receipt-notes/{receiptNoteId}/attachments/{attachmentId}` | [Get receipt note attachment](https://www.holded.com/developers/api-reference/receipt-notes/get-receipt-note-attachment) |
| `v2_get_receipt_note_pdf` | sales | GET | `/api/v2/receipt-notes/{receiptNoteId}/pdf` | [Get receipt note PDF](https://www.holded.com/developers/api-reference/receipt-notes/get-receipt-note-pdf) |
| `v2_get_recurring_schedule` | sales | GET | `/api/v2/recurring-invoices/{invoiceRecurringId}/schedule` | [Get recurring invoice schedule](https://www.holded.com/developers/api-reference/recurring-invoices/get-recurring-invoice-schedule) |
| `v2_get_remittance` | treasury | GET | `/api/v2/treasury/remittances/{remittanceId}` | [Get a remittance](https://www.holded.com/developers/api-reference/remittances/get-a-remittance) |
| `v2_get_salary_record` | team | GET | `/api/v2/salary-records/{salaryRecordId}` | [Get a salary record](https://www.holded.com/developers/api-reference/salary-records/get-a-salary-record) |
| `v2_get_salary_record_form_data` | team | GET | `/api/v2/salary-records/form-data` | [Get salary record form data](https://www.holded.com/developers/api-reference/salary-records/get-salary-record-form-data) |
| `v2_get_salary_record_pdf` | team | GET | `/api/v2/salary-records/{salaryRecordId}/pdf` | [Download a salary record PDF](https://www.holded.com/developers/api-reference/salary-records/download-a-salary-record-pdf) |
| `v2_get_sales_channel` | sales | GET | `/api/v2/sales-channels/{salesChannelId}` | [Get a sales channel by ID](https://www.holded.com/developers/api-reference/sales-channels/get-a-sales-channel-by-id) |
| `v2_get_sales_order` | inventory | GET | `/api/v2/sales-orders/{salesOrderId}` | [Get a sales order](https://www.holded.com/developers/api-reference/sales-orders/get-a-sales-order) |
| `v2_get_sales_order_attachment` | inventory | GET | `/api/v2/sales-orders/{salesOrderId}/attachments/{attachmentId}` | [Get sales order attachment](https://www.holded.com/developers/api-reference/sales-orders/get-sales-order-attachment) |
| `v2_get_sales_order_pdf` | inventory | GET | `/api/v2/sales-orders/{salesOrderId}/pdf` | [Get sales order PDF](https://www.holded.com/developers/api-reference/sales-orders/get-sales-order-pdf) |
| `v2_get_sales_order_shipped_items` | inventory | GET | `/api/v2/sales-orders/{salesOrderId}/shipped-items` | [Get shipped items for a sales order](https://www.holded.com/developers/api-reference/sales-orders/get-shipped-items-for-a-sales-order) |
| `v2_get_sales_receipt` | sales | GET | `/api/v2/sales-receipts/{salesReceiptId}` | [Get a sales receipt](https://www.holded.com/developers/api-reference/sales-receipts/get-a-sales-receipt) |
| `v2_get_sales_receipt_attachment` | sales | GET | `/api/v2/sales-receipts/{salesReceiptId}/attachments/{attachmentId}` | [Get sales receipt attachment](https://www.holded.com/developers/api-reference/sales-receipts/get-sales-receipt-attachment) |
| `v2_get_sales_receipt_pdf` | sales | GET | `/api/v2/sales-receipts/{salesReceiptId}/pdf` | [Get sales receipt PDF](https://www.holded.com/developers/api-reference/sales-receipts/get-sales-receipt-pdf) |
| `v2_get_service` | sales | GET | `/api/v2/services/{serviceId}` | [Get a service](https://www.holded.com/developers/api-reference/services/get-a-service) |
| `v2_get_task` | projects | GET | `/api/v2/tasks/{taskId}` | [Get a task](https://www.holded.com/developers/api-reference/tasks/get-a-task) |
| `v2_get_tax_per_country_sorted_keys` | accounting | GET | `/api/v2/taxes/keys-by-country` | [Get sorted tax keys by country and section](https://www.holded.com/developers/api-reference/tax/get-sorted-tax-keys-by-country-and-section) |
| `v2_get_time_off` | team | GET | `/api/v2/employees/{employeeId}/time-offs/{timeOffId}` | [Get a time off request (absence / holiday)](https://www.holded.com/developers/api-reference/time-off/get-a-time-off-request-absence-holiday) |
| `v2_get_usage` | developers | GET | `/api/v2/usage` | [Get API usage (automation token)](https://www.holded.com/developers/api-reference/developers/get-api-usage-automation-token) |
| `v2_get_usage_by_type` | developers | GET | `/api/v2/usage/{type}` | [Get API usage by type](https://www.holded.com/developers/api-reference/developers/get-api-usage-by-type) |
| `v2_get_warehouse` | inventory | GET | `/api/v2/warehouses/{warehouseId}` | [Get a warehouse by ID](https://www.holded.com/developers/api-reference/warehouses/get-a-warehouse-by-id) |
| `v2_get_warehouse_stock` | inventory | GET | `/api/v2/warehouses/{warehouseId}/stock` | [Get stock levels for a warehouse](https://www.holded.com/developers/api-reference/warehouses/get-stock-levels-for-a-warehouse) |
| `v2_get_waybill` | inventory | GET | `/api/v2/waybills/{waybillId}` | [Get a waybill](https://www.holded.com/developers/api-reference/waybills/get-a-waybill) |
| `v2_get_waybill_attachment` | inventory | GET | `/api/v2/waybills/{waybillId}/attachments/{attachmentId}` | [Get waybill attachment](https://www.holded.com/developers/api-reference/waybills/get-waybill-attachment) |
| `v2_get_waybill_pdf` | inventory | GET | `/api/v2/waybills/{waybillId}/pdf` | [Get waybill PDF](https://www.holded.com/developers/api-reference/waybills/get-waybill-pdf) |
| `v2_get_webhook` | developers | GET | `/api/v2/webhooks/{webhookId}` | [Get a webhook](https://www.holded.com/developers/api-reference/webhooks/get-a-webhook) |
| `v2_get_webhook_events` | developers | GET | `/api/v2/webhooks/events` | [List supported webhook event types](https://www.holded.com/developers/api-reference/webhooks/list-supported-webhook-event-types) |
| `v2_list_accounting_accounts` | accounting | GET | `/api/v2/accounting-accounts` | [List chart of accounts](https://www.holded.com/developers/api-reference/accounting/list-chart-of-accounts) |
| `v2_list_all_employee_times` | team | GET | `/api/v2/employee-times` | [List all employee time entries](https://www.holded.com/developers/api-reference/employee-time-tracking/list-all-employee-time-entries) |
| `v2_list_all_project_times` | projects | GET | `/api/v2/project-times` | [List all project time entries](https://www.holded.com/developers/api-reference/project-time-tracking/list-all-project-time-entries) |
| `v2_list_all_time_offs` | team | GET | `/api/v2/employees/time-offs` | [List all time off requests (absences / holidays)](https://www.holded.com/developers/api-reference/time-off/list-all-time-off-requests-absences-holidays) |
| `v2_list_banking_account_bank_movements` | treasury | GET | `/api/v2/treasury/accounts/{id}/bank-movements` | [List banking account movements](https://www.holded.com/developers/api-reference/banking-accounts/list-banking-account-movements) |
| `v2_list_banking_account_cash_movements` | treasury | GET | `/api/v2/treasury/accounts/{id}/cash-movements` | [List banking account cash movements](https://www.holded.com/developers/api-reference/banking-accounts/list-banking-account-cash-movements) |
| `v2_list_banking_accounts` | treasury | GET | `/api/v2/treasury/accounts` | [List banking accounts](https://www.holded.com/developers/api-reference/banking-accounts/list-banking-accounts) |
| `v2_list_booking_locations` | calendar | GET | `/api/v2/booking-locations` | [List all booking locations](https://www.holded.com/developers/api-reference/bookings/list-all-booking-locations) |
| `v2_list_bookings` | calendar | GET | `/api/v2/bookings` | [List all bookings](https://www.holded.com/developers/api-reference/bookings/list-all-bookings) |
| `v2_list_business_plan_goals` | treasury | GET | `/api/v2/business-plan/goals` | [List business plan goals vs actuals](https://www.holded.com/developers/api-reference/business-plan/list-business-plan-goals-vs-actuals) |
| `v2_list_business_plan_scenarios` | treasury | GET | `/api/v2/business-plan/scenarios` | [List business plan scenarios](https://www.holded.com/developers/api-reference/business-plan/list-business-plan-scenarios) |
| `v2_list_contact_attachments` | contacts | GET | `/api/v2/contacts/{contactId}/attachments` | [List contact attachments](https://www.holded.com/developers/api-reference/contact/list-contact-attachments) |
| `v2_list_contact_groups` | contacts | GET | `/api/v2/contact-groups` | [List contact groups](https://www.holded.com/developers/api-reference/contact-group/list-contact-groups) |
| `v2_list_contacts` | contacts | GET | `/api/v2/contacts` | [List contacts](https://www.holded.com/developers/api-reference/contact/list-contacts) |
| `v2_list_credit_note_attachments` | sales | GET | `/api/v2/credit-notes/{creditNoteId}/attachments` | [List credit note attachments](https://www.holded.com/developers/api-reference/credit-notes/list-credit-note-attachments) |
| `v2_list_credit_notes` | sales | GET | `/api/v2/credit-notes` | [List credit notes](https://www.holded.com/developers/api-reference/credit-notes/list-credit-notes) |
| `v2_list_employee_time_offs` | team | GET | `/api/v2/employees/{employeeId}/time-offs` | [List time off requests for an employee (absences / holidays)](https://www.holded.com/developers/api-reference/time-off/list-time-off-requests-for-an-employee-absences-holidays) |
| `v2_list_employee_times` | team | GET | `/api/v2/employees/{employeeId}/times` | [List time entries for an employee](https://www.holded.com/developers/api-reference/employee-time-tracking/list-time-entries-for-an-employee) |
| `v2_list_employees` | team | GET | `/api/v2/employees` | [List all employees](https://www.holded.com/developers/api-reference/employees/list-all-employees) |
| `v2_list_estimate_attachments` | sales | GET | `/api/v2/estimates/{estimateId}/attachments` | [List estimate attachments](https://www.holded.com/developers/api-reference/estimates/list-estimate-attachments) |
| `v2_list_estimates` | sales | GET | `/api/v2/estimates` | [List estimates](https://www.holded.com/developers/api-reference/estimates/list-estimates) |
| `v2_list_events` | calendar | GET | `/api/v2/events` | [List all events](https://www.holded.com/developers/api-reference/events/list-all-events) |
| `v2_list_expenses_accounts` | accounting | GET | `/api/v2/expenses-accounts` | [List all expenses accounts](https://www.holded.com/developers/api-reference/expenses-accounts/list-all-expenses-accounts) |
| `v2_list_funnels` | crm | GET | `/api/v2/funnels` | [List all funnels](https://www.holded.com/developers/api-reference/funnels/list-all-funnels) |
| `v2_list_inbox` | inbox | GET | `/api/v2/inbox` | [List inbox incoming documents](https://www.holded.com/developers/api-reference/inbox/list-inbox-incoming-documents) |
| `v2_list_invoice_attachments` | sales | GET | `/api/v2/invoices/{invoiceId}/attachments` | [List invoice attachments](https://www.holded.com/developers/api-reference/invoices/list-invoice-attachments) |
| `v2_list_invoice_recurrings` | sales | GET | `/api/v2/recurring-invoices` | [List recurring invoices](https://www.holded.com/developers/api-reference/recurring-invoices/list-recurring-invoices) |
| `v2_list_invoices` | sales | GET | `/api/v2/invoices` | [List invoices](https://www.holded.com/developers/api-reference/invoices/list-invoices) |
| `v2_list_invoicing_forecasts` | treasury | GET | `/api/v2/treasury/cashflow/invoicing-forecasts` | [List invoicing forecasts](https://www.holded.com/developers/api-reference/invoicing-forecast/list-invoicing-forecasts) |
| `v2_list_leads` | crm | GET | `/api/v2/leads` | [List all leads](https://www.holded.com/developers/api-reference/leads/list-all-leads) |
| `v2_list_ledger_entries` | accounting | GET | `/api/v2/ledger-entries` | [List ledger entries](https://www.holded.com/developers/api-reference/accounting/list-ledger-entries) |
| `v2_list_numbering_series` | sales | GET | `/api/v2/numbering-series/{type}` | [List numbering series by document type](https://www.holded.com/developers/api-reference/numbering-series/list-numbering-series-by-document-type) |
| `v2_list_payment_methods` | treasury | GET | `/api/v2/payment-methods` | [List payment methods](https://www.holded.com/developers/api-reference/payment-methods/list-payment-methods) |
| `v2_list_payments` | accounting | GET | `/api/v2/payments` | [List payments](https://www.holded.com/developers/api-reference/payment/list-payments) |
| `v2_list_payslips` | team | GET | `/api/v2/payslips` | [List payslips](https://www.holded.com/developers/api-reference/payslips/list-payslips) |
| `v2_list_price_lists` | inventory | GET | `/api/v2/price-lists` | [List price lists](https://www.holded.com/developers/api-reference/price-lists/list-price-lists) |
| `v2_list_product_images` | inventory | GET | `/api/v2/products/{productId}/images` | [List product images](https://www.holded.com/developers/api-reference/products/list-product-images) |
| `v2_list_production_orders` | inventory | GET | `/api/v2/production-orders` | [List production orders](https://www.holded.com/developers/api-reference/production-orders/list-production-orders) |
| `v2_list_products` | inventory | GET | `/api/v2/products` | [List all products](https://www.holded.com/developers/api-reference/products/list-all-products) |
| `v2_list_proforma_attachments` | sales | GET | `/api/v2/proformas/{proformaId}/attachments` | [List proforma attachments](https://www.holded.com/developers/api-reference/proformas/list-proforma-attachments) |
| `v2_list_proformas` | sales | GET | `/api/v2/proformas` | [List proformas](https://www.holded.com/developers/api-reference/proformas/list-proformas) |
| `v2_list_project_times` | projects | GET | `/api/v2/projects/{projectId}/times` | [List time entries for a project](https://www.holded.com/developers/api-reference/project-time-tracking/list-time-entries-for-a-project) |
| `v2_list_projects` | projects | GET | `/api/v2/projects` | [List projects](https://www.holded.com/developers/api-reference/projects/list-projects) |
| `v2_list_purchase_attachments` | accounting | GET | `/api/v2/purchases/{purchaseId}/attachments` | [List purchase attachments](https://www.holded.com/developers/api-reference/purchases/list-purchase-attachments) |
| `v2_list_purchase_order_attachments` | inventory | GET | `/api/v2/purchase-orders/{purchaseOrderId}/attachments` | [List purchase order attachments](https://www.holded.com/developers/api-reference/purchase-orders/list-purchase-order-attachments) |
| `v2_list_purchase_orders` | inventory | GET | `/api/v2/purchase-orders` | [List purchase orders](https://www.holded.com/developers/api-reference/purchase-orders/list-purchase-orders) |
| `v2_list_purchase_refunds` | accounting | GET | `/api/v2/purchase-refunds` | [List purchase refunds](https://www.holded.com/developers/api-reference/purchases/list-purchase-refunds) |
| `v2_list_purchase_shipments` | inventory | GET | `/api/v2/purchase-shipments` | [List purchase shipments](https://www.holded.com/developers/api-reference/purchase-shipments/list-purchase-shipments) |
| `v2_list_purchases` | accounting | GET | `/api/v2/purchases` | [List purchases](https://www.holded.com/developers/api-reference/purchases/list-purchases) |
| `v2_list_receipt_note_attachments` | sales | GET | `/api/v2/receipt-notes/{receiptNoteId}/attachments` | [List receipt note attachments](https://www.holded.com/developers/api-reference/receipt-notes/list-receipt-note-attachments) |
| `v2_list_receipt_notes` | sales | GET | `/api/v2/receipt-notes` | [List receipt notes](https://www.holded.com/developers/api-reference/receipt-notes/list-receipt-notes) |
| `v2_list_remittances` | treasury | GET | `/api/v2/treasury/remittances` | [List remittances](https://www.holded.com/developers/api-reference/remittances/list-remittances) |
| `v2_list_salary_records` | team | GET | `/api/v2/salary-records` | [List salary records](https://www.holded.com/developers/api-reference/salary-records/list-salary-records) |
| `v2_list_sales_channels` | sales | GET | `/api/v2/sales-channels` | [List all sales channels](https://www.holded.com/developers/api-reference/sales-channels/list-all-sales-channels) |
| `v2_list_sales_order_attachments` | inventory | GET | `/api/v2/sales-orders/{salesOrderId}/attachments` | [List sales order attachments](https://www.holded.com/developers/api-reference/sales-orders/list-sales-order-attachments) |
| `v2_list_sales_orders` | inventory | GET | `/api/v2/sales-orders` | [List sales orders](https://www.holded.com/developers/api-reference/sales-orders/list-sales-orders) |
| `v2_list_sales_receipt_attachments` | sales | GET | `/api/v2/sales-receipts/{salesReceiptId}/attachments` | [List sales receipt attachments](https://www.holded.com/developers/api-reference/sales-receipts/list-sales-receipt-attachments) |
| `v2_list_sales_receipts` | sales | GET | `/api/v2/sales-receipts` | [List sales receipts](https://www.holded.com/developers/api-reference/sales-receipts/list-sales-receipts) |
| `v2_list_services` | sales | GET | `/api/v2/services` | [List services](https://www.holded.com/developers/api-reference/services/list-services) |
| `v2_list_tags` | contacts | GET | `/api/v2/tags` | [List all tags](https://www.holded.com/developers/api-reference/tags/list-all-tags) |
| `v2_list_tasks` | projects | GET | `/api/v2/tasks` | [List all tasks](https://www.holded.com/developers/api-reference/tasks/list-all-tasks) |
| `v2_list_taxes` | accounting | GET | `/api/v2/taxes` | [List all taxes](https://www.holded.com/developers/api-reference/tax/list-all-taxes) |
| `v2_list_warehouses` | inventory | GET | `/api/v2/warehouses` | [List all warehouses](https://www.holded.com/developers/api-reference/warehouses/list-all-warehouses) |
| `v2_list_waybill_attachments` | inventory | GET | `/api/v2/waybills/{waybillId}/attachments` | [List waybill attachments](https://www.holded.com/developers/api-reference/waybills/list-waybill-attachments) |
| `v2_list_waybills` | inventory | GET | `/api/v2/waybills` | [List waybills](https://www.holded.com/developers/api-reference/waybills/list-waybills) |
| `v2_list_webhooks` | developers | GET | `/api/v2/webhooks` | [List webhooks](https://www.holded.com/developers/api-reference/webhooks/list-webhooks) |
| `v2_pause` | team | POST | `/api/v2/employees/{employeeId}/pause` | [Pause an employee time session](https://www.holded.com/developers/api-reference/employee-time-tracking/pause-an-employee-time-session) |
| `v2_preview_inbox_file` | inbox | GET | `/api/v2/inbox/{incomingDocumentId}/files/{filename}/preview` | [Get a processed thumbnail of a file from an inbox document](https://www.holded.com/developers/api-reference/inbox/get-a-processed-thumbnail-of-a-file-from-an-inbox-document) |
| `v2_receive_purchase_order` | inventory | POST | `/api/v2/purchase-orders/{purchaseOrderId}/receive` | [Receive units of a purchase order](https://www.holded.com/developers/api-reference/purchase-orders/receive-units-of-a-purchase-order) |
| `v2_reconcile_transaction_with_document` | treasury | POST | `/api/v2/treasury/accounts/{bankingAccountId}/bank-movements/{movementId}/reconcile` | [Reconcile a bank movement](https://www.holded.com/developers/api-reference/banking-accounts/reconcile-a-bank-movement) |
| `v2_reject_estimate` | sales | POST | `/api/v2/estimates/{estimateId}/reject` | [Reject an estimate](https://www.holded.com/developers/api-reference/estimates/reject-an-estimate) |
| `v2_search_contacts` | contacts | GET | `/api/v2/contacts/search` | [Search contacts by name](https://www.holded.com/developers/api-reference/contact/search-contacts-by-name) |
| `v2_send_credit_note` | sales | POST | `/api/v2/credit-notes/{creditNoteId}/send` | [Send a credit note by email](https://www.holded.com/developers/api-reference/credit-notes/send-a-credit-note-by-email) |
| `v2_send_estimate` | sales | POST | `/api/v2/estimates/{estimateId}/send` | [Send an estimate by email](https://www.holded.com/developers/api-reference/estimates/send-an-estimate-by-email) |
| `v2_send_invoice` | sales | POST | `/api/v2/invoices/{invoiceId}/send` | [Send an invoice by email](https://www.holded.com/developers/api-reference/invoices/send-an-invoice-by-email) |
| `v2_send_proforma` | sales | POST | `/api/v2/proformas/{proformaId}/send` | [Send a proforma by email](https://www.holded.com/developers/api-reference/proformas/send-a-proforma-by-email) |
| `v2_send_purchase_order` | inventory | POST | `/api/v2/purchase-orders/{purchaseOrderId}/send` | [Send a purchase order by email](https://www.holded.com/developers/api-reference/purchase-orders/send-a-purchase-order-by-email) |
| `v2_send_receipt_note` | sales | POST | `/api/v2/receipt-notes/{receiptNoteId}/send` | [Send a receipt note by email](https://www.holded.com/developers/api-reference/receipt-notes/send-a-receipt-note-by-email) |
| `v2_send_sales_order` | inventory | POST | `/api/v2/sales-orders/{salesOrderId}/send` | [Send a sales order by email](https://www.holded.com/developers/api-reference/sales-orders/send-a-sales-order-by-email) |
| `v2_send_sales_receipt` | sales | POST | `/api/v2/sales-receipts/{salesReceiptId}/send` | [Send a sales receipt by email](https://www.holded.com/developers/api-reference/sales-receipts/send-a-sales-receipt-by-email) |
| `v2_send_waybill` | inventory | POST | `/api/v2/waybills/{waybillId}/send` | [Send a waybill by email](https://www.holded.com/developers/api-reference/waybills/send-a-waybill-by-email) |
| `v2_set_credit_note_pipeline` | sales | PUT | `/api/v2/credit-notes/{creditNoteId}/pipeline` | [Set credit note pipeline](https://www.holded.com/developers/api-reference/credit-notes/set-credit-note-pipeline) |
| `v2_set_estimate_pipeline` | sales | PUT | `/api/v2/estimates/{estimateId}/pipeline` | [Set estimate pipeline](https://www.holded.com/developers/api-reference/estimates/set-estimate-pipeline) |
| `v2_set_invoice_pipeline` | sales | PUT | `/api/v2/invoices/{invoiceId}/pipeline` | [Set invoice pipeline](https://www.holded.com/developers/api-reference/invoices/set-invoice-pipeline) |
| `v2_set_proforma_pipeline` | sales | PUT | `/api/v2/proformas/{proformaId}/pipeline` | [Set proforma pipeline](https://www.holded.com/developers/api-reference/proformas/set-proforma-pipeline) |
| `v2_set_purchase_order_pipeline` | inventory | PUT | `/api/v2/purchase-orders/{purchaseOrderId}/pipeline` | [Set purchase order pipeline](https://www.holded.com/developers/api-reference/purchase-orders/set-purchase-order-pipeline) |
| `v2_set_purchase_pipeline` | accounting | PUT | `/api/v2/purchases/{purchaseId}/pipeline` | [Set purchase pipeline](https://www.holded.com/developers/api-reference/purchases/set-purchase-pipeline) |
| `v2_set_receipt_note_pipeline` | sales | PUT | `/api/v2/receipt-notes/{receiptNoteId}/pipeline` | [Set receipt note pipeline](https://www.holded.com/developers/api-reference/receipt-notes/set-receipt-note-pipeline) |
| `v2_set_sales_order_pipeline` | inventory | PUT | `/api/v2/sales-orders/{salesOrderId}/pipeline` | [Set sales order pipeline](https://www.holded.com/developers/api-reference/sales-orders/set-sales-order-pipeline) |
| `v2_set_sales_receipt_pipeline` | sales | PUT | `/api/v2/sales-receipts/{salesReceiptId}/pipeline` | [Set sales receipt pipeline](https://www.holded.com/developers/api-reference/sales-receipts/set-sales-receipt-pipeline) |
| `v2_set_waybill_pipeline` | inventory | PUT | `/api/v2/waybills/{waybillId}/pipeline` | [Set waybill pipeline](https://www.holded.com/developers/api-reference/waybills/set-waybill-pipeline) |
| `v2_ship_sales_order` | inventory | POST | `/api/v2/sales-orders/{salesOrderId}/ship` | [Ship all items in a sales order](https://www.holded.com/developers/api-reference/sales-orders/ship-all-items-in-a-sales-order) |
| `v2_ship_sales_order_by_lines` | inventory | POST | `/api/v2/sales-orders/{salesOrderId}/ship-by-lines` | [Ship specific lines in a sales order](https://www.holded.com/developers/api-reference/sales-orders/ship-specific-lines-in-a-sales-order) |
| `v2_skip_recurring_occurrence` | sales | POST | `/api/v2/recurring-invoices/{invoiceRecurringId}/skip` | [Skip a recurring invoice occurrence](https://www.holded.com/developers/api-reference/recurring-invoices/skip-a-recurring-invoice-occurrence) |
| `v2_unpause` | team | POST | `/api/v2/employees/{employeeId}/unpause` | [Resume an employee time session](https://www.holded.com/developers/api-reference/employee-time-tracking/resume-an-employee-time-session) |
| `v2_update_banking_account` | treasury | PUT | `/api/v2/treasury/accounts/{id}` | [Update a banking account](https://www.holded.com/developers/api-reference/banking-accounts/update-a-banking-account) |
| `v2_update_booking` | calendar | PUT | `/api/v2/bookings/{bookingId}` | [Update a booking](https://www.holded.com/developers/api-reference/bookings/update-a-booking) |
| `v2_update_contact` | contacts | PUT | `/api/v2/contacts/{contactId}` | [Update a contact](https://www.holded.com/developers/api-reference/contact/update-a-contact) |
| `v2_update_contact_group` | contacts | PUT | `/api/v2/contact-groups/{contactGroupId}` | [Update a contact group](https://www.holded.com/developers/api-reference/contact-group/update-a-contact-group) |
| `v2_update_credit_note` | sales | PUT | `/api/v2/credit-notes/{creditNoteId}` | [Update a credit note](https://www.holded.com/developers/api-reference/credit-notes/update-a-credit-note) |
| `v2_update_employee` | team | PUT | `/api/v2/employees/{employeeId}` | [Update an employee](https://www.holded.com/developers/api-reference/employees/update-an-employee) |
| `v2_update_employee_contract` | team | PUT | `/api/v2/employees/{employeeId}/contract` | [Update active contract](https://www.holded.com/developers/api-reference/employees/update-active-contract) |
| `v2_update_employee_time` | team | PUT | `/api/v2/employee-times/{timeId}` | [Update an employee time entry](https://www.holded.com/developers/api-reference/employee-time-tracking/update-an-employee-time-entry) |
| `v2_update_estimate` | sales | PUT | `/api/v2/estimates/{estimateId}` | [Update an estimate](https://www.holded.com/developers/api-reference/estimates/update-an-estimate) |
| `v2_update_event` | calendar | PUT | `/api/v2/events/{eventId}` | [Update an event](https://www.holded.com/developers/api-reference/events/update-an-event) |
| `v2_update_expenses_account` | accounting | PUT | `/api/v2/expenses-accounts/{expensesAccountId}` | [Update an expenses account](https://www.holded.com/developers/api-reference/expenses-accounts/update-an-expenses-account) |
| `v2_update_funnel` | crm | PUT | `/api/v2/funnels/{funnelId}` | [Update a funnel](https://www.holded.com/developers/api-reference/funnels/update-a-funnel) |
| `v2_update_inbox` | inbox | PUT | `/api/v2/inbox/{incomingDocumentId}` | [Update an incoming document](https://www.holded.com/developers/api-reference/inbox/update-an-incoming-document) |
| `v2_update_invoice` | sales | PUT | `/api/v2/invoices/{invoiceId}` | [Update an invoice](https://www.holded.com/developers/api-reference/invoices/update-an-invoice) |
| `v2_update_invoice_recurring` | sales | PUT | `/api/v2/recurring-invoices/{invoiceRecurringId}` | [Update a recurring invoice](https://www.holded.com/developers/api-reference/recurring-invoices/update-a-recurring-invoice) |
| `v2_update_lead` | crm | PUT | `/api/v2/leads/{leadId}` | [Update a lead](https://www.holded.com/developers/api-reference/leads/update-a-lead) |
| `v2_update_lead_dates` | crm | PUT | `/api/v2/leads/{leadId}/dates` | [Update lead dates](https://www.holded.com/developers/api-reference/leads/update-lead-dates) |
| `v2_update_lead_note` | crm | PUT | `/api/v2/leads/{leadId}/notes` | [Update a lead note](https://www.holded.com/developers/api-reference/leads/update-a-lead-note) |
| `v2_update_lead_stage` | crm | PUT | `/api/v2/leads/{leadId}/stage` | [Update a lead stage](https://www.holded.com/developers/api-reference/leads/update-a-lead-stage) |
| `v2_update_lead_task` | crm | PUT | `/api/v2/leads/{leadId}/tasks` | [Update a lead task](https://www.holded.com/developers/api-reference/leads/update-a-lead-task) |
| `v2_update_numbering_series` | sales | PUT | `/api/v2/numbering-series/{type}/{numberingSeriesId}` | [Update a numbering series](https://www.holded.com/developers/api-reference/numbering-series/update-a-numbering-series) |
| `v2_update_payment` | accounting | PUT | `/api/v2/payments/{paymentId}` | [Update a payment](https://www.holded.com/developers/api-reference/payment/update-a-payment) |
| `v2_update_payment_method` | treasury | PUT | `/api/v2/payment-methods/{paymentMethodId}` | [Update a payment method](https://www.holded.com/developers/api-reference/payment-methods/update-a-payment-method) |
| `v2_update_price_list` | inventory | PATCH | `/api/v2/price-lists/{priceListId}` | [Update a price list](https://www.holded.com/developers/api-reference/price-lists/update-a-price-list) |
| `v2_update_product` | inventory | PUT | `/api/v2/products/{productId}` | [Update a product](https://www.holded.com/developers/api-reference/products/update-a-product) |
| `v2_update_product_stock` | inventory | PUT | `/api/v2/products/{productId}/stock` | [Update stock for a product](https://www.holded.com/developers/api-reference/products/update-stock-for-a-product) |
| `v2_update_production_order` | inventory | PUT | `/api/v2/production-orders/{productionOrderId}` | [Update a production order](https://www.holded.com/developers/api-reference/production-orders/update-a-production-order) |
| `v2_update_proforma` | sales | PUT | `/api/v2/proformas/{proformaId}` | [Update a proforma](https://www.holded.com/developers/api-reference/proformas/update-a-proforma) |
| `v2_update_project` | projects | PUT | `/api/v2/projects/{projectId}` | [Update a project](https://www.holded.com/developers/api-reference/projects/update-a-project) |
| `v2_update_project_time` | projects | PUT | `/api/v2/projects/{projectId}/times/{timeId}` | [Update a project time entry](https://www.holded.com/developers/api-reference/project-time-tracking/update-a-project-time-entry) |
| `v2_update_purchase` | accounting | PUT | `/api/v2/purchases/{purchaseId}` | [Update a purchase](https://www.holded.com/developers/api-reference/purchases/update-a-purchase) |
| `v2_update_purchase_order` | inventory | PUT | `/api/v2/purchase-orders/{purchaseOrderId}` | [Update a purchase order](https://www.holded.com/developers/api-reference/purchase-orders/update-a-purchase-order) |
| `v2_update_purchase_shipment` | inventory | PUT | `/api/v2/purchase-shipments/{purchaseShipmentId}` | [Update a purchase shipment](https://www.holded.com/developers/api-reference/purchase-shipments/update-a-purchase-shipment) |
| `v2_update_receipt_note` | sales | PUT | `/api/v2/receipt-notes/{receiptNoteId}` | [Update a receipt note](https://www.holded.com/developers/api-reference/receipt-notes/update-a-receipt-note) |
| `v2_update_salary_record` | team | PUT | `/api/v2/salary-records/{salaryRecordId}` | [Update a salary record](https://www.holded.com/developers/api-reference/salary-records/update-a-salary-record) |
| `v2_update_sales_channel` | sales | PUT | `/api/v2/sales-channels/{salesChannelId}` | [Update a sales channel](https://www.holded.com/developers/api-reference/sales-channels/update-a-sales-channel) |
| `v2_update_sales_order` | inventory | PUT | `/api/v2/sales-orders/{salesOrderId}` | [Update a sales order](https://www.holded.com/developers/api-reference/sales-orders/update-a-sales-order) |
| `v2_update_sales_order_tracking` | inventory | PUT | `/api/v2/sales-orders/{salesOrderId}/tracking` | [Update sales order tracking information](https://www.holded.com/developers/api-reference/sales-orders/update-sales-order-tracking-information) |
| `v2_update_sales_receipt` | sales | PUT | `/api/v2/sales-receipts/{salesReceiptId}` | [Update a sales receipt](https://www.holded.com/developers/api-reference/sales-receipts/update-a-sales-receipt) |
| `v2_update_service` | sales | PUT | `/api/v2/services/{serviceId}` | [Update a service](https://www.holded.com/developers/api-reference/services/update-a-service) |
| `v2_update_task` | projects | PUT | `/api/v2/tasks/{taskId}` | [Update a task](https://www.holded.com/developers/api-reference/tasks/update-a-task) |
| `v2_update_time_off` | team | PUT | `/api/v2/employees/{employeeId}/time-offs/{timeOffId}` | [Update time off end date (absence / holiday)](https://www.holded.com/developers/api-reference/time-off/update-time-off-end-date-absence-holiday) |
| `v2_update_warehouse` | inventory | PATCH | `/api/v2/warehouses/{warehouseId}` | [Update a warehouse](https://www.holded.com/developers/api-reference/warehouses/update-a-warehouse) |
| `v2_update_waybill` | inventory | PUT | `/api/v2/waybills/{waybillId}` | [Update a waybill](https://www.holded.com/developers/api-reference/waybills/update-a-waybill) |
| `v2_update_waybill_tracking` | inventory | PUT | `/api/v2/waybills/{waybillId}/tracking` | [Update waybill tracking information](https://www.holded.com/developers/api-reference/waybills/update-waybill-tracking-information) |
| `v2_update_webhook` | developers | PUT | `/api/v2/webhooks/{webhookId}` | [Update a webhook](https://www.holded.com/developers/api-reference/webhooks/update-a-webhook) |
| `v2_upload_inbox` | inbox | POST | `/api/v2/inbox` | [Upload a document](https://www.holded.com/developers/api-reference/inbox/upload-a-document) |
| `v2_upload_product_image` | inventory | POST | `/api/v2/products/{productId}/images` | [Upload a product image](https://www.holded.com/developers/api-reference/products/upload-a-product-image) |

### v1

| Operation ID | API | Method | Path | API reference |
| --- | --- | --- | --- | --- |
| `v1_accounting_CreateAccount` | accounting | POST | `/api/accounting/v1/account` | [Create a new accounting account](https://www.holded.com/developers/v1/accounting-api/chart-of-accounts/createaccount) |
| `v1_accounting_CreateEntry` | accounting | POST | `/api/accounting/v1/entry` | [Create entry](https://www.holded.com/developers/v1/accounting-api/daily-ledger/createentry) |
| `v1_accounting_ListAccounts` | accounting | GET | `/api/accounting/v1/chartofaccounts` | [List all your accounting accounts](https://www.holded.com/developers/v1/accounting-api/chart-of-accounts/listaccounts) |
| `v1_accounting_ListDailyLedger` | accounting | GET | `/api/accounting/v1/dailyledger` | [List all your entries](https://www.holded.com/developers/v1/accounting-api/daily-ledger/listdailyledger) |
| `v1_crm_CancelBooking` | crm | DELETE | `/api/crm/v1/bookings/{bookingId}` | [Cancel Booking](https://www.holded.com/developers/v1/crm-api/bookings/cancel-booking) |
| `v1_crm_CreateBooking` | crm | POST | `/api/crm/v1/bookings` | [Create Booking](https://www.holded.com/developers/v1/crm-api/bookings/create-booking) |
| `v1_crm_CreateEvent` | crm | POST | `/api/crm/v1/events` | [Create Event](https://www.holded.com/developers/v1/crm-api/events/create-event) |
| `v1_crm_CreateFunnel` | crm | POST | `/api/crm/v1/funnels` | [Create Funnel](https://www.holded.com/developers/v1/crm-api/funnels/create-funnel) |
| `v1_crm_CreateLead` | crm | POST | `/api/crm/v1/leads` | [Create Lead](https://www.holded.com/developers/v1/crm-api/leads/create-lead) |
| `v1_crm_CreateLeadNote` | crm | POST | `/api/crm/v1/leads/{leadId}/notes` | [Create Lead Note](https://www.holded.com/developers/v1/crm-api/leads/create-lead-note) |
| `v1_crm_CreateLeadTask` | crm | POST | `/api/crm/v1/leads/{leadId}/tasks` | [Create Lead Task](https://www.holded.com/developers/v1/crm-api/leads/create-lead-task) |
| `v1_crm_DeleteEvent` | crm | DELETE | `/api/crm/v1/events/{eventId}` | [Delete Event](https://www.holded.com/developers/v1/crm-api/events/delete-event) |
| `v1_crm_DeleteFunnel` | crm | DELETE | `/api/crm/v1/funnels/{funnelId}` | [Delete Funnel](https://www.holded.com/developers/v1/crm-api/funnels/delete-funnel) |
| `v1_crm_DeleteLead` | crm | DELETE | `/api/crm/v1/leads/{leadId}` | [Delete Lead](https://www.holded.com/developers/v1/crm-api/leads/delete-lead) |
| `v1_crm_DeleteLeadTask` | crm | DELETE | `/api/crm/v1/leads/{leadId}/tasks` | [Delete Lead Task](https://www.holded.com/developers/v1/crm-api/leads/delete-lead-task) |
| `v1_crm_GetAvailableSlotsForLocation` | crm | GET | `/api/crm/v1/bookings/locations/{locationId}/slots` | [Get available slots for location](https://www.holded.com/developers/v1/crm-api/bookings/get-available-slots-for-location) |
| `v1_crm_GetBooking` | crm | GET | `/api/crm/v1/bookings/{bookingId}` | [Get Booking](https://www.holded.com/developers/v1/crm-api/bookings/get-booking) |
| `v1_crm_GetEvent` | crm | GET | `/api/crm/v1/events/{eventId}` | [Get Event](https://www.holded.com/developers/v1/crm-api/events/get-event) |
| `v1_crm_GetFunnel` | crm | GET | `/api/crm/v1/funnels/{funnelId}` | [Get Funnel](https://www.holded.com/developers/v1/crm-api/funnels/get-funnel) |
| `v1_crm_GetLead` | crm | GET | `/api/crm/v1/leads/{leadId}` | [Get Lead](https://www.holded.com/developers/v1/crm-api/leads/get-lead) |
| `v1_crm_ListBookings` | crm | GET | `/api/crm/v1/bookings` | [List Bookings](https://www.holded.com/developers/v1/crm-api/bookings/list-bookings) |
| `v1_crm_ListEvents` | crm | GET | `/api/crm/v1/events` | [List Events](https://www.holded.com/developers/v1/crm-api/events/list-events) |
| `v1_crm_ListFunnels` | crm | GET | `/api/crm/v1/funnels` | [List Funnels](https://www.holded.com/developers/v1/crm-api/funnels/list-funnels) |
| `v1_crm_ListLeads` | crm | GET | `/api/crm/v1/leads` | [List Leads](https://www.holded.com/developers/v1/crm-api/leads/list-leads) |
| `v1_crm_ListLocations` | crm | GET | `/api/crm/v1/bookings/locations` | [List Locations](https://www.holded.com/developers/v1/crm-api/bookings/list-locations) |
| `v1_crm_UpdateBooking` | crm | PUT | `/api/crm/v1/bookings/{bookingId}` | [Update Booking](https://www.holded.com/developers/v1/crm-api/bookings/update-booking) |
| `v1_crm_UpdateEvent` | crm | PUT | `/api/crm/v1/events/{eventId}` | [Update Event](https://www.holded.com/developers/v1/crm-api/events/update-event) |
| `v1_crm_UpdateFunnel` | crm | PUT | `/api/crm/v1/funnels/{funnelId}` | [Update Funnel](https://www.holded.com/developers/v1/crm-api/funnels/update-funnel) |
| `v1_crm_UpdateLead` | crm | PUT | `/api/crm/v1/leads/{leadId}` | [Update Lead](https://www.holded.com/developers/v1/crm-api/leads/update-lead) |
| `v1_crm_UpdateLeadCreationDate` | crm | PUT | `/api/crm/v1/leads/{leadId}/dates` | [Update Lead Creation Date](https://www.holded.com/developers/v1/crm-api/leads/update-lead-creation-date) |
| `v1_crm_UpdateLeadNote` | crm | PUT | `/api/crm/v1/leads/{leadId}/notes` | [Update Lead Note](https://www.holded.com/developers/v1/crm-api/leads/update-lead-note) |
| `v1_crm_UpdateLeadStage` | crm | PUT | `/api/crm/v1/leads/{leadId}/stages` | [Update Lead Stage](https://www.holded.com/developers/v1/crm-api/leads/update-lead-stage) |
| `v1_crm_UpdateLeadTask` | crm | PUT | `/api/crm/v1/leads/{leadId}/tasks` | [Update Lead Task](https://www.holded.com/developers/v1/crm-api/leads/update-lead-task) |
| `v1_invoicing_AttachFile` | invoicing | POST | `/api/invoicing/v1/documents/{docType}/{documentId}/attach` | [Attach File to a specific document](https://www.holded.com/developers/v1/invoice-api/documents/attach-file) |
| `v1_invoicing_CreateContact` | invoicing | POST | `/api/invoicing/v1/contacts` | [Create Contact](https://www.holded.com/developers/v1/invoice-api/contacts/create-contact) |
| `v1_invoicing_CreateContactGroup` | invoicing | POST | `/api/invoicing/v1/contacts/groups` | [Create Contact Group](https://www.holded.com/developers/v1/invoice-api/contact-groups/create-contact-group) |
| `v1_invoicing_CreateDocument` | invoicing | POST | `/api/invoicing/v1/documents/{docType}` | [Create Document](https://www.holded.com/developers/v1/invoice-api/documents/create-document) |
| `v1_invoicing_CreateExpensesAccount` | invoicing | POST | `/api/invoicing/v1/expensesaccounts` | [Create Expenses Account](https://www.holded.com/developers/v1/invoice-api/expenses-accounts/create-expenses-account) |
| `v1_invoicing_CreateNumberingSerie` | invoicing | POST | `/api/invoicing/v1/numberingseries/{type}` | [Create Numbering Serie](https://www.holded.com/developers/v1/invoice-api/numbering-series/create-numbering-serie) |
| `v1_invoicing_CreatePayment` | invoicing | POST | `/api/invoicing/v1/payments` | [Create Payment](https://www.holded.com/developers/v1/invoice-api/payments/create-payment) |
| `v1_invoicing_CreateProduct` | invoicing | POST | `/api/invoicing/v1/products` | [Create Product](https://www.holded.com/developers/v1/invoice-api/products/create-product) |
| `v1_invoicing_CreateSalesChannel` | invoicing | POST | `/api/invoicing/v1/saleschannels` | [Create Sales Channel](https://www.holded.com/developers/v1/invoice-api/sales-channels/create-sales-channel) |
| `v1_invoicing_CreateService` | invoicing | POST | `/api/invoicing/v1/services` | [Create Service](https://www.holded.com/developers/v1/invoice-api/services/create-service) |
| `v1_invoicing_CreateTreasury` | invoicing | POST | `/api/invoicing/v1/treasury` | [Create Treasury Account](https://www.holded.com/developers/v1/invoice-api/treasuries/create-treasury) |
| `v1_invoicing_CreateWarehouse` | invoicing | POST | `/api/invoicing/v1/warehouses` | [Create Warehouse](https://www.holded.com/developers/v1/invoice-api/warehouses/create-warehouse) |
| `v1_invoicing_DeleteContact` | invoicing | DELETE | `/api/invoicing/v1/contacts/{contactId}` | [Delete Contact](https://www.holded.com/developers/v1/invoice-api/contacts/delete-contact) |
| `v1_invoicing_DeleteContactGroup` | invoicing | DELETE | `/api/invoicing/v1/contacts/groups/{groupId}` | [Delete Contact Group](https://www.holded.com/developers/v1/invoice-api/contact-groups/delete-contact-group) |
| `v1_invoicing_DeleteDocument` | invoicing | DELETE | `/api/invoicing/v1/documents/{docType}/{documentId}` | [Delete Document](https://www.holded.com/developers/v1/invoice-api/documents/delete-document) |
| `v1_invoicing_DeleteExpensesAccount` | invoicing | DELETE | `/api/invoicing/v1/expensesaccounts/{expensesAccountId}` | [Delete Expenses Account](https://www.holded.com/developers/v1/invoice-api/expenses-accounts/delete-expenses-account) |
| `v1_invoicing_DeleteNumberingSerie` | invoicing | DELETE | `/api/invoicing/v1/numberingseries/{type}/{numberingSeriesId}` | [Delete Numbering Serie](https://www.holded.com/developers/v1/invoice-api/numbering-series/delete-numbering-serie) |
| `v1_invoicing_DeletePayment` | invoicing | DELETE | `/api/invoicing/v1/payments/{paymentId}` | [Delete Payment](https://www.holded.com/developers/v1/invoice-api/payments/delete-payment) |
| `v1_invoicing_DeleteProduct` | invoicing | DELETE | `/api/invoicing/v1/products/{productId}` | [Delete Product](https://www.holded.com/developers/v1/invoice-api/products/delete-product) |
| `v1_invoicing_DeleteSalesChannel` | invoicing | DELETE | `/api/invoicing/v1/saleschannels/{salesChannelId}` | [Delete Sales Channel](https://www.holded.com/developers/v1/invoice-api/sales-channels/delete-sales-channel) |
| `v1_invoicing_DeleteService` | invoicing | DELETE | `/api/invoicing/v1/services/{serviceId}` | [Delete Service](https://www.holded.com/developers/v1/invoice-api/services/delete-service) |
| `v1_invoicing_DeleteWarehouse` | invoicing | DELETE | `/api/invoicing/v1/warehouses/{warehouseId}` | [Delete Warehouse](https://www.holded.com/developers/v1/invoice-api/warehouses/delete-warehouse) |
| `v1_invoicing_GetAttachment` | invoicing | GET | `/api/invoicing/v1/contacts/{contactId}/attachments/get` | [Get attachment](https://www.holded.com/developers/v1/invoice-api/contacts/get-attachment) |
| `v1_invoicing_GetAttachmentsList` | invoicing | GET | `/api/invoicing/v1/contacts/{contactId}/attachments/list` | [Get contact attachments list](https://www.holded.com/developers/v1/invoice-api/contacts/get-attachments-list) |
| `v1_invoicing_GetContact` | invoicing | GET | `/api/invoicing/v1/contacts/{contactId}` | [Get Contact](https://www.holded.com/developers/v1/invoice-api/contacts/get-contact) |
| `v1_invoicing_GetContactGroup` | invoicing | GET | `/api/invoicing/v1/contacts/groups/{groupId}` | [Get Contact Group](https://www.holded.com/developers/v1/invoice-api/contact-groups/get-contact-group) |
| `v1_invoicing_GetDocument` | invoicing | GET | `/api/invoicing/v1/documents/{docType}/{documentId}` | [Get Document](https://www.holded.com/developers/v1/invoice-api/documents/getdocument) |
| `v1_invoicing_GetDocumentPDF` | invoicing | GET | `/api/invoicing/v1/documents/{docType}/{documentId}/pdf` | [Get Document PDF](https://www.holded.com/developers/v1/invoice-api/documents/getdocumentpdf) |
| `v1_invoicing_GetExpensesAccount` | invoicing | GET | `/api/invoicing/v1/expensesaccounts/{expensesAccountId}` | [Get Expenses Account](https://www.holded.com/developers/v1/invoice-api/expenses-accounts/get-expenses-account) |
| `v1_invoicing_GetNumberingSeries` | invoicing | GET | `/api/invoicing/v1/numberingseries/{type}` | [Get Numbering Series by Type](https://www.holded.com/developers/v1/invoice-api/numbering-series/get-numbering-series) |
| `v1_invoicing_GetPayment` | invoicing | GET | `/api/invoicing/v1/payments/{paymentId}` | [Get Payment](https://www.holded.com/developers/v1/invoice-api/payments/get-payment) |
| `v1_invoicing_GetProduct` | invoicing | GET | `/api/invoicing/v1/products/{productId}` | [Get  Product](https://www.holded.com/developers/v1/invoice-api/products/get-product) |
| `v1_invoicing_GetProductImage` | invoicing | GET | `/api/invoicing/v1/products/{productId}/image` | [Get Product Main Image](https://www.holded.com/developers/v1/invoice-api/products/get-product-image) |
| `v1_invoicing_GetProductSecondaryImage` | invoicing | GET | `/api/invoicing/v1/products/{productId}/image/{imageFileName}` | [Get Product Secondary Image](https://www.holded.com/developers/v1/invoice-api/products/get-product-secondary-image) |
| `v1_invoicing_GetRemittance` | invoicing | GET | `/api/invoicing/v1/remittances/{remittanceId}` | [Get Remittance](https://www.holded.com/developers/v1/invoice-api/remittances/get-remittance) |
| `v1_invoicing_GetSalesChannel` | invoicing | GET | `/api/invoicing/v1/saleschannels/{salesChannelId}` | [Get Sales Channel](https://www.holded.com/developers/v1/invoice-api/sales-channels/get-sales-channel) |
| `v1_invoicing_GetService` | invoicing | GET | `/api/invoicing/v1/services/{serviceId}` | [Get Service](https://www.holded.com/developers/v1/invoice-api/services/get-service) |
| `v1_invoicing_GetTaxes` | invoicing | GET | `/api/invoicing/v1/taxes` | [Get Taxes](https://www.holded.com/developers/v1/invoice-api/taxes/gettaxes) |
| `v1_invoicing_GetTreasury` | invoicing | GET | `/api/invoicing/v1/treasury/{treasuryId}` | [Get Treasury Account](https://www.holded.com/developers/v1/invoice-api/treasuries/get-treasury) |
| `v1_invoicing_GetWarehouse` | invoicing | GET | `/api/invoicing/v1/warehouses/{warehouseId}` | [Get Warehouse](https://www.holded.com/developers/v1/invoice-api/warehouses/get-warehouse) |
| `v1_invoicing_ListContactGroups` | invoicing | GET | `/api/invoicing/v1/contacts/groups` | [List Contact Groups](https://www.holded.com/developers/v1/invoice-api/contact-groups/list-contact-groups) |
| `v1_invoicing_ListContacts` | invoicing | GET | `/api/invoicing/v1/contacts` | [List Contacts](https://www.holded.com/developers/v1/invoice-api/contacts/list-contacts) |
| `v1_invoicing_ListDocuments` | invoicing | GET | `/api/invoicing/v1/documents/{docType}` | [List Documents](https://www.holded.com/developers/v1/invoice-api/documents/list-documents) |
| `v1_invoicing_ListExpensesAccounts` | invoicing | GET | `/api/invoicing/v1/expensesaccounts` | [List Expenses Accounts](https://www.holded.com/developers/v1/invoice-api/expenses-accounts/list-expenses-accounts) |
| `v1_invoicing_ListPaymentMethods` | invoicing | GET | `/api/invoicing/v1/paymentmethods` | [List Payment methods](https://www.holded.com/developers/v1/invoice-api/documents/list-payment-methods) |
| `v1_invoicing_ListPayments` | invoicing | GET | `/api/invoicing/v1/payments` | [List Payments](https://www.holded.com/developers/v1/invoice-api/payments/list-payments) |
| `v1_invoicing_ListProductImages` | invoicing | GET | `/api/invoicing/v1/products/{productId}/imagesList` | [List Product Images](https://www.holded.com/developers/v1/invoice-api/products/list-product-images) |
| `v1_invoicing_ListProducts` | invoicing | GET | `/api/invoicing/v1/products` | [List Products](https://www.holded.com/developers/v1/invoice-api/products/list-products) |
| `v1_invoicing_ListProductsStock` | invoicing | GET | `/api/invoicing/v1/warehouses/{warehouseId}/stock` | [List products stock](https://www.holded.com/developers/v1/invoice-api/warehouses/list-products-stock) |
| `v1_invoicing_ListRemittances` | invoicing | GET | `/api/invoicing/v1/remittances` | [List Remittances](https://www.holded.com/developers/v1/invoice-api/remittances/list-remittances) |
| `v1_invoicing_ListSalesChannels` | invoicing | GET | `/api/invoicing/v1/saleschannels` | [List Sales Channels](https://www.holded.com/developers/v1/invoice-api/sales-channels/list-sales-channels) |
| `v1_invoicing_ListServices` | invoicing | GET | `/api/invoicing/v1/services` | [List Services](https://www.holded.com/developers/v1/invoice-api/services/list-services) |
| `v1_invoicing_ListTreasuries` | invoicing | GET | `/api/invoicing/v1/treasury` | [List Treasuries Accounts](https://www.holded.com/developers/v1/invoice-api/treasuries/list-treasuries) |
| `v1_invoicing_ListWarehouses` | invoicing | GET | `/api/invoicing/v1/warehouses` | [List Warehouses](https://www.holded.com/developers/v1/invoice-api/warehouses/list-warehouses) |
| `v1_invoicing_PayDocument` | invoicing | POST | `/api/invoicing/v1/documents/{docType}/{documentId}/pay` | [Pay Document](https://www.holded.com/developers/v1/invoice-api/documents/pay-document) |
| `v1_invoicing_SendDocument` | invoicing | POST | `/api/invoicing/v1/documents/{docType}/{documentId}/send` | [Send Document](https://www.holded.com/developers/v1/invoice-api/documents/send-document) |
| `v1_invoicing_ShipAllItems` | invoicing | POST | `/api/invoicing/v1/documents/salesorder/{documentId}/shipall` | [Ship All Items](https://www.holded.com/developers/v1/invoice-api/documents/ship-all-items) |
| `v1_invoicing_ShipItemsByLine` | invoicing | POST | `/api/invoicing/v1/documents/salesorder/{documentId}/shipbylines` | [Ship items by line](https://www.holded.com/developers/v1/invoice-api/documents/ship-items-by-line) |
| `v1_invoicing_ShippedUnitsByItem` | invoicing | GET | `/api/invoicing/v1/documents/{docType}/{documentId}/shippeditems` | [Shipped units by item](https://www.holded.com/developers/v1/invoice-api/documents/shipped-units-by-item) |
| `v1_invoicing_UpdateContact` | invoicing | PUT | `/api/invoicing/v1/contacts/{contactId}` | [Update Contact](https://www.holded.com/developers/v1/invoice-api/contacts/update-contact) |
| `v1_invoicing_UpdateContactGroup` | invoicing | PUT | `/api/invoicing/v1/contacts/groups/{groupId}` | [Update Contact Group](https://www.holded.com/developers/v1/invoice-api/contact-groups/update-contact-group) |
| `v1_invoicing_UpdateDocument` | invoicing | PUT | `/api/invoicing/v1/documents/{docType}/{documentId}` | [Update Document](https://www.holded.com/developers/v1/invoice-api/documents/update-document) |
| `v1_invoicing_UpdateDocumentPipeline` | invoicing | POST | `/api/invoicing/v1/documents/{docType}/{documentId}/pipeline/set` | [Update pipeline from specific document.](https://www.holded.com/developers/v1/invoice-api/documents/update-document-pipeline) |
| `v1_invoicing_UpdateExpensesAccount` | invoicing | PUT | `/api/invoicing/v1/expensesaccounts/{expensesAccountId}` | [Update Expenses Account](https://www.holded.com/developers/v1/invoice-api/expenses-accounts/update-expenses-account) |
| `v1_invoicing_UpdateNumberingSerie` | invoicing | PUT | `/api/invoicing/v1/numberingseries/{type}/{numberingSeriesId}` | [Update Numbering Serie](https://www.holded.com/developers/v1/invoice-api/numbering-series/update-numbering-serie) |
| `v1_invoicing_UpdatePayment` | invoicing | PUT | `/api/invoicing/v1/payments/{paymentId}` | [Update Payment](https://www.holded.com/developers/v1/invoice-api/payments/update-payment) |
| `v1_invoicing_UpdateProduct` | invoicing | PUT | `/api/invoicing/v1/products/{productId}` | [Update Product](https://www.holded.com/developers/v1/invoice-api/products/update-product) |
| `v1_invoicing_UpdateProductStock` | invoicing | PUT | `/api/invoicing/v1/products/{productId}/stock` | [Update Product stock](https://www.holded.com/developers/v1/invoice-api/products/update-product-stock) |
| `v1_invoicing_UpdateSalesChannel` | invoicing | PUT | `/api/invoicing/v1/saleschannels/{salesChannelId}` | [Update Sales Channel](https://www.holded.com/developers/v1/invoice-api/sales-channels/update-sales-channel) |
| `v1_invoicing_UpdateService` | invoicing | PUT | `/api/invoicing/v1/services/{serviceId}` | [Update Service](https://www.holded.com/developers/v1/invoice-api/services/update-service) |
| `v1_invoicing_UpdateTrackingInfo` | invoicing | POST | `/api/invoicing/v1/documents/{docType}/{documentId}/updatetracking` | [Update tracking info from specific document.](https://www.holded.com/developers/v1/invoice-api/documents/update-tracking-info) |
| `v1_invoicing_UpdateWarehouse` | invoicing | PUT | `/api/invoicing/v1/warehouses/{warehouseId}` | [Update Warehouse](https://www.holded.com/developers/v1/invoice-api/warehouses/update-warehouse) |
| `v1_projects_CreateProject` | projects | POST | `/api/projects/v1/projects` | [Create Project](https://www.holded.com/developers/v1/projects-api/projects/create-project) |
| `v1_projects_CreateProjectTime` | projects | POST | `/api/projects/v1/projects/{projectId}/times` | [Create Project Time](https://www.holded.com/developers/v1/projects-api/time-tracking/create-project-time) |
| `v1_projects_CreateTask` | projects | POST | `/api/projects/v1/tasks` | [Create Task](https://www.holded.com/developers/v1/projects-api/tasks/create-task) |
| `v1_projects_DeleteProject` | projects | DELETE | `/api/projects/v1/projects/{projectId}` | [Delete Project](https://www.holded.com/developers/v1/projects-api/projects/delete-project) |
| `v1_projects_DeleteProjectTime` | projects | DELETE | `/api/projects/v1/projects/{projectId}/times/{timeTrackingId}` | [Delete Project Time](https://www.holded.com/developers/v1/projects-api/time-tracking/delete-project-time) |
| `v1_projects_DeleteTask` | projects | DELETE | `/api/projects/v1/tasks/{taskId}` | [Delete Task](https://www.holded.com/developers/v1/projects-api/tasks/delete-task) |
| `v1_projects_GetProject` | projects | GET | `/api/projects/v1/projects/{projectId}` | [Get Project](https://www.holded.com/developers/v1/projects-api/projects/get-project) |
| `v1_projects_GetProjectSummary` | projects | GET | `/api/projects/v1/projects/{projectId}/summary` | [GetProjectSummary](https://www.holded.com/developers/v1/projects-api/projects/get-projects-projectid-summary) |
| `v1_projects_GetProjectTime` | projects | GET | `/api/projects/v1/projects/{projectId}/times/{timeTrackingId}` | [GetProjectTimes](https://www.holded.com/developers/v1/projects-api/time-tracking/getprojecttimes) |
| `v1_projects_GetProjectTimes` | projects | GET | `/api/projects/v1/projects/{projectId}/times` | [Get Project Times](https://www.holded.com/developers/v1/projects-api/time-tracking/get-project-times) |
| `v1_projects_GetTask` | projects | GET | `/api/projects/v1/tasks/{taskId}` | [Get Task](https://www.holded.com/developers/v1/projects-api/tasks/get-task) |
| `v1_projects_ListProjects` | projects | GET | `/api/projects/v1/projects` | [List Projects](https://www.holded.com/developers/v1/projects-api/projects/list-projects) |
| `v1_projects_ListTasks` | projects | GET | `/api/projects/v1/tasks` | [List Tasks](https://www.holded.com/developers/v1/projects-api/tasks/list-tasks) |
| `v1_projects_ListTimes` | projects | GET | `/api/projects/v1/projects/times` | [List Times](https://www.holded.com/developers/v1/projects-api/time-tracking/list-times) |
| `v1_projects_UpdateProject` | projects | PUT | `/api/projects/v1/projects/{projectId}` | [Update Project](https://www.holded.com/developers/v1/projects-api/projects/update-project) |
| `v1_projects_UpdateProjectTime` | projects | PUT | `/api/projects/v1/projects/{projectId}/times/{timeTrackingId}` | [Update Project Time](https://www.holded.com/developers/v1/projects-api/time-tracking/update-project-time) |
| `v1_team_CreateEmployee` | team | POST | `/api/team/v1/employees` | [Create a new employee](https://www.holded.com/developers/v1/team-api/employees/createemployee) |
| `v1_team_CreateEmployeeTime` | team | POST | `/api/team/v1/employees/{employeeId}/times` | [Create a time-tracking for an specific employee](https://www.holded.com/developers/v1/team-api/employees-time-tracking/createemployeetime) |
| `v1_team_DeleteEmployee` | team | DELETE | `/api/team/v1/employees/{employeeId}` | [Delete an Employee](https://www.holded.com/developers/v1/team-api/employees/delete-a-employee) |
| `v1_team_DeleteTime` | team | DELETE | `/api/team/v1/employees/times/{employeeTimeId}` | [Delete a time-tracking](https://www.holded.com/developers/v1/team-api/employees-time-tracking/deletetime) |
| `v1_team_EmployeeClockin` | team | POST | `/api/team/v1/employees/{employeeId}/times/clockin` | [Employee clock-in](https://www.holded.com/developers/v1/team-api/employees-time-tracking/employeeclockin) |
| `v1_team_EmployeeClockout` | team | POST | `/api/team/v1/employees/{employeeId}/times/clockout` | [Employee clock-out](https://www.holded.com/developers/v1/team-api/employees-time-tracking/employeeclockout) |
| `v1_team_EmployeePause` | team | POST | `/api/team/v1/employees/{employeeId}/times/pause` | [Employee time-tracking pause](https://www.holded.com/developers/v1/team-api/employees-time-tracking/employeepause) |
| `v1_team_EmployeeUnpause` | team | POST | `/api/team/v1/employees/{employeeId}/times/unpause` | [Employee time-tracking unpause](https://www.holded.com/developers/v1/team-api/employees-time-tracking/employeeunpause) |
| `v1_team_GetEmployee` | team | GET | `/api/team/v1/employees/{employeeId}` | [Get an Employee](https://www.holded.com/developers/v1/team-api/employees/get-a-employee) |
| `v1_team_GetTime` | team | GET | `/api/team/v1/employees/times/{employeeTimeId}` | [Get a specific time-tracking](https://www.holded.com/developers/v1/team-api/employees-time-tracking/gettime) |
| `v1_team_ListEmployeeTimes` | team | GET | `/api/team/v1/employees/{employeeId}/times` | [List all the time-trackings of a single employee](https://www.holded.com/developers/v1/team-api/employees-time-tracking/listemployeetimes) |
| `v1_team_ListEmployees` | team | GET | `/api/team/v1/employees` | [List all your employees](https://www.holded.com/developers/v1/team-api/employees/listemployees) |
| `v1_team_ListTimes` | team | GET | `/api/team/v1/employees/times` | [List all the time-trackings of all your employees](https://www.holded.com/developers/v1/team-api/employees-time-tracking/listtimes) |
| `v1_team_UpdateEmployee` | team | PUT | `/api/team/v1/employees/{employeeId}` | [Update an employee](https://www.holded.com/developers/v1/team-api/employees/update-employee) |
| `v1_team_UpdateTime` | team | PUT | `/api/team/v1/employees/times/{employeeTimeId}` | [Update a time-tracking](https://www.holded.com/developers/v1/team-api/employees-time-tracking/updatetime) |
