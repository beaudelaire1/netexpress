# Requirements Document - NetExpress v2 Transformation

## Introduction

NetExpress v2 represents a complete transformation from a traditional back-office admin system to a modern collaborative multi-portal platform. The system will serve three distinct user types (Clients, Workers, and Administrators) with role-specific dashboards, integrated WYSIWYG messaging, and mobile-first design for field workers.

## Glossary

- **Client_Portal**: Web interface accessible to clients for viewing their documents and communicating with the company
- **Worker_Portal**: Mobile-optimized interface for field workers to manage their assigned tasks and schedules
- **Admin_Portal**: Comprehensive management interface for administrators with global KPIs and validation controls
- **WYSIWYG_Editor**: What You See Is What You Get rich text editor for professional communication
- **Task_Assignment**: System for assigning specific work tasks to individual workers
- **Document_Validation**: Process of approving and finalizing quotes and invoices
- **Auto_Account_Creation**: Automatic client account generation upon quote validation

## Requirements

### Requirement 1: Multi-Portal Architecture

**User Story:** As a business owner, I want separate portals for different user types, so that each user sees only relevant information and functionality.

#### Acceptance Criteria

1. THE System SHALL provide three distinct portal interfaces: Client_Portal, Worker_Portal, and Admin_Portal
2. WHEN a user logs in, THE System SHALL redirect them to their appropriate portal based on their role
3. THE System SHALL prevent cross-portal access through URL manipulation or direct navigation
4. WHEN a Worker attempts to access Admin_Portal URLs, THE System SHALL deny access and redirect to Worker_Portal
5. WHEN a Client attempts to access Worker_Portal or Admin_Portal URLs, THE System SHALL deny access and redirect to Client_Portal

### Requirement 2: Client Portal Functionality

**User Story:** As a client, I want to access my documents and communicate with the company, so that I can manage my business relationship efficiently.

#### Acceptance Criteria

1. WHEN a client logs into Client_Portal, THE System SHALL display their latest documents (pending quotes and unpaid invoices)
2. THE Client_Portal SHALL show historical interventions (past and future scheduled)
3. THE Client_Portal SHALL provide a messaging interface to contact the company directly
4. WHEN displaying client documents, THE System SHALL filter to show only documents belonging to the authenticated client
5. THE Client_Portal SHALL be responsive and functional on mobile devices

### Requirement 3: Worker Portal Functionality

**User Story:** As a field worker, I want to view my assigned tasks and schedule, so that I can efficiently manage my daily work.

#### Acceptance Criteria

1. WHEN a worker logs into Worker_Portal, THE System SHALL display only tasks assigned to that worker
2. THE Worker_Portal SHALL provide a calendar view showing daily and weekly schedules
3. THE Worker_Portal SHALL display intervention details including client address and contact information
4. WHEN a worker completes a task, THE System SHALL provide a "Mark as Complete" button that triggers invoice notification
5. THE Worker_Portal SHALL be optimized for mobile devices with touch-friendly interfaces

### Requirement 4: Admin Portal Functionality

**User Story:** As an administrator, I want comprehensive oversight and control, so that I can manage the entire business operation.

#### Acceptance Criteria

1. THE Admin_Portal SHALL display global KPIs including revenue and performance metrics
2. THE Admin_Portal SHALL provide a global planning view showing all workers and tasks
3. THE Admin_Portal SHALL enable final validation of all documents (quotes and invoices)
4. WHEN viewing the global planning, THE System SHALL show task assignments across all workers
5. THE Admin_Portal SHALL maintain all existing administrative functions

### Requirement 5: WYSIWYG Messaging System

**User Story:** As a user, I want to create professionally formatted messages, so that communication appears polished and clear.

#### Acceptance Criteria

1. THE System SHALL integrate CKEditor for rich text editing in all messaging interfaces
2. WHEN composing messages, THE System SHALL provide formatting options (bold, lists, links)
3. THE WYSIWYG_Editor SHALL show exactly what the recipient will receive
4. THE System SHALL use WYSIWYG_Editor for email composition, quote notes, and internal messages
5. THE System SHALL preserve message formatting when displaying to recipients

### Requirement 6: Authentication and Role Management

**User Story:** As a system administrator, I want secure role-based access control, so that users can only access appropriate functionality.

#### Acceptance Criteria

1. THE System SHALL use Django's native Groups and Permissions system for role management
2. THE System SHALL create two primary groups: "Clients" and "Workers"
3. WHEN a quote is validated, THE System SHALL automatically create a client account if one doesn't exist
4. WHEN creating a client account automatically, THE System SHALL send an email invitation to set password
5. THE System SHALL allow manual creation of worker accounts by administrators only

### Requirement 7: Mobile-First Design

**User Story:** As a field worker, I want the system to work perfectly on my mobile device, so that I can use it effectively on job sites.

#### Acceptance Criteria

1. THE Worker_Portal SHALL be optimized for mobile devices as the primary interface
2. THE System SHALL use TailwindCSS for responsive design across all portals
3. WHEN accessing on mobile devices, THE System SHALL provide touch-friendly buttons and navigation
4. THE System SHALL ensure all critical worker functions are accessible on small screens
5. THE System SHALL maintain readability and usability across different screen sizes

### Requirement 8: Enhanced User Experience

**User Story:** As any user, I want a modern and responsive interface, so that the system feels contemporary and efficient.

#### Acceptance Criteria

1. THE System SHALL integrate HTMX for dynamic content updates without full page reloads
2. THE System SHALL implement UI notifications (visual indicators) for important updates
3. WHEN data changes occur, THE System SHALL update relevant interface sections dynamically
4. THE System SHALL provide email notifications for critical events (task completion, document validation)
5. THE System SHALL maintain fast response times through optimized database queries

### Requirement 9: Electronic Signature Preservation

**User Story:** As a business owner, I want to maintain electronic signature capability, so that quotes can be validated without paper processes.

#### Acceptance Criteria

1. THE System SHALL preserve existing electronic signature functionality for quotes
2. WHEN a quote is electronically signed, THE System SHALL automatically generate a PDF document
3. THE System SHALL maintain the signature validation workflow without disruption
4. THE System SHALL ensure signed documents are legally compliant and tamper-evident
5. THE System SHALL integrate signature workflow with the new portal architecture

### Requirement 10: Data Migration and Compatibility

**User Story:** As a business owner, I want seamless transition from the current system, so that no data or functionality is lost.

#### Acceptance Criteria

1. THE System SHALL migrate all existing data without loss during the transformation
2. THE System SHALL maintain compatibility with existing database schema where possible
3. THE System SHALL provide migration scripts for any necessary data structure changes
4. WHEN migrating user accounts, THE System SHALL preserve existing login credentials
5. THE System SHALL ensure all existing documents and relationships remain accessible