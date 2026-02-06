from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema
from apps.base.views import DeleteMixin, AdminWriteViewSet
from apps.holidays.models import Holiday
from apps.holidays.serializers import (
    HolidaySerializer,
    HolidayListSerializer,
    BulkHolidayCreateSerializer
)


class HolidayViewSet(DeleteMixin, AdminWriteViewSet):
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
    
    # perform_destroy is handled by SoftDeleteMixin
    
    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'image': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Upload an image file containing holiday list'
                    }
                },
                'required': ['image']
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'upload_id': {'type': 'string'},
                    'image_url': {'type': 'string'},
                    'image_path': {'type': 'string'},
                    'extracted_holidays': {'type': 'array'},
                    'total_count': {'type': 'integer'},
                    'validation_errors': {'type': 'array', 'nullable': True}
                }
            },
            400: {'description': 'No image file provided'},
            500: {'description': 'Failed to process image'}
        },
        description="Extract holidays from an uploaded image using Gemini AI OCR. Upload an image containing a holiday list and get structured holiday data back.",
        summary="Extract holidays from image via OCR"
    )
    @action(
        detail=False, 
        methods=['POST'], 
        permission_classes=[IsAdminUser],
        parser_classes=[MultiPartParser, FormParser]
    )
    def extract_from_image(self, request):
        """
        Extract holidays from an uploaded image using Gemini OCR.
        Saves the image to MEDIA storage for audit trail.
        """
        if 'image' not in request.FILES:
            return Response(
                {'error': 'No image file provided. Please upload an image.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image_file = request.FILES['image']
        
        # Import here to avoid circular imports
        from apps.holidays.models import HolidayUpload
        from apps.ai_services.services import GeminiOCRService
        
        # Create upload record
        upload_record = HolidayUpload.objects.create(
            uploaded_by=request.user,
            image=image_file,
            extraction_status='PENDING'
        )
        
        try:
            # Use AI service for OCR processing
            ocr_service = GeminiOCRService()
            
            # Open the saved image file for processing
            with upload_record.image.open('rb') as img:
                # Create a file-like object that the service can read
                from django.core.files.uploadedfile import InMemoryUploadedFile
                import io
                
                # Read the image data
                image_data = img.read()
                
                # Create a new file object with the data
                image_file_for_service = InMemoryUploadedFile(
                    file=io.BytesIO(image_data),
                    field_name='image',
                    name=upload_record.image.name,
                    content_type=image_file.content_type,
                    size=len(image_data),
                    charset=None
                )
                
                # Extract holidays using the service
                result = ocr_service.extract_holidays_from_image(
                    image_file=image_file_for_service,
                    user=request.user,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    path=request.path
                )
            
            # Check if extraction was successful
            if result['status'] == 'SUCCESS':
                # Save extracted data to upload record
                upload_record.extracted_data = result['extracted_holidays']
                upload_record.extraction_status = 'SUCCESS'
                upload_record.save()
                
                return Response({
                    'success': True,
                    'upload_id': str(upload_record.id),
                    'image_url': request.build_absolute_uri(upload_record.image.url),
                    'image_path': upload_record.image.name,
                    'holidays': result['extracted_holidays'],  # All holidays with validation_error field
                    'total_count': result['total_count'],
                    'has_validation_errors': result.get('has_validation_errors', False),
                    'processing_time_ms': result.get('processing_time_ms'),
                    'model_used': result.get('model_used')
                }, status=status.HTTP_200_OK)
            else:
                # Extraction failed
                upload_record.extraction_status = 'FAILED'
                upload_record.error_message = result.get('error', 'Unknown error')
                upload_record.save()
                
                return Response({
                    'error': 'Failed to process image',
                    'details': result.get('error'),
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
