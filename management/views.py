from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .serializers import *
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework import viewsets, filters
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, timedelta
from django.db import transaction
from .tasks import send_due_date_notifications

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)
        data['message'] = 'Login successful'
        data['username'] = self.user.username
        return data

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    permission_classes = [AllowAny]

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

    def get_permissions(self):
        if self.action == 'list':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]
    
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]
        return [IsAdminUser()]
    
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['author__name', 'category__name']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

class BorrowAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        active_borrows = Borrow.objects.filter(user=request.user, return_date__isnull=True)
        serializer = BorrowSerializer(active_borrows, many=True)
        return Response(serializer.data)

    def post(self, request):
        book_id = request.data.get('book_id')
        borrow_date_str = request.data.get("borrow_date")

        if not book_id:
            return Response({"error": "book_id is required in request body"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            active_borrows = Borrow.objects.filter(user=request.user, return_date__isnull=True).count()
            if active_borrows >= 3:
                return Response({"error": "Borrow limit reached (max 3 active books)"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                book = Book.objects.select_for_update().get(id=book_id)
            except Book.DoesNotExist:
                return Response({"error": "Book not found"}, status=status.HTTP_404_NOT_FOUND)

            if book.available_copies < 1:
                return Response({"error": "No copies available"}, status=status.HTTP_400_BAD_REQUEST)

            if borrow_date_str:
                try:
                    borrow_date = datetime.strptime(borrow_date_str, "%Y-%m-%d")
                    borrow_date = timezone.make_aware(borrow_date)
                except ValueError:
                    return Response({"error": "Invalid borrow_date format, use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                borrow_date = timezone.now()

            due_date = borrow_date + timedelta(days=14)

            borrow = Borrow.objects.create(
                user=request.user,
                book=book,
                borrow_date=borrow_date,
                due_date=due_date
            )

            book.available_copies -= 1
            book.save()

            serializer = BorrowSerializer(borrow)
            return Response(serializer.data, status=status.HTTP_201_CREATED)


class ReturnBookAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        borrow_id = request.data.get('borrow_id')
        return_date_str = request.data.get('return_date')

        if not borrow_id:
            return Response({"error": "borrow_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            try:
                borrow = Borrow.objects.select_for_update().get(id=borrow_id, user=request.user)
            except Borrow.DoesNotExist:
                return Response({"error": "Borrow record not found"}, status=status.HTTP_404_NOT_FOUND)

            if borrow.return_date:
                return Response({"error": "Book already returned"}, status=status.HTTP_400_BAD_REQUEST)

            if not borrow.due_date:
                borrow.due_date = borrow.borrow_date + timedelta(days=14)

            if return_date_str:
                try:
                    return_date = datetime.strptime(return_date_str, "%Y-%m-%d")
                    return_date = timezone.make_aware(return_date)
                except ValueError:
                    return Response({"error": "Invalid return_date format, use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return_date = timezone.now()

            borrow.return_date = return_date
            borrow.save()

            borrow.book.available_copies += 1
            borrow.book.save()

            if borrow.return_date > borrow.due_date:
                days_late = (borrow.return_date - borrow.due_date).days
                profile, _ = UserProfile.objects.get_or_create(user=request.user)
                profile.penalty_points += days_late
                profile.save()

            return Response({
                "message": "Book returned successfully",
                "borrow_date": borrow.borrow_date,
                "due_date": borrow.due_date,
                "return_date": borrow.return_date
            }, status=status.HTTP_200_OK)

        
class UserPenaltyPointsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        if not (request.user.is_staff or request.user.id == id):
            return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        try:
            profile = UserProfile.objects.get(user__id=id)
        except UserProfile.DoesNotExist:
            return Response({"penalty_points": 0})

        return Response({"penalty_points": profile.penalty_points})
    
class SendDueNotificationsView(APIView):
    def get(self, request):
        send_due_date_notifications.delay()
        return Response({"message": "Due date notifications task started."})