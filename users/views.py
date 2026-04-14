from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.contrib import messages
import subprocess
import os
from django.conf import settings
from django.http import HttpResponse

User = get_user_model()

def is_superadmin(user):
    return user.is_authenticated and user.is_superadmin()

@login_required
@user_passes_test(is_superadmin)
def user_list(request):
    users = User.objects.all().order_by('username')
    return render(request, 'users/user_list.html', {'users': users})

@login_required
@user_passes_test(is_superadmin)
def user_create(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')
        is_active = request.POST.get('is_active') == 'on'
        
        user = User.objects.create_user(
            username=username, 
            email=email, 
            password=password, 
            role=role,
            is_active=is_active
        )
        messages.success(request, f"User {username} created successfully")
        return redirect('user_list')
    
    return render(request, 'users/user_form.html', {'roles': User.ROLE_CHOICES})

@login_required
@user_passes_test(is_superadmin)
def user_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.role = request.POST.get('role')
        user.is_active = request.POST.get('is_active') == 'on'
        password = request.POST.get('password')
        if password:
            user.set_password(password)
        user.save()
        messages.success(request, f"User {user.username} updated successfully")
        return redirect('user_list')
    
    return render(request, 'users/user_form.html', {
        'edit_user': user,
        'roles': User.ROLE_CHOICES
    })

@login_required
@user_passes_test(is_superadmin)
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You cannot delete yourself")
    else:
        username = user.username
        user.delete()
        messages.success(request, f"User {username} deleted successfully")
    return redirect('user_list')

# Backup and Restore
@login_required
@user_passes_test(is_superadmin)
def backup_database(request):
    db_config = settings.DATABASES['default']
    db_engine = db_config['ENGINE']
    
    if 'sqlite3' in db_engine:
        db_path = db_config['NAME']
        backup_path = os.path.join(settings.BASE_DIR, 'db_backup.sqlite3')
        try:
            if os.name == 'nt': # Windows
                subprocess.run(['copy', db_path, backup_path], shell=True, check=True)
            else:
                subprocess.run(['cp', db_path, backup_path], check=True)
            messages.success(request, f"SQLite database backup created successfully as '{backup_path}'")
        except Exception as e:
            messages.error(request, f"Backup failed: {str(e)}")
    else:
        # For PostgreSQL/MySQL, this requires external tools like pg_dump/mysqldump
        messages.warning(request, "Database backup for non-SQLite databases is not yet implemented via UI. Please use standard database backup tools (e.g., pg_dump for PostgreSQL).")
        
    return redirect('user_list')

@login_required
@user_passes_test(is_superadmin)
def restore_database(request):
    db_path = settings.DATABASES['default']['NAME']
    backup_path = os.path.join(settings.BASE_DIR, 'db_backup.sqlite3')
    
    if not os.path.exists(backup_path):
        messages.error(request, "No backup file found")
        return redirect('dashboard')
        
    try:
        if os.name == 'nt': # Windows
            subprocess.run(['copy', backup_path, db_path], shell=True, check=True)
        else:
            subprocess.run(['cp', backup_path, db_path], check=True)
        
        messages.success(request, "Database restored successfully. Please restart the server if needed.")
    except Exception as e:
        messages.error(request, f"Restore failed: {str(e)}")
        
    return redirect('dashboard')
