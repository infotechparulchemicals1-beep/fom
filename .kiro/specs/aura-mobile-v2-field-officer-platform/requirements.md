# Requirements Document: AURA Mobile v2.0 Field Officer Execution Platform

## Introduction

AURA Mobile v2.0 is a major upgrade transforming the mobile application from a basic GPS tracking app into a comprehensive Field Officer Sales and Route Execution System. Built with React Native/Expo SDK 57 and SQLite 3 for offline-first data storage, the system syncs with AURA Cloud (Supabase PostgreSQL 15) and integrates with AURA Microservice Backend (FastAPI on fom-1.onrender.com).

The v2.0 platform enforces strict field officer workflows including mandatory route planning, comprehensive audit trails, offline-first operation, and real-time KPI tracking to maximize field sales effectiveness.

## Glossary

- **AURA_Mobile**: The React Native mobile application for field officers
- **Field_Officer**: User with field_officer role who executes daily sales routes
- **Route_Plan**: Daily schedule of retailer/distributor visits planned before fieldwork begins
- **Check_In**: GPS-stamped entry record when Field_Officer arrives at retailer location
- **Check_Out**: Exit record requiring photo proof and visit notes (minimum 10 characters)
- **Sales_Order**: Financial transaction record created during retailer visit
- **Payment_Receipt**: Cash/digital payment record collected from retailers
- **Entity_Edit_Log**: Audit record tracking all modifications to plans, orders, and payments
- **Follow_Up**: Auto-generated revisit task when Check_Out notes contain specific keywords
- **AURA_Cloud**: Supabase PostgreSQL 15 database serving as cloud data store
- **AURA_Backend**: FastAPI microservice backend hosted on fom-1.onrender.com
- **Bridge_API**: Backend endpoints consumed by PC-Sales website (Manager, HR, Caller modules)
- **Sync_Queue**: Ordered queue managing offline data synchronization with 5-step dependency resolution
- **KPI_Dashboard**: Performance metrics showing targets, achievements, shortfall, and effort
- **Stock_Requisition**: Request for inventory replenishment submitted by Field_Officer
- **Manager**: User with manager role who verifies and approves field officer activities
- **Session_Break**: Recorded pause in field activities (lunch, travel, emergency)
- **Discount_Tracker**: Real-time calculation of applied discounts against monthly limits
- **Products_Cache**: Offline replica of product catalog with pricing and stock data
- **PC_Sales**: Desktop web application used by Managers, HR, and Callers

## Requirements

### Requirement 1: Role Restriction and Application Lock

**User Story:** As a security administrator, I want the mobile app locked exclusively to field_officer role, so that unauthorized roles cannot access field operations.

#### Acceptance Criteria

1. THE AURA_Mobile SHALL restrict login to users with field_officer role only
2. WHEN a user with valid credentials and field_officer role attempts login, THE AURA_Mobile SHALL grant access
3. WHEN a user provides invalid credentials, THE AURA_Mobile SHALL reject login before performing role validation
4. IF a user has multiple roles including field_officer, THEN THE AURA_Mobile SHALL grant access
5. WHEN a user with valid credentials and caller role attempts login, THE AURA_Mobile SHALL display "Role not authorized for mobile app" message
6. WHEN a user with valid credentials and admin role attempts login, THE AURA_Mobile SHALL display "Role not authorized for mobile app" message
7. WHEN a user with valid credentials and manager role attempts login, THE AURA_Mobile SHALL display "Role not authorized for mobile app" message
8. WHEN a user with valid credentials and any role other than field_officer attempts login, THE AURA_Mobile SHALL reject access and terminate the login session
9. THE AURA_Mobile SHALL exclude all UI screens associated with caller role from the application build
10. THE AURA_Mobile SHALL exclude all UI screens associated with admin role from the application build
11. WHEN a login attempt is rejected due to unauthorized role, THE AURA_Mobile SHALL log the rejection with user_id, attempted role, and timestamp

### Requirement 2: Mandatory Daily Route Planning

**User Story:** As a field operations manager, I want field officers to plan their daily routes before starting fieldwork, so that visits are organized and accountable.

#### Acceptance Criteria

