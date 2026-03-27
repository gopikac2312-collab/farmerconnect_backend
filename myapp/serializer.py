from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model

from .models import Product, Order, OrderItem, ExchangeOffer,CartItem,Cart,Feedback

User = get_user_model()

# -----------------------
# TASK SERIALIZER
# -----------------------
# class TaskSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Task
#         fields = '__all__'

# -----------------------
# REGISTER SERIALIZER
# -----------------------
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )

    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'role')  # ✅ ADD ROLE

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data['role'],   # ✅ SAVE ROLE
            is_active=True
        )
        return user


# -----------------------
# USER SERIALIZER
# -----------------------
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('id','username','email','password','role','phone','address')
        read_only_fields = ('id',)

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

# -----------------------
# PRODUCT SERIALIZER
# -----------------------
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'price',
            'stock',
            'image',
            'farmer',
            'is_active',
            'is_approved'
        ]
        read_only_fields = ['farmer', 'is_active', 'is_approved']

# -----------------------
# ORDER ITEM SERIALIZER
# -----------------------
class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "price", "total_price"]

    def get_total_price(self, obj):
        return obj.quantity * obj.price

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_id",
            "amount",
            "payment_method",
            "status",
            "created_at",
            "items",
            "total_amount",
        ]

    def get_total_amount(self, obj):
        return sum(item.quantity * item.price for item in obj.items.all())



    #-----EXCHANGE OFFERS----#

class ExchangeOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeOffer
        fields = '__all__'
        read_only_fields = ['farmer','status']

#-------CART-----#
class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    price = serializers.DecimalField(source="product.price", max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "product", "product_name", "price", "quantity", "subtotal"]

    def get_subtotal(self, obj):
        return obj.product.price * obj.quantity







from rest_framework_simplejwt.serializers import TokenObtainPairSerializer



class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role  # <- this is the important line
        return token

   

from rest_framework_simplejwt.views import TokenObtainPairView

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

class FeedbackSerializer(serializers.ModelSerializer):
    buyer_name = serializers.CharField(source="buyer.username", read_only=True)

    class Meta:
        model = Feedback
        fields = "__all__"

# serializers.py
from rest_framework import serializers
from .models import Review

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'user', 'product', 'rating', 'comment', 'created_at']



def validate_image(self, image):
    if image.size > 2 * 1024 * 1024:  # 2MB
        raise serializers.ValidationError("Image size must be under 2MB")
    return image
