from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    register_user,
    user_profile,
    verify_email,
    ProductViewSet,
    OrderViewSet,

    ExchangeOfferViewSet,
   create_order,
    verify_payment,
    create_cod_order,

    buyer_orders,
    farmer_notifications,
    farmer_stats,
    create_feedback,
    ReviewListView,
    CartViewSet,
    MyTokenObtainPairView,

)


router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='products')
router.register(r'orders', OrderViewSet, basename='orders')
# router.register(r'tasks', TaskViewSet, basename='tasks')
router.register(r'exchange-offers', ExchangeOfferViewSet, basename='exchange-offers')
router.register(r'cart', CartViewSet, basename='cart')

urlpatterns = [
    # AUTH
    path("api/token/", MyTokenObtainPairView.as_view(), name="token"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # API ROUTES
    path("", include(router.urls)),

    # USER
    path("register/", register_user, name="user-register"),
    path("profile/", user_profile, name="user-profile"),

    # EMAIL
    path("verify-email/<uidb64>/<token>/", verify_email, name="verify-email"),

    # PAYMENTS
   # PAYMENTS
   path('payment/create-order/', create_order, name='create_order'),
    path('payment/verify-payment/', verify_payment, name='verify_payment'),
    path('payment/create-cod-order/', create_cod_order, name='create_cod_order'),

    


    # ORDERS
    path("buyer/orders/", buyer_orders, name="buyer-orders"),

    # FARMER
    path("farmer/stats/", farmer_stats, name="farmer-stats"),
    path("farmer/notifications/", farmer_notifications, name="farmer-notifications"),
     

    # REVIEWS & FEEDBACK
    path("reviews/", ReviewListView.as_view(), name="reviews"),
    path("feedback/create/", create_feedback, name="create-feedback"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