1. WHEN a Field_Officer launches AURA_Mobile without a submitted route plan for current date, THE AURA_Mobile SHALL display Route Planner screen
2. THE AURA_Mobile SHALL disable Check_In button and display lock icon until route plan is submitted for current date
3. WHEN a Field_Officer attempts to navigate to Check_In screen without submitted route plan, THE AURA_Mobile SHALL display modal message "Please submit your daily route plan first" and prevent navigation
4. THE Route_Plan SHALL contain minimum 1 entity and maximum 20 entities
5. FOR ALL entities in Route_Plan, THE Route_Plan SHALL assign unique planned_sequence_number from 1 to entity count
6. WHEN Route_Plan is submitted, THE AURA_Mobile SHALL save plan_submission_time with ISO 8601 format including seconds
7. WHEN Route_Plan is submitted, THE AURA_Mobile SHALL display confirmation message "Route plan submitted successfully" and enable Check_In button
8. WHILE AURA_Mobile is offline, THE AURA_Mobile SHALL allow Route_Plan creation and queue for sync when connectivity is restored
9. IF Route_Plan submission fails validation, THE AURA_Mobile SHALL display specific error message and prevent submission
10. WHEN network connectivity is restored after offline Route_Plan creation, THE AURA_Mobile SHALL retry sync with exponential backoff starting at 5 seconds for maximum 3 attempts

### Requirement 3: Route Plan Audit Trail

**User Story:** As a field operations manager, I want all route plan modifications logged with reasons, so that I can track planning discipline and changes.

#### Acceptance Criteria

1. IF Route_Plan status is submitted, WHEN a Field_Officer attempts to add an entity to Route_Plan, THEN THE AURA_Mobile SHALL display edit_reason input dialog
2. IF Route_Plan status is submitted, WHEN a Field_Officer attempts to remove an entity from Route_Plan, THEN THE AURA_Mobile SHALL display edit_reason input dialog
3. IF Route_Plan status is submitted, WHEN a Field_Officer attempts to reorder entities in Route_Plan, THEN THE AURA_Mobile SHALL display edit_reason input dialog
4. IF edit_reason contains fewer than 10 non-whitespace characters, THEN THE AURA_Mobile SHALL display error message indicating reason must be at least 10 characters and prevent modification
5. IF edit_reason contains 10 or more non-whitespace characters, WHEN Field_Officer confirms modification, THEN THE AURA_Mobile SHALL save edit_reason to Entity_Edit_Log with entity_type as route_plan_item before applying modification
6. THE Entity_Edit_Log SHALL capture field_officer_id, entity_id, action_type, edit_reason, and edit_timestamp for each entry
7. IF Entity_Edit_Log save fails, THEN THE AURA_Mobile SHALL cancel the modification and display error message indicating modification not saved
8. WHEN Field_Officer cancels edit_reason dialog, THE AURA_Mobile SHALL cancel the modification without creating Entity_Edit_Log entry
9. THE AURA_Mobile SHALL sync Entity_Edit_Log entries to AURA_Cloud during next successful sync

### Requirement 4: GPS-Stamped Check-In

**User Story:** As a field officer, I want to check in at retailer locations with GPS verification, so that my visits are accurately recorded.

#### Acceptance Criteria

1. WHEN a Field_Officer selects Check_In for a planned entity, THE AURA_Mobile SHALL capture GPS coordinates with latitude and longitude precise to 6 decimal places
2. WHEN a Field_Officer selects Check_In for a planned entity, THE AURA_Mobile SHALL save check_in_time with second precision
3. WHEN a Field_Officer selects Check_In for a planned entity, THE AURA_Mobile SHALL calculate distance_from_entity_location in meters
4. IF GPS accuracy is worse than 50 meters, THEN THE AURA_Mobile SHALL display error message indicating insufficient GPS accuracy and prevent check-in
5. IF GPS location is not acquired within 30 seconds of check-in attempt, THEN THE AURA_Mobile SHALL display error message indicating GPS timeout and prevent check-in
6. IF GPS permission is denied, THEN THE AURA_Mobile SHALL display error message indicating location permission required and prevent check-in
7. IF calculated distance_from_entity_location exceeds 500 meters, THEN THE AURA_Mobile SHALL display error message indicating user is too far from entity location and prevent check-in
8. WHILE AURA_Mobile is offline, THE AURA_Mobile SHALL allow Check_In and queue check-in data for sync
9. WHEN Field_Officer checks in to entity not in Route_Plan, THE AURA_Mobile SHALL auto-add entity to plan and display prompt requiring edit_reason with minimum 10 characters
10. IF Field_Officer does not provide edit_reason when prompted, THEN THE AURA_Mobile SHALL prevent completion of check-in
11. IF local storage save fails during check-in, THEN THE AURA_Mobile SHALL display error message indicating storage failure and retry save operation up to 3 times
12. WHEN network connectivity is restored, THE AURA_Mobile SHALL sync queued check-in data to AURA_Cloud

