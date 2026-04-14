# Interior Soft - Cloth Wholesaler ERP

A production-ready, scalable web application for interior cloth wholesalers, built with Django.

## Features
- **Role-Based Access Control (RBAC)**: SuperAdmin, Admin, Accountant, Warehouse Manager, Delivery Person, Marketing Person.
- **Workflow-Driven Design**: Integrated Purchase Entry -> Sales Order -> Cutting -> Dispatch -> Delivery -> Payment workflow.
- **Hierarchical Inventory**: Organized Collections and Design Types with nested selection.
- **Ledger & Analytics**: Comprehensive transaction tracking, financial dashboards, and inactive customer insights.
- **Document Generation**: Automatic PDF generation for Delivery Challans and Invoices.
- **User Management**: Centralized control under SuperAdmin for creating and managing all system users.
- **Master Data**: Reusable master lists for Parties, Purchasers, and Product Designs.
- **Communication**: Integrated WhatsApp reminders and customer re-engagement tools.

## User Roles & Access
- **SuperAdmin**: System-wide control, user management, and database operations.
- **Admin**: Full operational visibility and control over all modules.
- **Accountant**: Order creation, delivery challan generation, purchase approval, and ledger visibility.
- **Warehouse Manager**: Purchase entry creation, cutting task execution, and dispatch readiness.
- **Delivery Person**: Assigned delivery tracking, challan access, and payment recording.
- **Marketing Person**: Read-only access to parties and inactive customer re-engagement.

## Installation

1. Clone the repository.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations:
   ```bash
   python manage.py migrate
   ```
5. Create initial users (SuperAdmin, Admin, Accountant, etc.):
   ```bash
   python create_initial_data.py
   ```
6. Start the development server:
   ```bash
   python manage.py runserver
   ```

## Default Credentials (Initial Setup)
- **SuperAdmin**: `superadmin / superpass123`
- **Admin**: `admin / admin123`
- **Accountant**: `accountant / pass123`
- **Warehouse Manager**: `warehouse / pass123`
- **Delivery Person**: `delivery / pass123`
- **Marketing Person**: `marketing / pass123`

## License
MIT
