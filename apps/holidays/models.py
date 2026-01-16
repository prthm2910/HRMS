from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.base.models import BaseTemplateModel
import uuid
from datetime import date, timedelta


class Holiday(BaseTemplateModel):
    """
    Represents company holidays that are excluded from leave calculations.
    Supports recurring holidays (auto-generates future years) and regional holidays.
    """
    
    date = models.DateField(
        help_text="The date of the holiday"
    )
    name = models.CharField(
        max_length=200,
        help_text="Name of the holiday (e.g., 'Republic Day', 'Diwali')"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description or additional details about the holiday"
    )
    is_recurring = models.BooleanField(
        default=False,
        help_text="If True, this holiday repeats yearly (auto-generates next 5 years)"
    )
    recurring_group_id = models.UUIDField(
        null=True,
        blank=True,
        editable=False,
        help_text="Links related recurring holidays together"
    )
    region = models.CharField(
        max_length=100,
        blank=True,
        help_text="Region/location for this holiday (e.g., 'Mumbai', 'All India'). Leave blank for company-wide."
    )
    is_working_day = models.BooleanField(
        default=False,
        help_text="Override: Mark a weekend day as a working day (e.g., compensatory Saturday)"
    )

    class Meta:
        verbose_name = "Holiday"
        verbose_name_plural = "Holidays"
        db_table = 'holidays'
        ordering = ['date']
        # Prevent duplicate holidays on the same date for the same region
        unique_together = [['date', 'region']]
        indexes = [
            models.Index(fields=['date', 'is_active', 'is_deleted']),
            models.Index(fields=['recurring_group_id']),
        ]

    def clean(self):
        """Validation logic"""
        # Validate name length
        if self.name and len(self.name.strip()) < 3:
            raise ValidationError(_("Holiday name must be at least 3 characters long."))
        
        # Validate that new holidays are not in the past (only for creation)
        if not self.pk and self.date and self.date < date.today():
            raise ValidationError(_("Cannot create holidays for past dates."))
        
        # Validate half-day period requirement
        if self.is_recurring and not self.name:
            raise ValidationError(_("Recurring holidays must have a name."))

    def save(self, *args, **kwargs):
        """
        Override save to auto-generate recurring holidays.
        When is_recurring=True, creates the next 5 years of holidays.
        """
        is_new = self.pk is None
        was_recurring = False
        
        # Check if this is an update and if is_recurring changed
        if not is_new:
            old_instance = Holiday.objects.get(pk=self.pk)
            was_recurring = old_instance.is_recurring
        
        # Generate recurring group ID if this is a new recurring holiday
        if is_new and self.is_recurring and not self.recurring_group_id:
            self.recurring_group_id = uuid.uuid4()
        
        # Save the current instance first
        super().save(*args, **kwargs)
        
        # Handle recurring holiday logic
        if self.is_recurring and is_new:
            # Generate future holidays (next 5 years)
            self._generate_future_holidays()
        elif not self.is_recurring and was_recurring:
            # User unchecked is_recurring - delete future holidays and clear group ID
            self._remove_future_recurring_holidays()

    def _generate_future_holidays(self):
        """Generate the next 5 years of recurring holidays"""
        if not self.recurring_group_id:
            return
        
        current_year = self.date.year
        holidays_to_create = []
        
        for year_offset in range(1, 6):  # Next 5 years
            future_year = current_year + year_offset
            future_date = self.date.replace(year=future_year)
            
            # Check if this holiday already exists
            exists = Holiday.objects.filter(
                date=future_date,
                region=self.region
            ).exists()
            
            if not exists:
                holidays_to_create.append(
                    Holiday(
                        date=future_date,
                        name=self.name,
                        description=self.description,
                        is_recurring=True,
                        recurring_group_id=self.recurring_group_id,
                        region=self.region,
                        is_working_day=self.is_working_day,
                        is_active=self.is_active,
                    )
                )
        
        # Bulk create all future holidays
        if holidays_to_create:
            Holiday.objects.bulk_create(holidays_to_create)

    def _remove_future_recurring_holidays(self):
        """Remove future holidays when is_recurring is set to False"""
        if not self.recurring_group_id:
            return
        
        # Delete all future holidays in this recurring group
        Holiday.objects.filter(
            recurring_group_id=self.recurring_group_id,
            date__gt=date.today()
        ).delete()
        
        # Clear recurring_group_id for all remaining holidays in the group
        Holiday.objects.filter(
            recurring_group_id=self.recurring_group_id
        ).update(
            is_recurring=False,
            recurring_group_id=None
        )

    def delete(self, *args, **kwargs):
        """
        Override delete to handle recurring holidays.
        If this holiday is part of a recurring group, delete/deactivate all related holidays.
        """
        if self.recurring_group_id:
            # Mark all holidays in this recurring group as deleted (soft delete)
            Holiday.objects.filter(
                recurring_group_id=self.recurring_group_id
            ).update(is_deleted=True)
        else:
            # Single holiday - just soft delete
            self.is_deleted = True
            self.save()

    def __str__(self):
        region_str = f" ({self.region})" if self.region else ""
        recurring_str = " [Recurring]" if self.is_recurring else ""
        return f"{self.name} - {self.date}{region_str}{recurring_str}"


class HolidayUpload(BaseTemplateModel):
    """
    Stores uploaded holiday images for audit trail.
    Images are stored in MEDIA_ROOT/holiday_uploads/ and only the path is stored in DB.
    """
    uploaded_by = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='holiday_uploads',
        help_text="User who uploaded the image"
    )
    image = models.ImageField(
        upload_to='holiday_uploads/%Y/%m/',  # Organizes by year/month
        help_text="Uploaded holiday list image (stored in MEDIA_ROOT)"
    )
    extracted_data = models.JSONField(
        blank=True,
        null=True,
        help_text="JSON data extracted from the image via OCR"
    )
    extraction_status = models.CharField(
        max_length=20,
        choices=[
            ('SUCCESS', 'Success'),
            ('FAILED', 'Failed'),
            ('PENDING', 'Pending')
        ],
        default='PENDING',
        help_text="Status of the OCR extraction"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if extraction failed"
    )
    
    class Meta:
        verbose_name = "Holiday Upload"
        verbose_name_plural = "Holiday Uploads"
        db_table = 'holiday_uploads'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['uploaded_by', 'created_at']),
            models.Index(fields=['extraction_status']),
        ]
    
    def __str__(self):
        return f"Upload by {self.uploaded_by.username} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"