### Requirement 5: Mandatory Check-Out Validation

**User Story:** As a field operations manager, I want every check-out to include photo proof and visit notes, so that I can verify visit quality and outcomes.

#### Acceptance Criteria

1. WHEN a Field_Officer initiates Check_Out, THE AURA_Mobile SHALL require minimum 1 photo and maximum 10 photos
2. WHEN a Field_Officer initiates Check_Out, THE AURA_Mobile SHALL require visit_notes with minimum 10 non-whitespace characters and maximum 500 characters
3. IF photo count is zero, THEN THE AURA_Mobile SHALL disable Check_Out button and display error message "At least one photo is required"
4. IF photo count exceeds 10, THEN THE AURA_Mobile SHALL disable photo capture button and display message "Maximum 10 photos allowed"
5. IF visit_notes contain fewer than 10 non-whitespace characters, THEN THE AURA_Mobile SHALL disable Check_Out button and display error message "Notes must be at least 10 characters"
6. IF visit_notes exceed 500 characters, THEN THE AURA_Mobile SHALL prevent additional input and display character count indicator
7. IF no Check_In record exists for current Field_Officer, THEN THE AURA_Mobile SHALL prevent Check_Out and display error message "No active check-in found"
8. IF Field_Officer has already checked out from current entity, THEN THE AURA_Mobile SHALL prevent duplicate Check_Out and display error message "Already checked out from this location"
9. THE AURA_Mobile SHALL capture check_out_time with ISO 8601 format including seconds
10. THE AURA_Mobile SHALL calculate visit_duration_minutes as integer rounded difference between check_out_time and check_in_time divided by 60
11. THE AURA_Mobile SHALL compress each photo to maximum 500KB while preserving aspect ratio before storage
12. WHILE AURA_Mobile is offline, THE AURA_Mobile SHALL allow Check_Out and queue up to 50 check-out records with photos for sync
13. IF offline Check_Out queue exceeds 50 records, THEN THE AURA_Mobile SHALL display error message "Sync required before additional check-outs" and prevent check-out
14. IF camera permission is denied, THEN THE AURA_Mobile SHALL display error message "Camera permission required for check-out photos" and prevent photo capture

### Requirement 6: Follow-Up Auto-Injection

**User Story:** As a field operations manager, I want follow-up visits automatically created when check-out notes indicate unresolved issues, so that customer concerns are tracked.

#### Acceptance Criteria

1. WHEN visit_notes contain keyword "follow-up", THE AURA_Mobile SHALL create follow-up task for the entity
2. WHEN visit_notes contain keyword "revisit", THE AURA_Mobile SHALL create follow-up task for the entity
3. WHEN visit_notes contain keyword "pending", THE AURA_Mobile SHALL create follow-up task for the entity
4. THE follow-up task SHALL include entity_id, follow_up_reason extracted from visit_notes, and due_date set to 7 days from check_out_time
5. THE AURA_Mobile SHALL display notification "Follow-up task created for [entity_name]"
6. THE AURA_Mobile SHALL sync follow-up task to AURA_Cloud during next successful sync
7. THE AURA_Mobile SHALL display follow-up tasks in notifications screen with high priority indicator

### Requirement 7: Sales Order Creation and Editing

**User Story:** As a field officer, I want to create sales orders during visits with comprehensive product selection, so that I can record customer purchases.

#### Acceptance Criteria

