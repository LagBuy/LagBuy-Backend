from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from common.services.storage import STORAGE


class ImageUploadView(APIView):
    """
    API endpoint for uploading product images.
    Handles file uploads and returns the image URL on success.
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        try:
            uploaded_image = request.FILES.get("image")
            if not uploaded_image:
                return Response(
                    {"detail": "No image file provided."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            file_url = STORAGE.upload_file(
                uploaded_image, uploaded_image.name, uploaded_image.content_type
            )
            if file_url:
                return Response({"url": file_url}, status=status.HTTP_201_CREATED)
            return Response(
                {"detail": "Failed to upload image."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            raise e  # allows for proper flagging and debugging