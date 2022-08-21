from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from ratelimit.decorators import ratelimit
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .serializers import *
from .models import *
from django.http import HttpResponse, JsonResponse
import json
from django.core.mail import send_mail, BadHeaderError
from ecommerce_backend.settings import EMAIL_HOST_USER
from django.core import serializers
from django.contrib.auth.models import User
from time import time
from django.db.models import Max, Min, Count, Case, When
from django.views.decorators.csrf import csrf_exempt

import pandas as pd
from sklearn.metrics.pairwise import linear_kernel
from sklearn.feature_extraction.text import TfidfVectorizer


PRODUCT_TYPES = (
    ('Mens', 'Mens'),
    ('Womens', 'Womens'),
    ('Kids', 'Kids')
)


def get_recommendation_by_title(title, items):
    dataset = pd.DataFrame(items.values())
    tfidf = TfidfVectorizer(stop_words='english')
    dataset['description'] = dataset['description'].fillna('')
    tfidf_matrix = tfidf.fit_transform(dataset['description'])
    cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)
    indices = pd.Series(dataset.index, index=dataset['name']).drop_duplicates()
    idx = indices[title]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:11]
    item_indices = [i[0] for i in sim_scores]
    return dataset['id'].iloc[item_indices]

def get_popular_items():
    order_items = OrderItem.objects.filter(ordered=True).values('item').annotate(count=Count('pk', distinct=True)).order_by('-count')
    order_items_ids = [item['item'] for item in order_items]
    preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(order_items_ids)])
    popular_items = Item.objects.filter(pk__in=order_items_ids).order_by(preserved)
    if popular_items.count() < 8:
        rem_items = Item.objects.exclude(pk__in=order_items_ids)[:8-popular_items.count()]
        popular_items = popular_items | rem_items
    return popular_items


def create_ref_code():
    return str(int(time()))