1. IF Field_Officer has active Check_In record for an entity, THEN THE AURA_Mobile SHALL enable Sales_Order creation button
2. THE Sales_Order SHALL include order_date, entity_id, field_officer_id, and line_items array with minimum 1 line item
3. FOR ALL line items in Sales_Order, THE line item SHALL include product_id, quantity between 1 and 10000, and unit_price greater than 0
4. WHEN a Field_Officer adds product to Sales_Order, THE AURA_Mobile SHALL calculate line_total as quantity multiplied by unit_price rounded to 2 decimal places
5. THE AURA_Mobile SHALL calculate order_subtotal as sum of all line_total values rounded to 2 decimal places
6. WHEN a Field_Officer applies discount_percentage, THE AURA_Mobile SHALL validate discount_percentage is between 0 and 100
7. THE AURA_Mobile SHALL calculate discount_amount as order_subtotal multiplied by discount_percentage divided by 100 rounded to 2 decimal places
8. THE AURA_Mobile SHALL calculate order_total as order_subtotal minus discount_amount plus tax_amount rounded to 2 decimal places
9. IF quantity is not a positive integer between 1 and 10000, THEN THE AURA_Mobile SHALL display error message "Quantity must be between 1 and 10000" and prevent line item save
10. IF unit_price is not a positive decimal with maximum 2 decimal places, THEN THE AURA_Mobile SHALL display error message "Unit price must be positive with maximum 2 decimal places" and prevent line item save
11. WHILE AURA_Mobile is offline, THE AURA_Mobile SHALL allow Sales_Order creation and queue for sync
12. IF Field_Officer attempts to modify Sales_Order after initial save, THEN THE AURA_Mobile SHALL display edit_reason input dialog requiring minimum 10 non-whitespace characters
13. IF Field_Officer provides edit_reason with minimum 10 non-whitespace characters, THEN THE AURA_Mobile SHALL save edit_reason to Entity_Edit_Log with entity_type as sales_order before applying modification
14. IF Sales_Order save fails, THEN THE AURA_Mobile SHALL display error message "Failed to save sales order" and preserve entered data for retry
15. THE AURA_Mobile SHALL calculate real-time order_total and display updated value within 100 milliseconds of any line item or discount change

### Requirement 8: Real-Time Discount Tracking

**User Story:** As a field operations manager, I want real-time tracking of discounts against monthly limits, so that field officers stay within approved thresholds.

#### Acceptance Criteria

1. THE AURA_Mobile SHALL display current_month_discount_total on Performance Dashboard
2. THE AURA_Mobile SHALL display monthly_discount_limit from fo_monthly_targets table
3. THE AURA_Mobile SHALL calculate discount_remaining as monthly_discount_limit minus current_month_discount_total
4. WHEN discount_remaining falls below 10 percent of monthly_discount_limit, THE AURA_Mobile SHALL display warning "Approaching discount limit"
5. WHEN current_month_discount_total exceeds monthly_discount_limit, THE AURA_Mobile SHALL display error "Monthly discount limit exceeded"
6. THE AURA_Mobile SHALL update discount calculations after each Sales_Order save
7. THE AURA_Mobile SHALL fetch latest discount totals from AURA_Cloud during sync

### Requirement 9: Payment Receipt Recording

**User Story:** As a field officer, I want to record cash and digital payments from retailers, so that collections are tracked and reconciled.

#### Acceptance Criteria

1. WHEN a Field_Officer is checked in to an entity, THE AURA_Mobile SHALL enable Payment_Receipt creation
2. THE Payment_Receipt SHALL include payment_date, entity_id, field_officer_id, payment_amount, and payment_method
3. THE AURA_Mobile SHALL support payment_method values of cash, upi, card, and cheque
4. WHEN payment_method is cheque, THE AURA_Mobile SHALL require cheque_number and cheque_date fields
5. THE AURA_Mobile SHALL allow Payment_Receipt creation while offline with queued sync
6. WHEN a Field_Officer modifies Payment_Receipt after initial save, THE AURA_Mobile SHALL require edit_reason with minimum 10 characters
7. THE AURA_Mobile SHALL save edit_reason to Entity_Edit_Log with entity_type as payment_receipt
8. THE AURA_Mobile SHALL sync Payment_Receipt to AURA_Cloud during next successful sync

### Requirement 10: KPI Performance Dashboard

**User Story:** As a field officer, I want to see my monthly performance metrics in real-time, so that I can track progress toward targets.

#### Acceptance Criteria

