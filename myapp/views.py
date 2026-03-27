# views.py

from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth import get_user_model
# from django.db import transaction
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

from .models import (
    Product, Farmer, Order, OrderItem,
    ExchangeOffer, Cart, Payment, Feedback, Notification, Review
)
from .serializer import (
    RegisterSerializer, ProductSerializer, UserSerializer,
    OrderSerializer, ExchangeOfferSerializer,
    CartItemSerializer,CartItem
, FeedbackSerializer, ReviewSerializer
)
from .permissions import IsFarmer
from .utils import email_verification_token
from .tasks import send_verification_email
from django.conf import settings
import razorpay

User = get_user_model()

# =====================================================
# RAZORPAY CLIENT
# =====================================================
client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

# =====================================================
# AUTH & REGISTER
# =====================================================


from rest_framework_simplejwt.views import TokenObtainPairView
from .serializer import MyTokenObtainPairSerializer

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        if user.role == "farmer":
            Farmer.objects.create(user=user)
        return Response({"message": "Registration successful"})
    print(serializer.errors)
    return Response(serializer.errors, status=400)



@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        return redirect("http://localhost:5173/login?verified=false")

    if user.is_email_verified:
        return redirect("http://localhost:5173/login?verified=already")

    if email_verification_token.check_token(user, token):
        user.is_active = True
        user.is_email_verified = True
        user.save()
        return redirect("http://localhost:5173/login?verified=true")

    return redirect("http://localhost:5173/login?verified=expired")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    return Response({
        "username": request.user.username,
        "email": request.user.email,
        "role": request.user.role,
    })

# =====================================================
# PRODUCT VIEWSET
# =====================================================
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'my_products']:
            return [IsAuthenticated(), IsFarmer()]
        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.role == 'buyer':
            return Product.objects.filter(is_active=True, is_approved=True, stock__gt=0)
        if user.is_authenticated and user.role == 'farmer':
            return Product.objects.filter(farmer__user=user)
        return Product.objects.filter(is_active=True)

    def perform_create(self, serializer):
        farmer = Farmer.objects.get(user=self.request.user)
        serializer.save(farmer=farmer, is_active=True, is_approved=True)

    def destroy(self, request, *args, **kwargs):
        try:
            product = Product.objects.get(pk=kwargs["pk"])
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        if product.farmer.user != request.user:
            raise PermissionDenied("You cannot delete this product")

        product.delete()
        return Response({"message": "Product deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def my_products(self, request):
        farmer = Farmer.objects.get(user=request.user)
        products = Product.objects.filter(farmer=farmer)
        return Response(ProductSerializer(products, many=True).data)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_product(request, pk):
    product = get_object_or_404(Product, id=pk, farmer=request.user)
    product.delete()
    return Response(status=204)

# 

# =====================================================
# ORDER VIEWSET
# =====================================================
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer

    def get_queryset(self):
        user = self.request.user

        if user.is_authenticated and user.role == "buyer":
            return Order.objects.filter(buyer=user).order_by('-created_at')

        if user.is_authenticated and user.role == "farmer":
            return Order.objects.filter(
                items__farmer__user=user
            ).distinct().order_by('-created_at')

        return Order.objects.none()


# =====================================================
# CART VIEWSET
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import CartItem, Product
from .serializer import CartItemSerializer

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]
    
    


    def get_queryset(self):
        # Only show cart items for the logged-in user
        return CartItem.objects.filter(user=self.request.user)

    # Custom action for adding an item
    @action(detail=False, methods=["post"])
    def add_item(self, request):
        # Use 'product' to match frontend field
        product_id = request.data.get("product")
        quantity = int(request.data.get("quantity", 1))

        if not product_id:
            return Response({"error": "Product required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        # If the cart item already exists, increase quantity
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={"quantity": quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        # Serialize and return the cart item
        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    





   

# =====================================================
# PAYMENT
# =====================================================
import razorpay
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import uuid
import json

client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_order(request):
    amount = request.data.get("amount")

    if not amount or not str(amount).isdigit():
        return Response({"error": "Amount must be a number"}, status=400)

    amount_paise = int(amount) * 100

    razorpay_order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "payment_capture": 1
    })

    order = Order.objects.create(
        user=request.user,
        order_id=razorpay_order["id"],
        amount=int(amount),
        payment_method="RAZORPAY",
        status="PENDING"
    )

    return Response({
        "order_id": razorpay_order["id"],
        "amount": amount_paise,
        "key": settings.RAZORPAY_KEY_ID
    })
# Verify Razorpay Payment

from .models import Order, CartItem, OrderItem

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    try:
        data = request.data

        params_dict = {
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"],
        }

        # 1️⃣ Verify Razorpay signature
        client.utility.verify_payment_signature(params_dict)

        # 2️⃣ Fetch existing order
        order = Order.objects.get(order_id=data["razorpay_order_id"])

        # 3️⃣ Update order status
        order.payment_id = data["razorpay_payment_id"]
        order.status = "PAID"
        order.save()

        # 4️⃣ Create Payment entry
        Payment.objects.create(
            user=request.user,
            order=order,
            razorpay_order_id=data["razorpay_order_id"],
            razorpay_payment_id=data["razorpay_payment_id"],
            razorpay_signature=data["razorpay_signature"],
            amount=order.amount,
            status="paid"
        )

        # 5️⃣ Move cart items → order items
        cart_items = CartItem.objects.filter(user=request.user)

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                farmer=item.product.farmer,
                quantity=item.quantity,
                price=item.product.price
            )

        cart_items.delete()

        return Response({
            "success": True,
            "message": "Payment verified successfully",
            "order_id": order.order_id
        })

    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=404)

    except razorpay.errors.SignatureVerificationError:
        return Response({"error": "Payment verification failed"}, status=400)

