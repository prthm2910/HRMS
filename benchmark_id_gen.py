import os
import django
import time
import uuid
from django.db import transaction, IntegrityError

# 1. SETUP DJANGO ENVIRONMENT
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms.settings')
django.setup()

from apps.organization.models import Employee
from django.contrib.auth import get_user_model

User = get_user_model()

def benchmark():
    # Setup
    print("--- STARTING ID GENERATION BENCHMARK ---")
    
    iterations = 1000  # Reduced for speed, still enough to see the trend
    batch_id = uuid.uuid4().hex[:4]

    # ==========================================================================
    # APPROACH 1: LBA (Look Before You Leap) - Current Logic
    # ==========================================================================
    print(f"\nTesting LBA (Current 'exists()' check) for {iterations} iterations...")
    start_lba = time.perf_counter()
    
    created_users_lba = []
    
    for i in range(iterations):
        # Create a UNIQUE user for every employee (OneToOne restriction)
        u = User.objects.create(
            username=f"lba_{batch_id}_{i}", 
            email=f"lba_{batch_id}_{i}@test.com"
        )
        created_users_lba.append(u)
        
        success = False
        while not success:
            new_id = f"LBA{uuid.uuid4().hex[:6].upper()}"
            # THE "SLOW" PART: Database round-trip to check existence
            if not Employee.objects.filter(employee_id=new_id).exists():
                Employee.objects.create(
                    user=u, 
                    employee_id=new_id, 
                    date_of_joining="2024-01-01", 
                    salary=1000
                )
                success = True
    
    end_lba = time.perf_counter()
    lba_time = end_lba - start_lba
    print(f"LBA Total Time: {lba_time:.4f} seconds")

    # ==========================================================================
    # APPROACH 2: EAFP (Optimistic Saving) - Proposed Logic
    # ==========================================================================
    print(f"\nTesting EAFP (Optimistic 'try/except') for {iterations} iterations...")
    start_eafp = time.perf_counter()
    
    created_users_eafp = []

    for i in range(iterations):
        # Create a UNIQUE user for every employee (OneToOne restriction)
        u = User.objects.create(
            username=f"eafp_{batch_id}_{i}", 
            email=f"eafp_{batch_id}_{i}@test.com"
        )
        created_users_eafp.append(u)
        
        success = False
        while not success:
            new_id = f"EAF{uuid.uuid4().hex[:6].upper()}"
            try:
                # THE "FAST" PART: Just try to save once. DB handles the check.
                with transaction.atomic():
                    Employee.objects.create(
                        user=u, 
                        employee_id=new_id, 
                        date_of_joining="2024-01-01", 
                        salary=1000
                    )
                success = True
            except IntegrityError:
                continue

    end_eafp = time.perf_counter()
    eafp_time = end_eafp - start_eafp
    print(f"EAFP Total Time: {eafp_time:.4f} seconds")

    # ==========================================================================
    # RESULTS
    # ==========================================================================
    diff = ((lba_time - eafp_time) / lba_time) * 100
    print("\n--- FINAL RESULTS ---")
    if eafp_time < lba_time:
        print(f"EAFP is {diff:.2f}% FASTER than LBA.")
    else:
        print(f"LBA is {abs(diff):.2f}% FASTER than EAFP (unexpected).")

    # Cleanup
    print("\n--- Cleaning up test data... ---")
    User.objects.filter(username__contains=batch_id).delete()
    print("--- DONE ---")

if __name__ == "__main__":
    benchmark()