1. THE Performance_Dashboard SHALL display monthly_sales_target from fo_monthly_targets table
2. THE Performance_Dashboard SHALL display current_month_sales_total calculated from Sales_Order records
3. THE Performance_Dashboard SHALL calculate sales_shortfall as monthly_sales_target minus current_month_sales_total
4. THE Performance_Dashboard SHALL display current_month_visit_count from check-in records
5. THE Performance_Dashboard SHALL display current_month_order_count from Sales_Order records
6. THE Performance_Dashboard SHALL display current_month_collection_total from Payment_Receipt records
7. THE Performance_Dashboard SHALL calculate conversion_rate as current_month_order_count divided by current_month_visit_count multiplied by 100
8. THE Performance_Dashboard SHALL refresh metrics after each Sales_Order, Payment_Receipt, or Check_Out save
9. THE Performance_Dashboard SHALL fetch latest targets from AURA_Cloud during sync

### Requirement 11: Offline-First Data Storage

**User Story:** As a field officer working in areas with poor connectivity, I want full app functionality while offline, so that I can complete my work without interruption.

#### Acceptance Criteria

1. THE AURA_Mobile SHALL store all Route_Plan data in local SQLite database
2. THE AURA_Mobile SHALL store all Check_In and Check_Out records in local SQLite database
3. THE AURA_Mobile SHALL store all Sales_Order records in local SQLite database
4. THE AURA_Mobile SHALL store all Payment_Receipt records in local SQLite database
5. THE AURA_Mobile SHALL store Products_Cache in local SQLite database
6. THE AURA_Mobile SHALL enable full read and write operations while offline
7. THE AURA_Mobile SHALL display offline indicator when network is unavailable
8. WHEN network becomes available, THE AURA_Mobile SHALL display online indicator

### Requirement 12: Ordered Sync Queue

**User Story:** As a system architect, I want offline changes synced in dependency order, so that data integrity is maintained during cloud synchronization.

#### Acceptance Criteria

1. THE Sync_Queue SHALL complete sync of fo_monthly_targets to AURA_Cloud before initiating sync of daily_route_plans
2. THE Sync_Queue SHALL complete sync of daily_route_plans to AURA_Cloud before initiating sync of route_plan_items
3. THE Sync_Queue SHALL complete sync of route_plan_items to AURA_Cloud before initiating sync of check-in records
4. THE Sync_Queue SHALL complete sync of check-in records to AURA_Cloud before initiating sync of Sales_Order and Payment_Receipt records
5. THE Sync_Queue SHALL complete sync of referenced entity before initiating sync of corresponding entity_edit_logs
6. IF sync operation fails, THEN THE Sync_Queue SHALL retry with exponential backoff at intervals of 5, 10, 20, 40, 80, 160, 320 seconds for maximum 3 attempts
7. IF network connectivity is lost during batch sync, THEN THE Sync_Queue SHALL cancel current batch and restart from beginning of batch when connectivity is restored
8. WHEN a sync operation fails 3 times, THE Sync_Queue SHALL log error with entity_id, entity_type, failure_reason, and timestamp to sync_error_log table
9. WHEN a sync operation fails 3 times, THE AURA_Mobile SHALL display notification "Sync failed for [entity_type] - contact support"
10. THE Sync_Queue SHALL preserve failed records in local SQLite database with failed_sync_attempts count until manual resolution
11. FOR ALL entities in Sync_Queue, THE Sync_Queue SHALL validate foreign key dependencies exist locally before initiating sync
12. IF foreign key dependency is missing for queued entity, THEN THE Sync_Queue SHALL move entity to failed_records with error "Missing dependency: [dependency_type]"

### Requirement 13: Products Cache Synchronization

**User Story:** As a field officer, I want access to current product catalog and pricing while offline, so that I can create accurate sales orders.

#### Acceptance Criteria

1. THE AURA_Mobile SHALL download complete products catalog from AURA_Backend during app launch when online
2. THE Products_Cache SHALL include product_id, product_name, unit_price, tax_rate, and is_active fields
3. THE Products_Cache SHALL update from AURA_Backend during background sync every 6 hours
4. WHEN Products_Cache is older than 24 hours, THE AURA_Mobile SHALL display warning "Product pricing may be outdated"
5. THE AURA_Mobile SHALL allow Sales_Order creation using cached product data while offline
6. THE AURA_Mobile SHALL sync Products_Cache updates with priority over transactional data
7. FOR ALL products in Products_Cache, THE AURA_Mobile SHALL validate is_active before allowing selection in Sales_Order