# Create COD Order
@api_view(["POST"])
def create_cod_order(request):
    data = request.data
    amount = data.get("amount")
    cart_items = data.get("cartItems", [])

    if not amount:
        return Response({"error": "Amount is required"}, status=400)

    order = {
        "order_id": "COD_" + str(uuid.uuid4().hex[:8]),
        "amount": amount,
        "cart_items": cart_items,
        "payment_type": "COD",
    }

    # Save order in DB here

    return Response({"success": True, "order": order})



# =====================================================
# EXCHANGE OFFERS
# =====================================================
class ExchangeOfferViewSet(viewsets.ModelViewSet):
    serializer_class = ExchangeOfferSerializer
    permission_classes = [IsAuthenticated, IsFarmer]

    def get_queryset(self):
        return ExchangeOffer.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        farmer = Farmer.objects.get(user=self.request.user)
        serializer.save(farmer=farmer)

    @action(detail=False, methods=['get'])
    def my_offers(self, request):
        farmer = Farmer.objects.get(user=request.user)
        offers = ExchangeOffer.objects.filter(farmer=farmer)
        return Response(ExchangeOfferSerializer(offers, many=True).data)

# =====================================================
# REVIEWS
# =====================================================
class ReviewListView(APIView):
    def get(self, request):
        reviews = Review.objects.all()
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)

# =====================================================
# FEEDBACK
# =====================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_feedback(request):
    if request.user.role != 'buyer':
        return Response({"detail": "Only buyers can give feedback"}, status=403)

    order_id = request.data.get("order_id")
    product_id = request.data.get("product_id")
    rating = request.data.get("rating")
    comment = request.data.get("comment")

    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    item = get_object_or_404(OrderItem, order=order, product_id=product_id)

    if Feedback.objects.filter(order=order, product=item.product).exists():
        return Response({"detail": "Feedback already given"}, status=400)

    feedback = Feedback.objects.create(
        order=order,
        product=item.product,
        farmer=item.farmer,
        buyer=request.user,
        rating=rating,
        comment=comment
    )

    Notification.objects.create(
        farmer=item.farmer,
        message=f"New feedback received for {item.product.name}"
    )

    return Response(FeedbackSerializer(feedback).data, status=201)

@api_view(['GET'])
def product_reviews(request, product_id):
    feedbacks = Feedback.objects.filter(product_id=product_id)
    serializer = FeedbackSerializer(feedbacks, many=True)
    return Response(serializer.data)


# =====================================================
# BUYER ORDERS
# =====================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def buyer_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


# =====================================================
# FARMER STATS
# =====================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def farmer_stats(request):
    if request.user.role != 'farmer':
        return Response({"detail": "Not allowed"}, status=403)

    farmer = get_object_or_404(Farmer, user=request.user)
    total_products = Product.objects.filter(farmer=farmer).count()
    total_orders = OrderItem.objects.filter(farmer=farmer).values('order').distinct().count()
    # earnings = OrderItem.objects.filter(farmer=farmer, order__status='delivered').aggregate(
    #     total=Sum(F('quantity') * F('price'))
    # )['total'] or 0

    # return Response({"products": total_products, "orders": total_orders, "earnings": earnings})

# =====================================================
# FARMER NOTIFICATIONS
# =====================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def farmer_notifications(request):
    if request.user.role != 'farmer':
        return Response({"detail": "Not allowed"}, status=403)

    farmer = get_object_or_404(Farmer, user=request.user)
    notifications = Notification.objects.filter(farmer=farmer, is_read=False).order_by('-created_at')

    return Response({
        "unread_count": notifications.count(),
        "notifications": [{"id": n.id, "message": n.message, "created_at": n.created_at} for n in notifications]
    })



# # views.py
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response
# from django.db import transaction
# from .models import Cart, Order, OrderItem, Product

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# @transaction.atomic
# def create_order(request):
#     cart = Cart.objects.filter(buyer=request.user)  # get all cart items for buyer

#     if not cart.exists():
#         return Response({"detail": "Cart is empty"}, status=400)

#     order = Order.objects.create(
#         buyer=request.user,
#         status="pending"
#     )

#     total = 0
#     for item in cart:
#         OrderItem.objects.create(
#             order=order,
#             product=item.product,
#             farmer=item.product.farmer,
#             quantity=item.quantity,
#             price=item.product.price
#         )
#         total += item.quantity * item.product.price
#         # reduce stock
#         item.product.stock -= item.quantity
#         item.product.save()

#     order.total_amount = total
#     order.save()

#     # delete cart items
#     cart.delete()

#     return Response({
#         "id": order.id,
#         "total_amount": order.total_amount
#     })
