import os
import django

# 1. SETUP DJANGO ENVIRONMENT
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def cleanup():
    # List of usernames we want to KEEP (from the provided image)
    usernames_to_keep = [
        'admin',
        'associate_developer@example.com',
        'benchmark user',
        'cto@example.com',
        'junior_developer@example.com'
    ]

    print(f"--- 🧹 Cleaning up User model ---")
    
    # Identify users to delete
    users_to_delete = User.objects.exclude(username__in=usernames_to_keep)
    count = users_to_delete.count()
    
    if count == 0:
        print("Everything is already clean! No extra users found.")
        return

    print(f"Found {count} users to delete. (Keeping: {', '.join(usernames_to_keep)})")
    
    # Perform the deletion
    # Note: This will also delete associated Employees due to on_delete=CASCADE
    users_to_delete.delete()
    
    print(f"Successfully deleted {count} redundant users.")
    print("--- 📚 DONE ---")

if __name__ == "__main__":
    cleanup()