### Requirement 14: Stock Requisition Workflow

**User Story:** As a field officer, I want to request inventory replenishment from warehouse, so that I can fulfill customer orders.

#### Acceptance Criteria

1. THE AURA_Mobile SHALL enable Stock_Requisition creation from inventory screen
2. THE Stock_Requisition SHALL include field_officer_id, requisition_date, line items array, and request_notes
3. WHEN a Field_Officer adds product to Stock_Requisition, THE AURA_Mobile SHALL require requested_quantity greater than zero
4. THE Stock_Requisition SHALL have status values of pending, approved, and fulfilled
5. THE AURA_Mobile SHALL allow Stock_Requisition creation while offline with queued sync
6. THE AURA_Mobile SHALL sync Stock_Requisition to AURA_Backend during next successful sync
7. WHEN Manager approves Stock_Requisition via PC_Sales, THE AURA_Mobile SHALL receive status update during sync
8. THE AURA_Mobile SHALL display notification when Stock_Requisition status changes to approved or fulfilled

### Requirement 15: Session Break Tracking

**User Story:** As a field operations manager, I want field officers to log work pauses, so that I can understand field time utilization.

#### Acceptance Criteria

1. THE AURA_Mobile SHALL enable Session_Break recording from main menu
2. THE Session_Break SHALL include field_officer_id, break_start_time, break_end_time, and break_reason
3. THE AURA_Mobile SHALL support break_reason values of lunch, travel, emergency, and other
4. WHEN break_reason is other, THE AURA_Mobile SHALL require custom_reason field with minimum 5 characters
5. WHEN Field_Officer starts Session_Break, THE AURA_Mobile SHALL save break_start_time with second precision
6. WHEN Field_Officer ends Session_Break, THE AURA_Mobile SHALL save break_end_time with second precision
7. THE AURA_Mobile SHALL calculate break_duration_minutes as difference between break_end_time and break_start_time
8. THE AURA_Mobile SHALL sync Session_Break records to AURA_Cloud during next successful sync

### Requirement 16: Manager Verification Workflow

**User Story:** As a manager, I want to review and verify field officer activities through PC-Sales interface, so that I can ensure compliance and quality.

#### Acceptance Criteria

1. THE AURA_Backend SHALL expose Bridge_API endpoint GET /api/v1/field-activities for PC_Sales consumption
2. THE Bridge_API SHALL return check-in, check-out, sales orders, and payment receipts filtered by date range and field_officer_id
3. THE Bridge_API SHALL include visit photos and notes in check-out response payload
4. THE AURA_Backend SHALL expose Bridge_API endpoint POST /api/v1/verify-activity for Manager verification
5. WHEN Manager verifies activity via PC_Sales, THE AURA_Backend SHALL update verification_status to verified
6. WHEN Manager rejects activity via PC_Sales, THE AURA_Backend SHALL require rejection_reason with minimum 10 characters
7. THE AURA_Mobile SHALL sync verification_status updates during next successful sync
8. WHEN verification_status changes to verified, THE AURA_Mobile SHALL display notification "Activity verified by manager"
9. WHEN verification_status changes to rejected, THE AURA_Mobile SHALL display notification with rejection_reason

### Requirement 17: Bridge API for PC-Sales Integration

**User Story:** As a PC-Sales developer, I want well-documented REST APIs to fetch field officer data, so that Manager and HR modules function correctly.

#### Acceptance Criteria

1. THE AURA_Backend SHALL expose Bridge_API endpoint GET /api/v1/field-officers for retrieving field officer list
2. THE AURA_Backend SHALL expose Bridge_API endpoint GET /api/v1/route-plans for retrieving daily route plans
3. THE AURA_Backend SHALL expose Bridge_API endpoint GET /api/v1/sales-summary for retrieving aggregated sales metrics
4. THE AURA_Backend SHALL expose Bridge_API endpoint GET /api/v1/collection-summary for retrieving payment collection metrics
5. THE Bridge_API SHALL require authentication token in Authorization header
6. THE Bridge_API SHALL return HTTP 401 when authentication token is invalid or missing
7. THE Bridge_API SHALL return HTTP 403 when requesting user lacks manager or hr role
8. THE Bridge_API SHALL support pagination with page and page_size query parameters
9. THE Bridge_API SHALL return response time below 500 milliseconds for cached queries