class CheckoutView(APIView):

    @method_decorator(ratelimit(method='POST', key='ip', rate='10/s', block=True))
    def post(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            total_price = float(order.get_total())
            if total_price > 0:
                address = self.request.data['address']
                try:
                    save_order_db(order, total_price, address)
                except Exception as e:
                    return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

                # send email
                products = []
                for item in order.items.all():
                    products.append(item)
                my_items = ''.join(str(v) + ',\n' for v in products)
                subject = "Order Confirmation - The Fashion Fit"
                message = "Name: " + str(self.request.user) + "\nItems:\n" + my_items + "\nTotal Price: Rs." + str(total_price)
                message2 = "Your order of items:\n" + my_items + "\nTotal Price: Rs." + str(total_price) + "\nYou can contact us on sales@thefashionfit.com"
                try:
                    send_mail(subject, message, EMAIL_HOST_USER, [EMAIL_HOST_USER], fail_silently=False)
                except BadHeaderError:
                    return Response({"message": "Invalid header found."}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                try:
                    send_mail(subject, message2, EMAIL_HOST_USER, [
                                self.request.user.email], fail_silently=False)
                except BadHeaderError:
                    return Response({"message": "Invalid header found."}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)

                return Response({"message": "Your order was successful!"}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Error while validating form data. Please try again..."}, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist:
            return Response({"message": "You do not have an active order"}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({"message": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def save_order_db(order, total_price, address):
    order.ordered_date = timezone.now()
    order.total_price = total_price
    order.shipping_address = Address.objects.filter(id=address['id']).first()
    order.payment = PaymentMethod.objects.filter(payment_code="COD").first()
    order.save()

    order_items = order.items.all()
    order_items.update(ordered=True)
    total_profit_loss = 0
    for item in order_items:
        # item.ordered_date = timezone_now
        total_profit_loss += item.profit_loss
        item.save()

    order.ordered = True
    order.status = 0
    order.ref_code = create_ref_code()
    order.total_profit_loss = total_profit_loss
    order.save()


class HomeView(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        items = Item.objects.filter(is_active=True).order_by('-id')
        popular_items = get_popular_items()
        posts = Post.objects.filter(status=1).order_by('-created_on')[:3]

        items_serializer = ItemSerializer(items, many=True, context={'user_id': self.request.user.id}).data
        popular_items_serializer = ItemSerializer(popular_items, many=True, context={'user_id': self.request.user.id}).data
        posts_serializer = PostSerializer(posts, many=True).data
        context = {
            'all_items':  items_serializer,
            'all_popular_items':  popular_items_serializer,
            'blogs':  posts_serializer,
        }
        
        return Response(context, status=status.HTTP_200_OK)


class OrderSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.filter(user=self.request.user, ordered=False).first()
            context = {
                'order': OrderSerializer(order).data,
                'subtotal': order.get_subtotal() if order else 0,
                'total': order.get_total() if order else 0,
            }
            return Response(context, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"message": "Something went wrong."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WishlistView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        try:
            wishlist = Wishlist.objects.filter(user=self.request.user)
            context = {
                'wishlist': WishlistSerializer(wishlist, many=True).data,
            }
            return Response(context, status=status.HTTP_200_OK)
        except:
            return Response({"message": "Something went wrong."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ItemDetailView(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        item = Item.objects.get(slug=self.kwargs['slug'])
        items = Item.objects.filter(is_active=True).order_by('-id')
        reviews = Review.objects.filter(item=item)
        related_products_id = get_recommendation_by_title(item.name, items)
        related_products = Item.objects.filter(pk__in=related_products_id)

        item_serializer = ItemSerializer(item, context={'user_id': self.request.user.id}).data
        related_products_serializer = ItemSerializer(related_products, many=True, context={'user_id': self.request.user.id}).data
        reviews_serializer = ReviewSerializer(reviews, many=True).data
        context = {
            'item':  item_serializer,
            'related_products':  related_products_serializer,
            'reviews': reviews_serializer,
        }

        return Response(context, status=status.HTTP_200_OK)


class ShopDetailView(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        all_items = Item.objects.filter(is_active=True).order_by('-id')
        categories = ItemCategory.objects.filter(is_active=True)
        subcategories = ItemSubCategory.objects.filter(is_active=True)
        price_range_min = Item.objects.all().aggregate(Min('price'))
        price_range_max = Item.objects.all().aggregate(Max('price'))
        price_range = {'min': price_range_min, 'max': price_range_max}
        brands = Brand.objects.all().distinct('name')
        colors = Color.objects.all().distinct('color_code')

        all_items_serializer = ItemSerializer(all_items, many=True, context={'user_id': self.request.user.id}).data
        categories_serializer = ItemCategorySerializer(categories, many=True).data
        for category in categories_serializer:
            category['subcategories'] = ItemSubCategorySerializer(ItemSubCategory.objects.filter(category_id=category['id']), many=True).data
        subcategories_serializer = ItemSubCategorySerializer(subcategories, many=True).data
        brands_serializer = BrandSerializer(brands, many=True).data
        colors_serializer = ColorSerializer(colors, many=True).data
        context = {
            'items':  all_items_serializer,
            'categories':  categories_serializer,
            'subcategories':  subcategories_serializer,
            'price_range': price_range,
            'brands': brands_serializer,
            'colors': colors_serializer
        }
        return Response(context, status=status.HTTP_200_OK)


class CategoryDetailView(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        # raise 404 error if category is not found, replace try-except block
        category = get_object_or_404(ItemCategory, slug=self.kwargs['slug'])

        all_items = Item.objects.filter(is_active=True, category=category).order_by('-id')
        subcategories = ItemSubCategory.objects.filter(is_active=True, category=category)
        price_range_min = Item.objects.all().aggregate(Min('price'))
        price_range_max = Item.objects.all().aggregate(Max('price'))
        price_range = {'min': price_range_min, 'max': price_range_max}
        brands = Brand.objects.all().distinct('name')
        colors = Color.objects.all().distinct('color_code')

        all_items_serializer = ItemSerializer(all_items, many=True, context={'user_id': self.request.user.id}).data
        subcategories_serializer = ItemSubCategorySerializer(subcategories, many=True).data
        brands_serializer = BrandSerializer(brands, many=True).data
        colors_serializer = ColorSerializer(colors, many=True).data
        context = {
            'items': all_items_serializer,
            'subcategories': subcategories_serializer,
            'price_range': price_range,
            'brands': brands_serializer,
            'colors': colors_serializer,
            'category': ItemCategorySerializer(category).data,
        }

        return Response(context, status=status.HTTP_200_OK)


class SubcategoryDetailView(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        all_items = Item.objects.filter(is_active=True).order_by('-id')
        categories = ItemCategory.objects.filter(is_active=True)
        subcategories = ItemSubCategory.objects.filter(is_active=True)
        price_range_min = Item.objects.all().aggregate(Min('price'))
        price_range_max = Item.objects.all().aggregate(Max('price'))
        price_range = {'min': price_range_min, 'max': price_range_max}
        brands = Brand.objects.all().distinct('name')
        colors = Color.objects.all().distinct('color_code')

        all_items_serializer = ItemSerializer(all_items, many=True, context={'user_id': self.request.user.id}).data
        categories_serializer = ItemCategorySerializer(categories, many=True).data
        for category in categories_serializer:
            category['subcategories'] = ItemSubCategorySerializer(ItemSubCategory.objects.filter(category_id=category['id']), many=True).data
        subcategories_serializer = ItemSubCategorySerializer(subcategories, many=True).data
        brands_serializer = BrandSerializer(brands, many=True).data
        colors_serializer = ColorSerializer(colors, many=True).data
        context = {
            'all_items':  all_items_serializer,
            'categories':  categories_serializer,
            'subcategories':  subcategories_serializer,
            'price_range': price_range,
            'brands': brands_serializer,
            'colors': colors_serializer
        }

        # check if slug1 is in fact a category, else raise 404 error
        # can reuse this later or not
        get_object_or_404(ItemCategory, slug=self.kwargs['slug1'])

        # raise 404 error if subcategory is not found, replace try-except block
        subcategory = get_object_or_404(ItemSubCategory, slug=self.kwargs['slug'])

        context['subcategory'] = subcategory
        context['category'] = subcategory.category
        
        return Response(context, status=status.HTTP_200_OK)


class SearchView(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def post(self, *args, **kwargs):
        search = self.request.data['search_q']
        results = Item.objects.filter(Q(name__icontains=search), is_active=True)
        categories = ItemCategory.objects.filter(is_active=True)
        subcategories = ItemSubCategory.objects.filter(is_active=True)
        query = search
        price_range_min = Item.objects.all().aggregate(Min('price'))
        price_range_max = Item.objects.all().aggregate(Max('price'))
        price_range = {'min': price_range_min, 'max': price_range_max}
        brands = Brand.objects.all().distinct('name')
        colors = Color.objects.all().distinct('color_code')

        results_serializer = ItemSerializer(results, many=True, context={'user_id': self.request.user.id}).data
        categories_serializer = ItemCategorySerializer(categories, many=True).data
        for category in categories_serializer:
            category['subcategories'] = ItemSubCategorySerializer(ItemSubCategory.objects.filter(category_id=category['id']), many=True).data
        subcategories_serializer = ItemSubCategorySerializer(subcategories, many=True).data
        brands_serializer = BrandSerializer(brands, many=True).data
        colors_serializer = ColorSerializer(colors, many=True).data
        context = {
            'query': query,
            'items': results_serializer,
            'categories': categories_serializer,
            'subcategories': subcategories_serializer,
            'price_range': price_range,
            'brands': brands_serializer,
            'colors': colors_serializer
        }
        
        return Response(context, status=status.HTTP_200_OK)


class AboutView(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        categories = ItemCategory.objects.filter(is_active=True)
        subcategories = ItemSubCategory.objects.filter(is_active=True)

        categories_serializer = ItemCategorySerializer(categories, many=True).data
        subcategories_serializer = ItemSubCategorySerializer(subcategories, many=True).data
        context = {
            'categories': categories_serializer,
            'subcategories': subcategories_serializer,
        }
        
        return Response(context, status=status.HTTP_200_OK)


class ContactView(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        categories = ItemCategory.objects.filter(is_active=True)
        subcategories = ItemSubCategory.objects.filter(is_active=True)

        categories_serializer = ItemCategorySerializer(categories, many=True).data
        subcategories_serializer = ItemSubCategorySerializer(subcategories, many=True).data
        context = {
            'categories': categories_serializer,
            'subcategories': subcategories_serializer,
        }
        
        return Response(context, status=status.HTTP_200_OK)


class PrivacyPolicyView(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        categories = ItemCategory.objects.filter(is_active=True)
        subcategories = ItemSubCategory.objects.filter(is_active=True)

        categories_serializer = ItemCategorySerializer(categories, many=True).data
        subcategories_serializer = ItemSubCategorySerializer(subcategories, many=True).data
        context = {
            'categories': categories_serializer,
            'subcategories': subcategories_serializer,
        }
        
        return Response(context, status=status.HTTP_200_OK)


class TermsConditionsView(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        categories = ItemCategory.objects.filter(is_active=True)
        subcategories = ItemSubCategory.objects.filter(is_active=True)

        categories_serializer = ItemCategorySerializer(categories, many=True).data
        subcategories_serializer = ItemSubCategorySerializer(subcategories, many=True).data
        context = {
            'categories': categories_serializer,
            'subcategories': subcategories_serializer,
        }
        
        return Response(context, status=status.HTTP_200_OK)


class FAQView(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        categories = ItemCategory.objects.filter(is_active=True)
        subcategories = ItemSubCategory.objects.filter(is_active=True)

        categories_serializer = ItemCategorySerializer(categories, many=True).data
        subcategories_serializer = ItemSubCategorySerializer(subcategories, many=True).data
        context = {
            'categories': categories_serializer,
            'subcategories': subcategories_serializer,
        }
        
        return Response(context, status=status.HTTP_200_OK)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.IsAuthenticated])
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False,
        ordered_date=timezone.now()
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            return Response({"message": "This item quantity was updated."}, status=status.HTTP_200_OK)
        else:
            order.items.add(order_item)
            return Response({"message": "This item was added to your cart."}, status=status.HTTP_200_OK)
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        return Response({"message": "This item was added to your cart."}, status=status.HTTP_200_OK)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.IsAuthenticated])
def add_items_to_cart(request, slug):
    try:
        item = get_object_or_404(Item, slug=slug)
        quantity = request.data['quantity']
        color = request.data['color']
        if int(quantity) > 0:
            if int(quantity) <= item.stock_count:
                order_item, created = OrderItem.objects.get_or_create(
                    item=item,
                    color = Color.objects.get(id=color),
                    user=request.user,
                    ordered=False
                )
                order_qs = Order.objects.filter(user=request.user, ordered=False)
                if order_qs.exists():
                    order = order_qs[0]
                    # check if the order item is in the order
                    if order.items.filter(item__slug=item.slug, color=Color.objects.get(id=color)).exists():
                        order_item.quantity = order_item.quantity + int(quantity)
                        order_item.save()
                        return Response({"message": "This order item was updated."}, status=status.HTTP_200_OK)
                    else:
                        order_item.quantity = int(quantity)
                        order_item.color = Color.objects.get(id=color)
                        order_item.save()
                        order.items.add(order_item)
                        return Response({"message": "This item was added to your cart."}, status=status.HTTP_200_OK)
                else:
                    ordered_date = timezone.now()
                    order = Order.objects.create(user=request.user, ordered_date=ordered_date)
                    order_item.quantity = int(quantity)
                    order_item.color = Color.objects.get(id=color)
                    order_item.save()
                    order.items.add(order_item)
                    return Response({"message": "This item was added to your cart."}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "The quantity cannot be more than "+str(item.stock_count)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"message": "The quantity cannot be less than zero."}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(e)
        return Response({"message": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.IsAuthenticated])
def add_single_item_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()

            my_items = OrderItem.objects.filter(user=request.user, ordered=False)
            data = serializers.serialize('json', my_items)
            order_items = json.loads(data)
            my_order = Order.objects.filter(user=request.user, ordered=False)
            data2 = serializers.serialize('json', my_order)
            my_order = json.loads(data2)
            # messages.success(request, "This item quantity was updated.")
            # return redirect("order-cart")
            return Response({'success': 'Success', 'order_items': order_items, 'my_order': my_order}, status=status.HTTP_200_OK)
        else:
            order.items.add(order_item)
            return Response({"message": "This item was added to your cart."}, status=status.HTTP_200_OK)
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        return Response({"message": "This item was added to your cart."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.IsAuthenticated])
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)

            my_items = OrderItem.objects.filter(
                user=request.user, ordered=False)
            data = serializers.serialize('json', my_items)
            order_items = json.loads(data)
            return Response({'status': 'Success', 'order_items': order_items}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "This item was not in your cart."}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({"message": "You do not have an active order."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.IsAuthenticated])
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            order_item.delete()

            return Response({"message": "This item was removed from your cart."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "This item was not in your cart."}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({"message": "You do not have an active order."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.IsAuthenticated])
def cancel_order(request, ref_code):
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=True,
        ref_code=ref_code
    )
    if order_qs.exists():
        order = order_qs.first()
        order.status = 4
        order.save()
    else:
        return Response({"message": "You do not have an active order."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def add_to_wishlist(request, slug):
    item = get_object_or_404(Item, slug=slug)
    Wishlist.objects.get_or_create(item=item, user=request.user)
    count = Wishlist.objects.filter(user=request.user).count()
    return JsonResponse({"count": count, "status": 200, "message": "Successfully Added To The Wishlist."})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def remove_from_wishlist(request, slug):
    item = get_object_or_404(Item, slug=slug)
    wishlist_item = Wishlist.objects.filter(
        item=item,
        user=request.user
    )
    if wishlist_item.exists():
        wishlist_item.delete()
        return Response({"message": "This item is removed from Wishlist."}, status=status.HTTP_200_OK)
    else:
        return Response({"message": "This item is not available in Wishlist."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@csrf_exempt
def subscribe(request):
    try:
        email_add = request.data['email']
        Subscribe.objects.create(email=email_add)
        return Response({"message": "Your subscription has been added."}, status=status.HTTP_200_OK)
    except ObjectDoesNotExist:
        return Response({"message": "This email does not exist."}, status=status.HTTP_400_BAD_REQUEST)
    except:
        return Response({"message": "Something went wrong."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
def contact_form(request):
    if request.method == "POST":
        try:
            name = request.data['name']
            email = request.data['email']
            subject = request.data['subject']
            message = request.data['message']
            contact_us = Contact.objects.create(name=name, email=email, subject=subject, message=message)

            subject = subject + " - Contact Fashion Fit"
            message = "Name: " + name + "\nEmail: " + email + "\nMessage: " + message
            try:
                send_mail(subject, message, email, [EMAIL_HOST_USER], fail_silently=False)
            except BadHeaderError:
                return Response({"message": "Invalid header found."}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": "Contact form submitted."}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({"message": "Required fields missing."}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({"message": "Something went wrong."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
def product_review(request, slug):
    if request.method == "POST":
        try:
            username = request.data['username']
            rating = request.data['rating']
            description = request.data['description']

            user = User.objects.get(username=username)
            item = Item.objects.get(slug=slug)
            Review.objects.create(user=user, item=item, rating=rating, description=description)

            return Response({"message": "You review has been submitted."}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"message": "Something went wrong."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BlogsView(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        posts = Post.objects.filter(status=1).order_by('-created_on')

        categories = ItemCategory.objects.filter(is_active=True)
        subcategories = ItemSubCategory.objects.filter(is_active=True)
        
        posts_serializer = PostSerializer(posts, many=True).data
        categories_serializer = ItemCategorySerializer(categories, many=True).data
        subcategories_serializer = ItemSubCategorySerializer(subcategories, many=True).data
        context = {
            'blogs': posts_serializer,
            'categories': categories_serializer,
            'subcategories': subcategories_serializer,
        }
        
        return Response(context, status=status.HTTP_200_OK)


class BlogView(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        posts = Post.objects.filter(slug=kwargs['slug']).first()
        categories = ItemCategory.objects.filter(is_active=True)
        
        posts_serializer = PostSerializer(posts).data
        categories_serializer = ItemCategorySerializer(categories, many=True).data
        context = {
            'blog': posts_serializer,
            'categories': categories_serializer,
        }
        
        return Response(context, status=status.HTTP_200_OK)


class OrderConfirmation(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        categories = ItemCategory.objects.filter(is_active=True)
        subcategories = ItemSubCategory.objects.filter(is_active=True)
        
        categories_serializer = ItemCategorySerializer(categories, many=True).data
        subcategories_serializer = ItemSubCategorySerializer(subcategories, many=True).data
        context = {
            'categories': categories_serializer,
            'subcategories': subcategories_serializer,
        }
        
        return Response(context, status=status.HTTP_200_OK)


class ThankYou(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        categories = ItemCategory.objects.filter(is_active=True)
        subcategories = ItemSubCategory.objects.filter(is_active=True)
        
        categories_serializer = ItemCategorySerializer(categories, many=True).data
        subcategories_serializer = ItemSubCategorySerializer(subcategories, many=True).data
        context = {
            'categories': categories_serializer,
            'subcategories': subcategories_serializer,
        }
        
        return Response(context, status=status.HTTP_200_OK)


class DashboardPage(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        profile = self.request.user
        categories = ItemCategory.objects.filter(is_active=True)
        subcategories = ItemSubCategory.objects.filter(is_active=True)
        
        categories_serializer = ItemCategorySerializer(categories, many=True).data
        subcategories_serializer = ItemSubCategorySerializer(subcategories, many=True).data
        context = {
            'profile': profile,
            'categories': categories_serializer,
            'subcategories': subcategories_serializer,
        }
        
        return Response(context, status=status.HTTP_200_OK)


class OrdersViewPage(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        orders = Order.objects.filter(user=self.request.user, ordered=True).order_by('-id')

        orders_serializer = OrderSerializer(orders, many=True).data
        context = {
            'orders': orders_serializer,
        }
        
        return Response(context, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_product_type(request, slug):
    all_items = Item.objects.filter(product_type=slug).order_by('-id')
    categories = ItemCategory.objects.filter(is_active=True)
    subcategories = ItemSubCategory.objects.filter(is_active=True)
    price_range_min = Item.objects.all().aggregate(Min('price'))
    price_range_max = Item.objects.all().aggregate(Max('price'))
    price_range = {'min': price_range_min, 'max': price_range_max}
    brands = Brand.objects.all().distinct('name')
    colors = Color.objects.all().distinct('color_code')

    all_items_serializer = ItemSerializer(all_items, many=True, context={'user_id': request.user.id}).data
    categories_serializer = ItemCategorySerializer(categories, many=True).data
    for category in categories_serializer:
        category['subcategories'] = ItemSubCategorySerializer(ItemSubCategory.objects.filter(category_id=category['id']), many=True).data
    subcategories_serializer = ItemSubCategorySerializer(subcategories, many=True).data
    brands_serializer = BrandSerializer(brands, many=True).data
    colors_serializer = ColorSerializer(colors, many=True).data
    context = {
        'items':  all_items_serializer,
        'categories':  categories_serializer,
        'subcategories':  subcategories_serializer,
        'price_range': price_range,
        'brands': brands_serializer,
        'colors': colors_serializer,
        'category': ItemCategorySerializer(category).data,
    }
    return Response(context, status=status.HTTP_200_OK)


class CategoriesView(APIView):

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        categories = ItemCategory.objects.filter(is_active=True)
        subcategories = ItemSubCategory.objects.filter(is_active=True)
        
        categories_serializer = ItemCategorySerializer(categories, many=True).data
        subcategories_serializer = ItemSubCategorySerializer(subcategories, many=True).data
        context = {
            'categories': categories_serializer,
            'subcategories': subcategories_serializer,
        }
        
        return Response(context, status=status.HTTP_200_OK)

  
class AddressView(APIView):
    
    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        try:
            addresses = Address.objects.filter(user=self.request.user)

            address_serializer = AddressSerializer(addresses, many=True).data
            context = {
                'addresses': address_serializer,
            }
            return Response(context, status=status.HTTP_200_OK)
        except:
            return Response({"message": "Something went wrong."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(ratelimit(method='POST', key='ip', rate='10/s', block=True))
    def post(self, *args, **kwargs):
        try:
            full_name = self.request.data['full_name']
            phone_number = self.request.data['phone_number']
            street_address = self.request.data['street_address']
            apartment_address = self.request.data['apartment_address']
            default = self.request.data['default']

            if default == "true":
                addresses = Address.objects.filter(user=self.request.user, default=True).first()
                if addresses:
                    addresses.default = False
                    addresses.save()
            
            address = Address()
            address.user = self.request.user
            address.full_name = full_name
            address.phone_number = phone_number
            address.street_address = street_address
            address.apartment_address = apartment_address
            addresses = Address.objects.filter(user=self.request.user).first()
            if addresses:
                address.default = True if (default == "true") else False
            else:
                address.default = True

            address.save()

            address_serializer = AddressSerializer(address).data

            return Response({"message": "Your address was successful added!", "address": address_serializer}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"message": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateAddressView(APIView):
        
    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def get(self, *args, **kwargs):
        try:
            address = Address.objects.get(id=kwargs['address_id'])

            address_serializer = AddressSerializer(address).data
            context = {
                'address': address_serializer,
            }
            return Response(context, status=status.HTTP_200_OK)
        except:
            return Response({"message": "Something went wrong."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(ratelimit(method='POST', key='ip', rate='10/s', block=True))
    def patch(self, *args, **kwargs):
        try:
            address_id = kwargs['address_id']
            full_name = self.request.data['full_name']
            phone_number = self.request.data['phone_number']
            street_address = self.request.data['street_address']
            apartment_address = self.request.data['apartment_address']
            default = self.request.data['default']

            if default == "true":
                addresses = Address.objects.filter(user=self.request.user, default=True).first()
                if addresses:
                    addresses.default = False
                    addresses.save()
            
            address = Address.objects.get(id=address_id)
            address.full_name = full_name
            address.phone_number = phone_number
            address.street_address = street_address
            address.apartment_address = apartment_address
            address.default = True if (default == "true") else False
            address.save()

            return Response({"message": "Your address was successful updated!"}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"message": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    @method_decorator(ratelimit(method='POST', key='ip', rate='10/s', block=True))
    def delete(self, *args, **kwargs):
        try:
            address = Address.objects.get(id=kwargs['address_id'])
            address.delete()

            return Response({"message": "Your address was successful removed!"}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"message": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

  
class FilterProductView(APIView):

    @method_decorator(ratelimit(method='POST', key='ip', rate='10/s', block=True))
    def post(self, *args, **kwargs):
        try:
            filters = self.request.data['filters']

            # problem: get only distinct product
            
            items = Item.objects.filter(is_active=True)
            if filters['search_query']:
                items = items.filter(Q(name__icontains=filters['search_query']), is_active=True)
            if filters['categories']:
                items = items.filter(category__slug__in=list(set(filters['categories'])))
            if filters['subcategories']:
                items = items.filter(subcategory__slug__in=list(set(filters['subcategories'])))
            if filters['sizes']:
                items = items.filter(size__size_code__in=list(set(filters['sizes'])))
            if filters['brands']:
                items = items.filter(brand__slug__in=list(set(filters['brands'])))
            if filters['price_range']:
                items = items.filter(price__range=filters['price_range'])
            
            items = items.order_by('-id')
            if filters['sort']:
                if filters['sort'] == "price_low":
                    items = items.order_by('price')
                elif filters['sort'] == "price_high":
                    items = items.order_by('-price')
                else:
                    pass

            # serializers
            items_serializers = ItemSerializer(items, many=True, context={'user_id': self.request.user.id}).data

            context = {
                "items": items_serializers,
            }
            return Response(context, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"message": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
