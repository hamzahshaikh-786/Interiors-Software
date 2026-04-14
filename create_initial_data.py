import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interior_soft.settings')
django.setup()

from users.models import User

def create_users():
    # SuperAdmin
    if not User.objects.filter(username='superadmin').exists():
        User.objects.create_superuser('superadmin', 'superadmin@example.com', 'superpass123', role='superadmin')
        print("SuperAdmin user created")

    # Admin
    if not User.objects.filter(username='admin').exists():
        User.objects.create_user('admin', 'admin@example.com', 'admin123', role='admin')
        print("Admin user created")

    # Accountant
    if not User.objects.filter(username='accountant').exists():
        User.objects.create_user('accountant', 'accountant@example.com', 'pass123', role='accountant')
        print("Accountant user created")

    # Warehouse Manager
    if not User.objects.filter(username='warehouse').exists():
        User.objects.create_user('warehouse', 'warehouse@example.com', 'pass123', role='warehouse_manager')
        print("Warehouse Manager user created")

    # Delivery Person
    if not User.objects.filter(username='delivery').exists():
        User.objects.create_user('delivery', 'delivery@example.com', 'pass123', role='delivery_person')
        print("Delivery person user created")

    # Marketing Person
    if not User.objects.filter(username='marketing').exists():
        User.objects.create_user('marketing', 'marketing@example.com', 'pass123', role='marketing_person')
        print("Marketing person user created")

if __name__ == '__main__':
    create_users()