### Requirement 18: Notification System

**User Story:** As a field officer, I want timely notifications about important events, so that I stay informed and responsive.

#### Acceptance Criteria

1. THE AURA_Mobile SHALL display notification when follow-up task is auto-created from check-out notes
2. THE AURA_Mobile SHALL display notification when Stock_Requisition status changes to approved or fulfilled
3. THE AURA_Mobile SHALL display notification when Manager verifies or rejects activity
4. THE AURA_Mobile SHALL display notification when monthly_sales_target is updated by Manager
5. THE AURA_Mobile SHALL display notification when discount_remaining falls below 10 percent threshold
6. THE AURA_Mobile SHALL store notifications in local SQLite database with read/unread status
7. THE AURA_Mobile SHALL display unread notification count badge on notifications icon
8. WHEN Field_Officer taps notification, THE AURA_Mobile SHALL navigate to relevant screen and mark notification as read

### Requirement 19: Data Validation and Integrity

**User Story:** As a system architect, I want comprehensive data validation at creation and modification, so that data quality is maintained.

#### Acceptance Criteria

1. WHEN a Field_Officer enters quantity in Sales_Order, THE AURA_Mobile SHALL validate quantity is positive integer
2. WHEN a Field_Officer enters unit_price in Sales_Order, THE AURA_Mobile SHALL validate unit_price is positive decimal with maximum 2 decimal places
3. WHEN a Field_Officer enters payment_amount in Payment_Receipt, THE AURA_Mobile SHALL validate payment_amount is positive decimal with maximum 2 decimal places
4. WHEN a Field_Officer selects payment_date in Payment_Receipt, THE AURA_Mobile SHALL validate payment_date is not future date
5. WHEN a Field_Officer enters discount_percentage in Sales_Order, THE AURA_Mobile SHALL validate discount_percentage is between 0 and 100
6. THE AURA_Mobile SHALL prevent saving entity with validation errors
7. THE AURA_Mobile SHALL display field-specific error messages below invalid input fields

### Requirement 20: Configuration Parser and Pretty Printer

**User Story:** As a system architect, I want robust parsing and serialization of configuration files, so that app settings are reliably loaded and saved.

#### Acceptance Criteria

1. WHEN AURA_Mobile loads configuration file from config/app_settings.json, THE Config_Parser SHALL parse JSON into Configuration object
2. IF configuration file contains invalid JSON syntax, THEN THE Config_Parser SHALL return error message "JSON parse error at line [line_number]: [error_description]"
3. IF configuration file is not readable due to permissions, THEN THE Config_Parser SHALL return error message "Configuration file not accessible: [file_path]"
4. THE Pretty_Printer SHALL format Configuration objects back into valid JSON with 2-space indentation and newline at end of file
5. FOR ALL valid Configuration objects C, IF C is parsed to object O1, THEN O1 is printed to string S, THEN S is parsed to object O2, THEN O1 SHALL equal O2 in all configuration key values
6. THE Config_Parser SHALL validate required configuration keys sync_interval_seconds, max_offline_days, and photo_max_size_kb are present
7. IF required configuration key is missing, THEN THE Config_Parser SHALL return error message "Missing required configuration: [key_name]"
8. THE Config_Parser SHALL validate sync_interval_seconds is integer between 30 and 3600
9. THE Config_Parser SHALL validate max_offline_days is integer between 1 and 30
10. THE Config_Parser SHALL validate photo_max_size_kb is integer between 100 and 2000
11. IF configuration value fails validation, THEN THE Config_Parser SHALL return error message "[key_name] must be [validation_rule]"
12. IF configuration file is missing or invalid, THEN THE AURA_Mobile SHALL use default configuration values: sync_interval_seconds=300, max_offline_days=7, photo_max_size_kb=500

### Requirement 21: Sync Conflict Resolution

**User Story:** As a system architect, I want automatic conflict resolution for sync operations, so that concurrent edits are handled gracefully.

#### Acceptance Criteria

