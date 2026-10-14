# API coverage

Official API snapshot: **2026-10-14**.

The bundled catalog exposes **136 operations** of the Holded v1 API: **72 invoicing**, **29 crm**, **16 projects**, **15 team**, **4 accounting**.

## Sources

Holded published the v1 reference with ReadMe (developers.holded.com). Each v1 API is an OpenAPI 3.0 document in ReadMe's API registry; the original ReadMe reference pages (Internet Archive captures up to 2026) identify them as `@holded/v1.0#<id>`:

- invoicing: [https://dash.readme.com/api/v1/api-registry/delc6k4mltcvjvk](https://dash.readme.com/api/v1/api-registry/delc6k4mltcvjvk)
- crm: [https://dash.readme.com/api/v1/api-registry/3avojom3x2i4gl](https://dash.readme.com/api/v1/api-registry/3avojom3x2i4gl)
- projects: [https://dash.readme.com/api/v1/api-registry/osa1dlwrwhirf](https://dash.readme.com/api/v1/api-registry/osa1dlwrwhirf)
- team: [https://dash.readme.com/api/v1/api-registry/apza3e5ummfnu54er](https://dash.readme.com/api/v1/api-registry/apza3e5ummfnu54er)
- accounting: [https://dash.readme.com/api/v1/api-registry/168v3gl2suxrvj](https://dash.readme.com/api/v1/api-registry/168v3gl2suxrvj)

Holded now serves the v1 reference as an archive at [https://www.holded.com/developers/v1](https://www.holded.com/developers/v1); every `doc_url` points there. At snapshot time the archive lists exactly the same 136 method/path pairs, parameters, body fields, types and required flags as these definitions (the archive renders only top-level body fields; nested schemas come from the definitions).

Holded labels v1 as deprecated/maintenance mode and documents a new v2 API (`https://api.holded.com/api/v2/...`, Bearer authentication, OpenAPI at `https://api.holded.com/openapi/api2.json`). v2 is **not** part of this catalog. Authentication for v1 uses the `key` header, which the client adds; header parameters are therefore excluded from the catalog.

Coverage means every HTTP operation in these definitions is callable. Holded plan limits, permissions and account features still apply. Response schemas are not bundled; responses are returned as received. Undocumented endpoints are not claimed as supported.

## Normalizations and limitations

- Operation IDs are `<api>_<Name>`, where `Name` is the source `operationId` (or `summary` when absent) converted to PascalCase (`List Contacts` -> `ListContacts`, `getDocument` -> `GetDocument`). Explicit overrides: `accounting_ListAccounts` (GET `/chartofaccounts`), `projects_GetProjectSummary` (GET `/projects/{projectId}/summary`), `projects_GetProjectTime` (GET `/projects/{projectId}/times/{timeTrackingId}`), `team_DeleteEmployee` (DELETE `/employees/{employeeId}`), `team_GetEmployee` (GET `/employees/{employeeId}`), `team_ListEmployeeTimes` (GET `/employees/{employeeId}/times`). They cover missing identifiers, a collision (`GetProjectTimes` is used for both the list and the single-entry operation in the source) and all-lowercase source names.
- Paths are full paths (`/api/<api>/v1/...`) built from each definition's server URL.
- Local `$ref`s are expanded (siblings retained). Recursive positions, if any appear in future definitions, are left unconstrained and marked with `x-holded-recursive-reference`.
- A schema declaring `properties` without `type` is normalized to `type: object`.
- Operation-level parameters override path-level parameters with the same name and location. Path parameters are always `required: true`. Header parameters are excluded (none are declared besides the `key` security scheme). Parameters without a schema default to `type: string`; parameters without a description get an empty one.
- `docType` path parameters carry an `enum`. Where the parameter's description lists its values (`should be one of: {...}`), that list is used (e.g. `{salesorder, waybill}` for tracking and pipeline updates, `{salesorder, order}` for shipped units). Where the source gives no description, the full list from the documents reference is applied: `invoice`, `salesreceipt`, `creditnote`, `salesorder`, `proform`, `waybill`, `estimate`, `purchase`, `purchaseorder`, `purchaserefund`.
- Query parameters whose description says `Options:` followed by backticked values get an `enum` (the documents `sort` parameter: `created-asc`, `created-desc`). Other value lists that the source describes only in prose (contact `type`, `taxOperation`, languages, carrier keys) are kept as descriptions, because the source does not present them as exhaustive.
- File uploads (`invoicing_AttachFile`) use `multipart/form-data` with `file: {"type": "string", "format": "binary"}` and an optional `setMain` boolean, as in the source.
- `body_required` and `required` flags are kept from the source. The source marks no request body as required, even where a body is needed in practice.
- Timestamps (`starttmp`, `endtmp`, `date`, `dueDate`, ...) are Unix timestamps; the source does not state the unit, but its examples use seconds (10 digits). The source types some as strings and some as integers, and this catalog keeps the source types. Exceptions: tracking `pickUpDate`/`deliveryDate` use `DD/MM/YYYY` strings and the CRM slots `day` uses `yyyy-mm-dd`.
- `invoicing_GetDocumentPDF` returns JSON `{"status": 1, "data": "<base64>"}` rather than a binary PDF (per the official response example).
- Pagination is only declared where the source declares it: a `page` query parameter on `accounting_ListDailyLedger`, `team_ListEmployees` and `team_ListTimes` (pages of up to 500 items). Other list operations declare no pagination inputs and none are added.

## Regenerate

```sh
uv sync --group dev
uv run python scripts/update_catalog.py --snapshot-date YYYY-MM-DD
```

For a reproducible offline rebuild, keep the five source documents and pass them:

```sh
uv run python scripts/update_catalog.py --snapshot-date YYYY-MM-DD \
  --invoicing invoicing.json --crm crm.json --projects projects.json \
  --team team.json --accounting accounting.json
```

Add `--verify-docs` to fetch every archive page and check that it documents the same method and path. If Holded republishes a definition under a new registry id, update `REGISTRY_IDS` in `scripts/update_catalog.py`. The generator rejects duplicate operation IDs, duplicate method/path pairs, unresolved references, missing or extra path parameters, unexpected servers and unsupported body content types before writing anything.

## Operations

| Operation ID | Method | Path | API reference |
| --- | --- | --- | --- |
| `accounting_CreateAccount` | POST | `/api/accounting/v1/account` | [Create a new accounting account](https://www.holded.com/developers/v1/accounting-api/chart-of-accounts/createaccount) |
| `accounting_CreateEntry` | POST | `/api/accounting/v1/entry` | [Create entry](https://www.holded.com/developers/v1/accounting-api/daily-ledger/createentry) |
| `accounting_ListAccounts` | GET | `/api/accounting/v1/chartofaccounts` | [List all your accounting accounts](https://www.holded.com/developers/v1/accounting-api/chart-of-accounts/listaccounts) |
| `accounting_ListDailyLedger` | GET | `/api/accounting/v1/dailyledger` | [List all your entries](https://www.holded.com/developers/v1/accounting-api/daily-ledger/listdailyledger) |
| `crm_CancelBooking` | DELETE | `/api/crm/v1/bookings/{bookingId}` | [Cancel Booking](https://www.holded.com/developers/v1/crm-api/bookings/cancel-booking) |
| `crm_CreateBooking` | POST | `/api/crm/v1/bookings` | [Create Booking](https://www.holded.com/developers/v1/crm-api/bookings/create-booking) |
| `crm_CreateEvent` | POST | `/api/crm/v1/events` | [Create Event](https://www.holded.com/developers/v1/crm-api/events/create-event) |
| `crm_CreateFunnel` | POST | `/api/crm/v1/funnels` | [Create Funnel](https://www.holded.com/developers/v1/crm-api/funnels/create-funnel) |
| `crm_CreateLead` | POST | `/api/crm/v1/leads` | [Create Lead](https://www.holded.com/developers/v1/crm-api/leads/create-lead) |
| `crm_CreateLeadNote` | POST | `/api/crm/v1/leads/{leadId}/notes` | [Create Lead Note](https://www.holded.com/developers/v1/crm-api/leads/create-lead-note) |
| `crm_CreateLeadTask` | POST | `/api/crm/v1/leads/{leadId}/tasks` | [Create Lead Task](https://www.holded.com/developers/v1/crm-api/leads/create-lead-task) |
| `crm_DeleteEvent` | DELETE | `/api/crm/v1/events/{eventId}` | [Delete Event](https://www.holded.com/developers/v1/crm-api/events/delete-event) |
| `crm_DeleteFunnel` | DELETE | `/api/crm/v1/funnels/{funnelId}` | [Delete Funnel](https://www.holded.com/developers/v1/crm-api/funnels/delete-funnel) |
| `crm_DeleteLead` | DELETE | `/api/crm/v1/leads/{leadId}` | [Delete Lead](https://www.holded.com/developers/v1/crm-api/leads/delete-lead) |
| `crm_DeleteLeadTask` | DELETE | `/api/crm/v1/leads/{leadId}/tasks` | [Delete Lead Task](https://www.holded.com/developers/v1/crm-api/leads/delete-lead-task) |
| `crm_GetAvailableSlotsForLocation` | GET | `/api/crm/v1/bookings/locations/{locationId}/slots` | [Get available slots for location](https://www.holded.com/developers/v1/crm-api/bookings/get-available-slots-for-location) |
| `crm_GetBooking` | GET | `/api/crm/v1/bookings/{bookingId}` | [Get Booking](https://www.holded.com/developers/v1/crm-api/bookings/get-booking) |
| `crm_GetEvent` | GET | `/api/crm/v1/events/{eventId}` | [Get Event](https://www.holded.com/developers/v1/crm-api/events/get-event) |
| `crm_GetFunnel` | GET | `/api/crm/v1/funnels/{funnelId}` | [Get Funnel](https://www.holded.com/developers/v1/crm-api/funnels/get-funnel) |
| `crm_GetLead` | GET | `/api/crm/v1/leads/{leadId}` | [Get Lead](https://www.holded.com/developers/v1/crm-api/leads/get-lead) |
| `crm_ListBookings` | GET | `/api/crm/v1/bookings` | [List Bookings](https://www.holded.com/developers/v1/crm-api/bookings/list-bookings) |
| `crm_ListEvents` | GET | `/api/crm/v1/events` | [List Events](https://www.holded.com/developers/v1/crm-api/events/list-events) |
| `crm_ListFunnels` | GET | `/api/crm/v1/funnels` | [List Funnels](https://www.holded.com/developers/v1/crm-api/funnels/list-funnels) |
| `crm_ListLeads` | GET | `/api/crm/v1/leads` | [List Leads](https://www.holded.com/developers/v1/crm-api/leads/list-leads) |
| `crm_ListLocations` | GET | `/api/crm/v1/bookings/locations` | [List Locations](https://www.holded.com/developers/v1/crm-api/bookings/list-locations) |
| `crm_UpdateBooking` | PUT | `/api/crm/v1/bookings/{bookingId}` | [Update Booking](https://www.holded.com/developers/v1/crm-api/bookings/update-booking) |
| `crm_UpdateEvent` | PUT | `/api/crm/v1/events/{eventId}` | [Update Event](https://www.holded.com/developers/v1/crm-api/events/update-event) |
| `crm_UpdateFunnel` | PUT | `/api/crm/v1/funnels/{funnelId}` | [Update Funnel](https://www.holded.com/developers/v1/crm-api/funnels/update-funnel) |
| `crm_UpdateLead` | PUT | `/api/crm/v1/leads/{leadId}` | [Update Lead](https://www.holded.com/developers/v1/crm-api/leads/update-lead) |
| `crm_UpdateLeadCreationDate` | PUT | `/api/crm/v1/leads/{leadId}/dates` | [Update Lead Creation Date](https://www.holded.com/developers/v1/crm-api/leads/update-lead-creation-date) |
| `crm_UpdateLeadNote` | PUT | `/api/crm/v1/leads/{leadId}/notes` | [Update Lead Note](https://www.holded.com/developers/v1/crm-api/leads/update-lead-note) |
| `crm_UpdateLeadStage` | PUT | `/api/crm/v1/leads/{leadId}/stages` | [Update Lead Stage](https://www.holded.com/developers/v1/crm-api/leads/update-lead-stage) |
| `crm_UpdateLeadTask` | PUT | `/api/crm/v1/leads/{leadId}/tasks` | [Update Lead Task](https://www.holded.com/developers/v1/crm-api/leads/update-lead-task) |
| `invoicing_AttachFile` | POST | `/api/invoicing/v1/documents/{docType}/{documentId}/attach` | [Attach File to a specific document](https://www.holded.com/developers/v1/invoice-api/documents/attach-file) |
| `invoicing_CreateContact` | POST | `/api/invoicing/v1/contacts` | [Create Contact](https://www.holded.com/developers/v1/invoice-api/contacts/create-contact) |
| `invoicing_CreateContactGroup` | POST | `/api/invoicing/v1/contacts/groups` | [Create Contact Group](https://www.holded.com/developers/v1/invoice-api/contact-groups/create-contact-group) |
| `invoicing_CreateDocument` | POST | `/api/invoicing/v1/documents/{docType}` | [Create Document](https://www.holded.com/developers/v1/invoice-api/documents/create-document) |
| `invoicing_CreateExpensesAccount` | POST | `/api/invoicing/v1/expensesaccounts` | [Create Expenses Account](https://www.holded.com/developers/v1/invoice-api/expenses-accounts/create-expenses-account) |
| `invoicing_CreateNumberingSerie` | POST | `/api/invoicing/v1/numberingseries/{type}` | [Create Numbering Serie](https://www.holded.com/developers/v1/invoice-api/numbering-series/create-numbering-serie) |
| `invoicing_CreatePayment` | POST | `/api/invoicing/v1/payments` | [Create Payment](https://www.holded.com/developers/v1/invoice-api/payments/create-payment) |
| `invoicing_CreateProduct` | POST | `/api/invoicing/v1/products` | [Create Product](https://www.holded.com/developers/v1/invoice-api/products/create-product) |
| `invoicing_CreateSalesChannel` | POST | `/api/invoicing/v1/saleschannels` | [Create Sales Channel](https://www.holded.com/developers/v1/invoice-api/sales-channels/create-sales-channel) |
| `invoicing_CreateService` | POST | `/api/invoicing/v1/services` | [Create Service](https://www.holded.com/developers/v1/invoice-api/services/create-service) |
| `invoicing_CreateTreasury` | POST | `/api/invoicing/v1/treasury` | [Create Treasury Account](https://www.holded.com/developers/v1/invoice-api/treasuries/create-treasury) |
| `invoicing_CreateWarehouse` | POST | `/api/invoicing/v1/warehouses` | [Create Warehouse](https://www.holded.com/developers/v1/invoice-api/warehouses/create-warehouse) |
| `invoicing_DeleteContact` | DELETE | `/api/invoicing/v1/contacts/{contactId}` | [Delete Contact](https://www.holded.com/developers/v1/invoice-api/contacts/delete-contact) |
| `invoicing_DeleteContactGroup` | DELETE | `/api/invoicing/v1/contacts/groups/{groupId}` | [Delete Contact Group](https://www.holded.com/developers/v1/invoice-api/contact-groups/delete-contact-group) |
| `invoicing_DeleteDocument` | DELETE | `/api/invoicing/v1/documents/{docType}/{documentId}` | [Delete Document](https://www.holded.com/developers/v1/invoice-api/documents/delete-document) |
| `invoicing_DeleteExpensesAccount` | DELETE | `/api/invoicing/v1/expensesaccounts/{expensesAccountId}` | [Delete Expenses Account](https://www.holded.com/developers/v1/invoice-api/expenses-accounts/delete-expenses-account) |
| `invoicing_DeleteNumberingSerie` | DELETE | `/api/invoicing/v1/numberingseries/{type}/{numberingSeriesId}` | [Delete Numbering Serie](https://www.holded.com/developers/v1/invoice-api/numbering-series/delete-numbering-serie) |
| `invoicing_DeletePayment` | DELETE | `/api/invoicing/v1/payments/{paymentId}` | [Delete Payment](https://www.holded.com/developers/v1/invoice-api/payments/delete-payment) |
| `invoicing_DeleteProduct` | DELETE | `/api/invoicing/v1/products/{productId}` | [Delete Product](https://www.holded.com/developers/v1/invoice-api/products/delete-product) |
| `invoicing_DeleteSalesChannel` | DELETE | `/api/invoicing/v1/saleschannels/{salesChannelId}` | [Delete Sales Channel](https://www.holded.com/developers/v1/invoice-api/sales-channels/delete-sales-channel) |
| `invoicing_DeleteService` | DELETE | `/api/invoicing/v1/services/{serviceId}` | [Delete Service](https://www.holded.com/developers/v1/invoice-api/services/delete-service) |
| `invoicing_DeleteWarehouse` | DELETE | `/api/invoicing/v1/warehouses/{warehouseId}` | [Delete Warehouse](https://www.holded.com/developers/v1/invoice-api/warehouses/delete-warehouse) |
| `invoicing_GetAttachment` | GET | `/api/invoicing/v1/contacts/{contactId}/attachments/get` | [Get attachment](https://www.holded.com/developers/v1/invoice-api/contacts/get-attachment) |
| `invoicing_GetAttachmentsList` | GET | `/api/invoicing/v1/contacts/{contactId}/attachments/list` | [Get contact attachments list](https://www.holded.com/developers/v1/invoice-api/contacts/get-attachments-list) |
| `invoicing_GetContact` | GET | `/api/invoicing/v1/contacts/{contactId}` | [Get Contact](https://www.holded.com/developers/v1/invoice-api/contacts/get-contact) |
| `invoicing_GetContactGroup` | GET | `/api/invoicing/v1/contacts/groups/{groupId}` | [Get Contact Group](https://www.holded.com/developers/v1/invoice-api/contact-groups/get-contact-group) |
| `invoicing_GetDocument` | GET | `/api/invoicing/v1/documents/{docType}/{documentId}` | [Get Document](https://www.holded.com/developers/v1/invoice-api/documents/getdocument) |
| `invoicing_GetDocumentPDF` | GET | `/api/invoicing/v1/documents/{docType}/{documentId}/pdf` | [Get Document PDF](https://www.holded.com/developers/v1/invoice-api/documents/getdocumentpdf) |
| `invoicing_GetExpensesAccount` | GET | `/api/invoicing/v1/expensesaccounts/{expensesAccountId}` | [Get Expenses Account](https://www.holded.com/developers/v1/invoice-api/expenses-accounts/get-expenses-account) |
| `invoicing_GetNumberingSeries` | GET | `/api/invoicing/v1/numberingseries/{type}` | [Get Numbering Series by Type](https://www.holded.com/developers/v1/invoice-api/numbering-series/get-numbering-series) |
| `invoicing_GetPayment` | GET | `/api/invoicing/v1/payments/{paymentId}` | [Get Payment](https://www.holded.com/developers/v1/invoice-api/payments/get-payment) |
| `invoicing_GetProduct` | GET | `/api/invoicing/v1/products/{productId}` | [Get  Product](https://www.holded.com/developers/v1/invoice-api/products/get-product) |
| `invoicing_GetProductImage` | GET | `/api/invoicing/v1/products/{productId}/image` | [Get Product Main Image](https://www.holded.com/developers/v1/invoice-api/products/get-product-image) |
| `invoicing_GetProductSecondaryImage` | GET | `/api/invoicing/v1/products/{productId}/image/{imageFileName}` | [Get Product Secondary Image](https://www.holded.com/developers/v1/invoice-api/products/get-product-secondary-image) |
| `invoicing_GetRemittance` | GET | `/api/invoicing/v1/remittances/{remittanceId}` | [Get Remittance](https://www.holded.com/developers/v1/invoice-api/remittances/get-remittance) |
| `invoicing_GetSalesChannel` | GET | `/api/invoicing/v1/saleschannels/{salesChannelId}` | [Get Sales Channel](https://www.holded.com/developers/v1/invoice-api/sales-channels/get-sales-channel) |
| `invoicing_GetService` | GET | `/api/invoicing/v1/services/{serviceId}` | [Get Service](https://www.holded.com/developers/v1/invoice-api/services/get-service) |
| `invoicing_GetTaxes` | GET | `/api/invoicing/v1/taxes` | [Get Taxes](https://www.holded.com/developers/v1/invoice-api/taxes/gettaxes) |
| `invoicing_GetTreasury` | GET | `/api/invoicing/v1/treasury/{treasuryId}` | [Get Treasury Account](https://www.holded.com/developers/v1/invoice-api/treasuries/get-treasury) |
| `invoicing_GetWarehouse` | GET | `/api/invoicing/v1/warehouses/{warehouseId}` | [Get Warehouse](https://www.holded.com/developers/v1/invoice-api/warehouses/get-warehouse) |
| `invoicing_ListContactGroups` | GET | `/api/invoicing/v1/contacts/groups` | [List Contact Groups](https://www.holded.com/developers/v1/invoice-api/contact-groups/list-contact-groups) |
| `invoicing_ListContacts` | GET | `/api/invoicing/v1/contacts` | [List Contacts](https://www.holded.com/developers/v1/invoice-api/contacts/list-contacts) |
| `invoicing_ListDocuments` | GET | `/api/invoicing/v1/documents/{docType}` | [List Documents](https://www.holded.com/developers/v1/invoice-api/documents/list-documents) |
| `invoicing_ListExpensesAccounts` | GET | `/api/invoicing/v1/expensesaccounts` | [List Expenses Accounts](https://www.holded.com/developers/v1/invoice-api/expenses-accounts/list-expenses-accounts) |
| `invoicing_ListPaymentMethods` | GET | `/api/invoicing/v1/paymentmethods` | [List Payment methods](https://www.holded.com/developers/v1/invoice-api/documents/list-payment-methods) |
| `invoicing_ListPayments` | GET | `/api/invoicing/v1/payments` | [List Payments](https://www.holded.com/developers/v1/invoice-api/payments/list-payments) |
| `invoicing_ListProductImages` | GET | `/api/invoicing/v1/products/{productId}/imagesList` | [List Product Images](https://www.holded.com/developers/v1/invoice-api/products/list-product-images) |
| `invoicing_ListProducts` | GET | `/api/invoicing/v1/products` | [List Products](https://www.holded.com/developers/v1/invoice-api/products/list-products) |
| `invoicing_ListProductsStock` | GET | `/api/invoicing/v1/warehouses/{warehouseId}/stock` | [List products stock](https://www.holded.com/developers/v1/invoice-api/warehouses/list-products-stock) |
| `invoicing_ListRemittances` | GET | `/api/invoicing/v1/remittances` | [List Remittances](https://www.holded.com/developers/v1/invoice-api/remittances/list-remittances) |
| `invoicing_ListSalesChannels` | GET | `/api/invoicing/v1/saleschannels` | [List Sales Channels](https://www.holded.com/developers/v1/invoice-api/sales-channels/list-sales-channels) |
| `invoicing_ListServices` | GET | `/api/invoicing/v1/services` | [List Services](https://www.holded.com/developers/v1/invoice-api/services/list-services) |
| `invoicing_ListTreasuries` | GET | `/api/invoicing/v1/treasury` | [List Treasuries Accounts](https://www.holded.com/developers/v1/invoice-api/treasuries/list-treasuries) |
| `invoicing_ListWarehouses` | GET | `/api/invoicing/v1/warehouses` | [List Warehouses](https://www.holded.com/developers/v1/invoice-api/warehouses/list-warehouses) |
| `invoicing_PayDocument` | POST | `/api/invoicing/v1/documents/{docType}/{documentId}/pay` | [Pay Document](https://www.holded.com/developers/v1/invoice-api/documents/pay-document) |
| `invoicing_SendDocument` | POST | `/api/invoicing/v1/documents/{docType}/{documentId}/send` | [Send Document](https://www.holded.com/developers/v1/invoice-api/documents/send-document) |
| `invoicing_ShipAllItems` | POST | `/api/invoicing/v1/documents/salesorder/{documentId}/shipall` | [Ship All Items](https://www.holded.com/developers/v1/invoice-api/documents/ship-all-items) |
| `invoicing_ShipItemsByLine` | POST | `/api/invoicing/v1/documents/salesorder/{documentId}/shipbylines` | [Ship items by line](https://www.holded.com/developers/v1/invoice-api/documents/ship-items-by-line) |
| `invoicing_ShippedUnitsByItem` | GET | `/api/invoicing/v1/documents/{docType}/{documentId}/shippeditems` | [Shipped units by item](https://www.holded.com/developers/v1/invoice-api/documents/shipped-units-by-item) |
| `invoicing_UpdateContact` | PUT | `/api/invoicing/v1/contacts/{contactId}` | [Update Contact](https://www.holded.com/developers/v1/invoice-api/contacts/update-contact) |
| `invoicing_UpdateContactGroup` | PUT | `/api/invoicing/v1/contacts/groups/{groupId}` | [Update Contact Group](https://www.holded.com/developers/v1/invoice-api/contact-groups/update-contact-group) |
| `invoicing_UpdateDocument` | PUT | `/api/invoicing/v1/documents/{docType}/{documentId}` | [Update Document](https://www.holded.com/developers/v1/invoice-api/documents/update-document) |
| `invoicing_UpdateDocumentPipeline` | POST | `/api/invoicing/v1/documents/{docType}/{documentId}/pipeline/set` | [Update pipeline from specific document.](https://www.holded.com/developers/v1/invoice-api/documents/update-document-pipeline) |
| `invoicing_UpdateExpensesAccount` | PUT | `/api/invoicing/v1/expensesaccounts/{expensesAccountId}` | [Update Expenses Account](https://www.holded.com/developers/v1/invoice-api/expenses-accounts/update-expenses-account) |
| `invoicing_UpdateNumberingSerie` | PUT | `/api/invoicing/v1/numberingseries/{type}/{numberingSeriesId}` | [Update Numbering Serie](https://www.holded.com/developers/v1/invoice-api/numbering-series/update-numbering-serie) |
| `invoicing_UpdatePayment` | PUT | `/api/invoicing/v1/payments/{paymentId}` | [Update Payment](https://www.holded.com/developers/v1/invoice-api/payments/update-payment) |
| `invoicing_UpdateProduct` | PUT | `/api/invoicing/v1/products/{productId}` | [Update Product](https://www.holded.com/developers/v1/invoice-api/products/update-product) |
| `invoicing_UpdateProductStock` | PUT | `/api/invoicing/v1/products/{productId}/stock` | [Update Product stock](https://www.holded.com/developers/v1/invoice-api/products/update-product-stock) |
| `invoicing_UpdateSalesChannel` | PUT | `/api/invoicing/v1/saleschannels/{salesChannelId}` | [Update Sales Channel](https://www.holded.com/developers/v1/invoice-api/sales-channels/update-sales-channel) |
| `invoicing_UpdateService` | PUT | `/api/invoicing/v1/services/{serviceId}` | [Update Service](https://www.holded.com/developers/v1/invoice-api/services/update-service) |
| `invoicing_UpdateTrackingInfo` | POST | `/api/invoicing/v1/documents/{docType}/{documentId}/updatetracking` | [Update tracking info from specific document.](https://www.holded.com/developers/v1/invoice-api/documents/update-tracking-info) |
| `invoicing_UpdateWarehouse` | PUT | `/api/invoicing/v1/warehouses/{warehouseId}` | [Update Warehouse](https://www.holded.com/developers/v1/invoice-api/warehouses/update-warehouse) |
| `projects_CreateProject` | POST | `/api/projects/v1/projects` | [Create Project](https://www.holded.com/developers/v1/projects-api/projects/create-project) |
| `projects_CreateProjectTime` | POST | `/api/projects/v1/projects/{projectId}/times` | [Create Project Time](https://www.holded.com/developers/v1/projects-api/time-tracking/create-project-time) |
| `projects_CreateTask` | POST | `/api/projects/v1/tasks` | [Create Task](https://www.holded.com/developers/v1/projects-api/tasks/create-task) |
| `projects_DeleteProject` | DELETE | `/api/projects/v1/projects/{projectId}` | [Delete Project](https://www.holded.com/developers/v1/projects-api/projects/delete-project) |
| `projects_DeleteProjectTime` | DELETE | `/api/projects/v1/projects/{projectId}/times/{timeTrackingId}` | [Delete Project Time](https://www.holded.com/developers/v1/projects-api/time-tracking/delete-project-time) |
| `projects_DeleteTask` | DELETE | `/api/projects/v1/tasks/{taskId}` | [Delete Task](https://www.holded.com/developers/v1/projects-api/tasks/delete-task) |
| `projects_GetProject` | GET | `/api/projects/v1/projects/{projectId}` | [Get Project](https://www.holded.com/developers/v1/projects-api/projects/get-project) |
| `projects_GetProjectSummary` | GET | `/api/projects/v1/projects/{projectId}/summary` | [GetProjectSummary](https://www.holded.com/developers/v1/projects-api/projects/get-projects-projectid-summary) |
| `projects_GetProjectTime` | GET | `/api/projects/v1/projects/{projectId}/times/{timeTrackingId}` | [GetProjectTimes](https://www.holded.com/developers/v1/projects-api/time-tracking/getprojecttimes) |
| `projects_GetProjectTimes` | GET | `/api/projects/v1/projects/{projectId}/times` | [Get Project Times](https://www.holded.com/developers/v1/projects-api/time-tracking/get-project-times) |
| `projects_GetTask` | GET | `/api/projects/v1/tasks/{taskId}` | [Get Task](https://www.holded.com/developers/v1/projects-api/tasks/get-task) |
| `projects_ListProjects` | GET | `/api/projects/v1/projects` | [List Projects](https://www.holded.com/developers/v1/projects-api/projects/list-projects) |
| `projects_ListTasks` | GET | `/api/projects/v1/tasks` | [List Tasks](https://www.holded.com/developers/v1/projects-api/tasks/list-tasks) |
| `projects_ListTimes` | GET | `/api/projects/v1/projects/times` | [List Times](https://www.holded.com/developers/v1/projects-api/time-tracking/list-times) |
| `projects_UpdateProject` | PUT | `/api/projects/v1/projects/{projectId}` | [Update Project](https://www.holded.com/developers/v1/projects-api/projects/update-project) |
| `projects_UpdateProjectTime` | PUT | `/api/projects/v1/projects/{projectId}/times/{timeTrackingId}` | [Update Project Time](https://www.holded.com/developers/v1/projects-api/time-tracking/update-project-time) |
| `team_CreateEmployee` | POST | `/api/team/v1/employees` | [Create a new employee](https://www.holded.com/developers/v1/team-api/employees/createemployee) |
| `team_CreateEmployeeTime` | POST | `/api/team/v1/employees/{employeeId}/times` | [Create a time-tracking for an specific employee](https://www.holded.com/developers/v1/team-api/employees-time-tracking/createemployeetime) |
| `team_DeleteEmployee` | DELETE | `/api/team/v1/employees/{employeeId}` | [Delete an Employee](https://www.holded.com/developers/v1/team-api/employees/delete-a-employee) |
| `team_DeleteTime` | DELETE | `/api/team/v1/employees/times/{employeeTimeId}` | [Delete a time-tracking](https://www.holded.com/developers/v1/team-api/employees-time-tracking/deletetime) |
| `team_EmployeeClockin` | POST | `/api/team/v1/employees/{employeeId}/times/clockin` | [Employee clock-in](https://www.holded.com/developers/v1/team-api/employees-time-tracking/employeeclockin) |
| `team_EmployeeClockout` | POST | `/api/team/v1/employees/{employeeId}/times/clockout` | [Employee clock-out](https://www.holded.com/developers/v1/team-api/employees-time-tracking/employeeclockout) |
| `team_EmployeePause` | POST | `/api/team/v1/employees/{employeeId}/times/pause` | [Employee time-tracking pause](https://www.holded.com/developers/v1/team-api/employees-time-tracking/employeepause) |
| `team_EmployeeUnpause` | POST | `/api/team/v1/employees/{employeeId}/times/unpause` | [Employee time-tracking unpause](https://www.holded.com/developers/v1/team-api/employees-time-tracking/employeeunpause) |
| `team_GetEmployee` | GET | `/api/team/v1/employees/{employeeId}` | [Get an Employee](https://www.holded.com/developers/v1/team-api/employees/get-a-employee) |
| `team_GetTime` | GET | `/api/team/v1/employees/times/{employeeTimeId}` | [Get a specific time-tracking](https://www.holded.com/developers/v1/team-api/employees-time-tracking/gettime) |
| `team_ListEmployeeTimes` | GET | `/api/team/v1/employees/{employeeId}/times` | [List all the time-trackings of a single employee](https://www.holded.com/developers/v1/team-api/employees-time-tracking/listemployeetimes) |
| `team_ListEmployees` | GET | `/api/team/v1/employees` | [List all your employees](https://www.holded.com/developers/v1/team-api/employees/listemployees) |
| `team_ListTimes` | GET | `/api/team/v1/employees/times` | [List all the time-trackings of all your employees](https://www.holded.com/developers/v1/team-api/employees-time-tracking/listtimes) |
| `team_UpdateEmployee` | PUT | `/api/team/v1/employees/{employeeId}` | [Update an employee](https://www.holded.com/developers/v1/team-api/employees/update-employee) |
| `team_UpdateTime` | PUT | `/api/team/v1/employees/times/{employeeTimeId}` | [Update a time-tracking](https://www.holded.com/developers/v1/team-api/employees-time-tracking/updatetime) |
