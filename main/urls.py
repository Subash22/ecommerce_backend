from django.urls import path
from .views import *
from users import views as user_views


urlpatterns = [
    path('register/', user_views.register, name='user-register'),
    path('', HomeView.as_view(), name='home'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('order-cart/', OrderSummaryView.as_view(), name='order-cart'),
    path('add-to-cart/<slug>/', add_to_cart, name='add-to-cart'),
    path('add-items-to-cart/<slug>/', add_items_to_cart, name='add-items-to-cart'),
    path('add-single-item-to-cart/<slug>/', add_single_item_to_cart, name='add-single-item-to-cart'),
    path('remove-item-from-cart/<slug>/', remove_single_item_from_cart, name='remove-single-item-from-cart'),
    path('remove-from-cart/<slug>/', remove_from_cart, name='remove-from-cart'),
    path('cancel-order/<ref_code>/', cancel_order, name='cancel-order'),
    path('wishlist/', WishlistView.as_view(), name='wishlist'),
    path('add-to-wishlist/<slug>/', add_to_wishlist, name='add-to-wishlist'),
    path('remove-from-wishlist/<slug>/', remove_from_wishlist, name='remove-from-wishlist'),
    path('shop/', ShopDetailView.as_view(), name='shop'),
    path('product/<slug>/', ItemDetailView.as_view(), name='product'),
    path('product/<slug>/review/', product_review, name='product-review'),
    
    path('search/', SearchView.as_view(), name='search'),
    path('about/', AboutView.as_view(), name='about'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('contact-form/', contact_form, name='contact-form'),
    path('privacy-policy/', PrivacyPolicyView.as_view(), name='privacy-policy'),
    path('terms-conditions/', TermsConditionsView.as_view(), name='terms-conditions'),
    path('faq/', FAQView.as_view(), name='faq'),
    path('subscribe/', subscribe, name='subscribe'),

    path('blogs/', BlogsView.as_view(), name='blogs'),
    path('blog/<slug>/', BlogView.as_view(), name='blog'),

    path('order_confirmation/', OrderConfirmation.as_view(), name='order-confirmation'),
    path('thank_you/', ThankYou.as_view(), name='thank-you'),

    path('dashboard/', DashboardPage.as_view(), name='dashboard'),
    path('orders/', OrdersViewPage.as_view(), name='orders'),

    path('product-type/<slug>/', get_product_type, name="product-type"),

    path('activate/<uidb64>/<token>/',user_views.activate, name='activate'),
    
    path('category/<slug>/', CategoryDetailView.as_view(), name='category'),
    path('subcategory/<slug1>/<slug>/', SubcategoryDetailView.as_view(), name='subcategory'),
    
    path('categories/', CategoriesView.as_view(), name='categories'),
    
    path('addresses/', AddressView.as_view(), name='address'),
    path('address/<int:address_id>', UpdateAddressView.as_view(), name='edit-address'),
    
    path('filter-product/', FilterProductView.as_view(), name='filter-product'),
]