1. WHEN AURA_Mobile syncs Sales_Order with cloud version modified after local version, THE Sync_Queue SHALL detect conflict based on updated_at timestamps
2. WHEN sync conflict occurs for Sales_Order, THE Sync_Queue SHALL use server-wins strategy and overwrite local version
3. WHEN sync conflict occurs for Route_Plan, THE Sync_Queue SHALL use server-wins strategy and overwrite local version
4. THE Sync_Queue SHALL preserve conflicted local version in conflict_log table with original_data and server_data
5. THE AURA_Mobile SHALL display notification "Sync conflict resolved - [entity_type] updated from server"
6. THE AURA_Mobile SHALL allow Field_Officer to view conflict_log from settings screen
7. WHEN Manager modifies entity via PC_Sales while Field_Officer has unsync'd changes, THE Sync_Queue SHALL log conflict and notify Field_Officer

### Requirement 22: Photo Storage and Compression

**User Story:** As a field officer with limited device storage, I want photos automatically compressed, so that storage space is optimized.

#### Acceptance Criteria

1. WHEN Field_Officer captures photo for Check_Out, THE AURA_Mobile SHALL compress photo to maximum 500KB file size
2. THE AURA_Mobile SHALL preserve photo aspect ratio during compression
3. THE AURA_Mobile SHALL save compressed photo to local file system with naming pattern checkin_[entity_id]_[timestamp].jpg
4. THE AURA_Mobile SHALL store photo file path in check-out record photo_paths array
5. THE AURA_Mobile SHALL upload photos to AURA_Cloud storage during sync
6. WHEN photo upload succeeds, THE AURA_Mobile SHALL update photo_sync_status to synced in local database
7. WHEN photo upload fails, THE AURA_Mobile SHALL retry during next sync cycle

### Requirement 23: Security and Authentication

**User Story:** As a security administrator, I want secure authentication and authorization, so that only authorized field officers access the system.

#### Acceptance Criteria

1. THE AURA_Mobile SHALL require user authentication before granting app access
2. THE AURA_Mobile SHALL use JWT token authentication with AURA_Backend
3. THE AURA_Mobile SHALL store authentication token securely using device secure storage
4. WHEN authentication token expires, THE AURA_Mobile SHALL prompt Field_Officer for re-authentication
5. THE AURA_Mobile SHALL include authentication token in Authorization header for all API requests
6. THE AURA_Mobile SHALL clear local database and secure storage when Field_Officer logs out
7. WHEN Field_Officer enters incorrect password 3 consecutive times, THE AURA_Mobile SHALL lock account for 15 minutes

### Requirement 24: Error Handling and Recovery

**User Story:** As a field officer, I want clear error messages and recovery options, so that I can resolve issues independently.

#### Acceptance Criteria

1. WHEN AURA_Backend returns HTTP 500 error, THE AURA_Mobile SHALL display "Server error - please try again later" message
2. WHEN AURA_Backend returns HTTP 404 error, THE AURA_Mobile SHALL display "Requested data not found" message
3. WHEN network request times out after 30 seconds, THE AURA_Mobile SHALL display "Request timed out - check your connection" message
4. WHEN SQLite database operation fails, THE AURA_Mobile SHALL log error details and display "Database error - please contact support" message
5. WHEN photo capture fails, THE AURA_Mobile SHALL display "Camera error - please try again" message with retry button
6. THE AURA_Mobile SHALL log all errors to local error_log table with timestamp, error_type, and error_message
7. THE AURA_Mobile SHALL provide "Send Error Logs" option in settings screen for support diagnostics

### Requirement 25: Performance and Responsiveness

**User Story:** As a field officer, I want fast app response times, so that I can efficiently complete my work.

#### Acceptance Criteria

1. THE AURA_Mobile SHALL display Route Planner screen within 500 milliseconds of app launch
2. THE AURA_Mobile SHALL complete Check_In save operation within 200 milliseconds
3. THE AURA_Mobile SHALL complete Sales_Order calculation and save within 300 milliseconds
4. THE AURA_Mobile SHALL load Performance_Dashboard metrics within 400 milliseconds
5. THE AURA_Mobile SHALL complete Products_Cache query within 100 milliseconds
6. THE AURA_Mobile SHALL display loading indicator for operations exceeding 200 milliseconds
7. THE AURA_Mobile SHALL maintain 60 frames per second UI rendering during list scrolling with 100 or more items
