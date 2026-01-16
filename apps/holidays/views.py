from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone
from datetime import date
import google.generativeai as genai
from django.conf import settings
import json
import base64

from apps.holidays.models import Holiday
from apps.holidays.serializers import (
    HolidaySerializer,
    HolidayListSerializer,
    BulkHolidayCreateSerializer,
    HolidayExtraction,
    BulkHolidayExtraction
)


class IsAdminOrReadOnly(IsAuthenticated):
    """
    Custom permission: Admin can do anything, regular users can only read.
    """
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not super().has_permission(request, view):
            return False
        
        # Allow read-only for all authenticated users
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Write operations require admin/staff
        return request.user.is_staff or request.user.is_superuser


class HolidayViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing holidays.
    
    Permissions:
    - Admin/Staff: Full CRUD access
    - Regular users: Read-only access
    
    Endpoints:
    - GET /api/holidays/ - List all active holidays
    - POST /api/holidays/ - Create a single holiday (admin only)
    - GET /api/holidays/{id}/ - Get holiday details
    - PATCH /api/holidays/{id}/ - Update holiday (admin only)
    - DELETE /api/holidays/{id}/ - Delete holiday (admin only)
    - POST /api/holidays/extract-from-image/ - Extract holidays from image via OCR
    - POST /api/holidays/bulk-create/ - Create multiple holidays at once
    """
    
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    
    def get_queryset(self):
        """
        Return active holidays only for regular users.
        Admin can see all holidays including deleted ones.
        """
        queryset = Holiday.objects.all()
        
        # Regular users only see active, non-deleted holidays
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(is_active=True, is_deleted=False)
        
        # Optional filtering by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        region = self.request.query_params.get('region')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        if region:
            queryset = queryset.filter(region=region)
        
        return queryset.order_by('date')
    
    def get_serializer_class(self):
        """Use lightweight serializer for list view"""
        if self.action == 'list':
            return HolidayListSerializer
        return HolidaySerializer
    
    def perform_destroy(self, instance):
        """Soft delete instead of hard delete"""
        instance.is_deleted = True
        instance.save()
    
    @action(detail=False, methods=['POST'], permission_classes=[IsAdminUser])
    def extract_from_image(self, request):
        """
        Extract holidays from an uploaded image using Gemini OCR.
        Saves the image to MEDIA storage for audit trail.
        
        Request:
        - multipart/form-data with 'image' file
        
        Response:
        - JSON with extracted holidays array and image URL
        """
        if 'image' not in request.FILES:
            return Response(
                {'error': 'No image file provided. Please upload an image.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image_file = request.FILES['image']
        
        # Import here to avoid circular imports
        from apps.holidays.models import HolidayUpload
        
        # Create upload record (saves image to MEDIA_ROOT automatically)
        upload_record = HolidayUpload.objects.create(
            uploaded_by=request.user,
            image=image_file,  # Django saves this to MEDIA_ROOT/holiday_uploads/YYYY/MM/
            extraction_status='PENDING'
        )
        
        try:
            # Configure Gemini API
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            # Read image data from the saved file
            with upload_record.image.open('rb') as img:
                image_data = img.read()
            
            # Prepare the prompt
            prompt = """
            Analyze this handwritten or printed holiday list image and extract the following information for each holiday:
            - Date (in YYYY-MM-DD format)
            - Holiday name
            - Type or description (if mentioned)
            - Is it recurring yearly? (yes/no)
            - Region (if mentioned, e.g., Mumbai, Bangalore, All India)
            
            Return the data in JSON format as an array of objects with keys: date, name, description, is_recurring (boolean), region.
            
            Example output:
            [
              {
                "date": "2026-01-26",
                "name": "Republic Day",
                "description": "National Holiday",
                "is_recurring": true,
                "region": "All India"
              },
              {
                "date": "2026-08-15",
                "name": "Independence Day",
                "description": "",
                "is_recurring": true,
                "region": "All India"
              }
            ]
            
            Important:
            - Only return valid JSON, no additional text
            - Use YYYY-MM-DD format for dates
            - Set is_recurring to true for national holidays or holidays that repeat yearly
            - If region is not mentioned, use empty string ""
            """
            
            # Generate content from image
            response = model.generate_content([
                prompt,
                {"mime_type": image_file.content_type, "data": image_data}
            ])
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            extracted_data = json.loads(response_text)
            
            # Validate using Pydantic
            validated_holidays = []
            validation_errors = []
            
            for idx, holiday_data in enumerate(extracted_data):
                try:
                    # Validate each holiday
                    holiday = HolidayExtraction(**holiday_data)
                    validated_holidays.append(holiday.model_dump())
                except Exception as e:
                    validation_errors.append({
                        'index': idx,
                        'data': holiday_data,
                        'error': str(e)
                    })
            
            # Save extracted data to upload record
            upload_record.extracted_data = validated_holidays
            upload_record.extraction_status = 'SUCCESS'
            upload_record.save()
            
            return Response({
                'success': True,
                'upload_id': str(upload_record.id),
                'image_url': request.build_absolute_uri(upload_record.image.url),
                'image_path': upload_record.image.name,  # Relative path stored in DB
                'extracted_holidays': validated_holidays,
                'total_count': len(validated_holidays),
                'validation_errors': validation_errors if validation_errors else None
            }, status=status.HTTP_200_OK)
            
        except json.JSONDecodeError as e:
            upload_record.extraction_status = 'FAILED'
            upload_record.error_message = f'JSON Parse Error: {str(e)}'
            upload_record.save()
            
            return Response({
                'error': 'Failed to parse OCR response as JSON',
                'details': str(e),
                'raw_response': response_text[:500],  # First 500 chars for debugging
                'upload_id': str(upload_record.id)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except Exception as e:
            upload_record.extraction_status = 'FAILED'
            upload_record.error_message = str(e)
            upload_record.save()
            
            return Response({
                'error': 'Failed to process image',
                'details': str(e),
                'upload_id': str(upload_record.id)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['POST'], permission_classes=[IsAdminUser])
    def bulk_create(self, request):
        """
        Create multiple holidays at once.
        Skips duplicates and returns detailed response.
        
        Request:
        {
          "holidays": [
            {
              "date": "2026-01-26",
              "name": "Republic Day",
              "description": "",
              "is_recurring": true,
              "region": "All India"
            },
            ...
          ]
        }
        
        Response:
        {
          "success": true,
          "total_submitted": 10,
          "created_count": 7,
          "skipped_count": 3,
          "created_holidays": [...],
          "skipped_holidays": [...]
        }
        """
        serializer = BulkHolidayCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            result = serializer.save()
            
            # Serialize created holidays
            created_serializer = HolidaySerializer(result['created'], many=True)
            
            return Response({
                'success': True,
                'total_submitted': len(request.data.get('holidays', [])),
                'created_count': len(result['created']),
                'skipped_count': len(result['skipped']),
                'created_holidays': created_serializer.data,
                'skipped_holidays': result['skipped']
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
