from users.serializers import UserSerializer
from .models import *
from rest_framework import serializers


class ItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCategory
        fields = ('__all__')


class ItemSubCategorySerializer(serializers.ModelSerializer):
    category = ItemCategorySerializer()

    class Meta:
        model = ItemSubCategory
        fields = ('__all__')
        

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ('__all__')


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ('__all__')
        

class ItemImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemImage
        fields = ('__all__')
        

class ItemSerializer(serializers.ModelSerializer):
    category = ItemCategorySerializer()
    subcategory = ItemSubCategorySerializer()
    brand = BrandSerializer()
    color = ColorSerializer(many=True)
    images = ItemImageSerializer(many=True)
    is_wishlist = serializers.SerializerMethodField('is_wishlist_added')
    
    def is_wishlist_added(self, obj):
        user_id = self.context.get("user_id")
        if user_id:
            for wishlist in Wishlist.objects.filter(user__id=user_id):
                if obj.id == wishlist.item.id:
                    return True
            else:
                return False
        return False

    class Meta:
        model = Item
        fields = ('__all__')
        

class OrderItemSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    item = ItemSerializer()
    color = ColorSerializer()

    class Meta:
        model = OrderItem
        fields = ('__all__')
        

class WishlistSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    item = ItemSerializer()

    class Meta:
        model = Wishlist
        fields = ('__all__')
        

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ('__all__')
        

class AddressSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Address
        fields = ('__all__')
        

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ('__all__')
        

class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    items = OrderItemSerializer(many=True)
    shipping_address = AddressSerializer()
    payment = PaymentMethodSerializer()
    coupon = CouponSerializer()

    class Meta:
        model = Order
        fields = ('__all__')
        

class RefundSerializer(serializers.ModelSerializer):
    order = OrderSerializer()

    class Meta:
        model = Refund
        fields = ('__all__')
        

class SubscribeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscribe
        fields = ('__all__')
        

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('__all__')
        

class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    item = ItemSerializer()

    class Meta:
        model = Review
        fields = ('__all__')
        

class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer()

    class Meta:
        model = Post
        fields = ('__all__')
        

class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = ('__all__')
