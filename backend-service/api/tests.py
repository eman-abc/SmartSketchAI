from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from .models import User, GeneratedImage

class ImageHistoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='password123', role='forensic')
        self.client.force_authenticate(user=self.user)
        
        # Create some test images
        GeneratedImage.objects.create(user=self.user, prompt="Test prompt 1")
        GeneratedImage.objects.create(user=self.user, prompt="Test prompt 2")

    def test_get_my_images(self):
        url = reverse('my_images')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['prompt'], "Test prompt 2") # Ordered by -created_at
