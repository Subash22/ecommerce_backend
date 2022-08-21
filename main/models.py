from django.db import models
from django.shortcuts import reverse
from django.utils.text import slugify
from django.utils.html import mark_safe
# from smart_selects.db_fields import ChainedForeignKey
from django.conf import settings
from tinymce import models as tinymce_models

# Create your models here.
STATUS = (
    (0,"Draft"),
    (1,"Publish")
)

PAYMENT_STATUS = (
    (0,"Pending"),
    (1,"Approved"),
    (2,"Rejected")
)

ORDER_STATUS = (
    (0,"Pending"),
    (1,"Processing"),
    (2,"Being Delivered"),
    (3,"Received"),
    (4,"Canceled"),
    (5,"Refund Requested"),
    (6,"Refund Granted")
)

PRODUCT_TYPES = (
    ('Mobile', 'Mobile'),
    ('Laptop', 'Laptop'),
    ('Accessories', 'Accessories')
)

OFFER_IMAGES = (
    ('SI', 'Slider Image'),
    ('BI', 'Banner Image')
)

class ItemCategory(models.Model):
    name = models.CharField(max_length=100)
    category_type = models.CharField(choices=PRODUCT_TYPES, max_length=20)
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name + "(" + self.category_type + ")"

    def get_absolute_url(self):
        return reverse("category", kwargs={
            'slug': self.slug
        })

    class Meta:
        verbose_name_plural = "Categories"
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(ItemCategory, self).save(*args, **kwargs)


class ItemSubCategory(models.Model):
    category = models.ForeignKey(ItemCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name + "(" + self.category.category_type + ")"
        
    def get_absolute_url(self):
        return reverse("subcategory", kwargs={
            'slug1': self.category.slug,
            'slug': self.slug
        })

    class Meta:
        verbose_name_plural = "Sub Categories"

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(ItemSubCategory, self).save(*args, **kwargs)


class Brand(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(blank=True, null=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("brand", kwargs={
            'slug': self.slug
        })

    def image_tag(self):
        return mark_safe(f'<img src="{self.image.url}" width="50" height="50" />')

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Brand, self).save(*args, **kwargs)


class Color(models.Model):
    name = models.CharField(max_length=100)
    color_code = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ItemImage(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def image_tag(self):
        return mark_safe(f'<img src="{self.image.url}" width="50" height="50" />')


class Item(models.Model):
    name = models.CharField(max_length=100)
    cost_price = models.FloatField(help_text="Enter your cost price.", default=0)
    price = models.FloatField(help_text="Enter your selling price.", default=0)
    discount_price = models.FloatField(help_text="Enter the discounted price.", blank=True, null=True, default=0)
    product_type = models.CharField(choices=PRODUCT_TYPES, max_length=20)
    category = models.ForeignKey(ItemCategory, on_delete=models.SET_NULL, blank=True, null=True)
    subcategory = models.ForeignKey(ItemSubCategory, on_delete=models.SET_NULL, blank=True, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, blank=True, null=True)
    color = models.ManyToManyField(Color)
    images = models.ManyToManyField(ItemImage)
    description = tinymce_models.HTMLField()
    stock_count = models.IntegerField(default=0)
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("product", kwargs={
            'slug': self.slug
        })

    def get_add_to_cart_url(self):
        return reverse("add-to-cart", kwargs={
            'slug': self.slug
        })
        
    def get_add_items_to_cart_url(self):
        return reverse("add-items-to-cart", kwargs={
            'slug': self.slug
        })

    def get_remove_from_cart_url(self):
        return reverse("remove-from-cart", kwargs={
            'slug': self.slug
        })
        
    def get_add_to_wishlist_url(self):
        return reverse("add-to-wishlist", kwargs={
            'slug': self.slug
        })

    def get_remove_from_wishlist_url(self):
        return reverse("remove-from-wishlist", kwargs={
            'slug': self.slug
        })

    def image_tag(self):
        for image in self.images.all():
            return mark_safe(f'<img src="{image.image.url}" width="50" height="50" />')

    def get_profit_loss(self):
        if self.discount_price == 0:
            return self.price - self.cost_price
        else:
            return self.discount_price - self.cost_price

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Item, self).save(*args, **kwargs)


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    def __str__(self):
        return self.item.name


class OrderItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ordered = models.BooleanField(default=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    selling_price = models.FloatField(default=0)
    profit_loss = models.FloatField(default=0)
    quantity = models.IntegerField(default=1)
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, blank=True, null=True)
    ordered_date = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"{self.quantity} of {self.item.name}({self.size}x{self.color})"

    def get_total_item_price(self):
        return self.quantity * self.item.price

    def save(self, *args, **kwargs):
        discount_price = float(0 if self.item.discount_price is None else self.item.discount_price)
        if discount_price != 0:
            self.selling_price = discount_price
        else:
            self.selling_price  = self.item.price
        self.profit_loss = (float(self.selling_price) - float(self.item.cost_price)) * float(self.quantity)
        super(OrderItem, self).save(*args, **kwargs)

    def get_total_discount_item_price(self):
        return self.quantity * self.item.discount_price

    def get_amount_saved(self):
        return self.get_total_item_price() - self.get_total_discount_item_price()

    def get_final_price(self):
        if self.item.discount_price:
            return round(self.get_total_discount_item_price(),2)
        return round(self.get_total_item_price(),2)


class PaymentMethod(models.Model):
    payment_name = models.CharField(max_length=100)
    payment_code = models.CharField(unique=True, max_length=3)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.payment_name

    def image_tag(self):
        return mark_safe(f'<img src="{self.image.url}" width="50" height="50" />')


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=100)
    street_address = models.CharField(max_length=100)
    apartment_address = models.CharField(max_length=100)
    default = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name_plural = 'Addresses'


class Coupon(models.Model):
    code = models.CharField(max_length=15, unique=True)
    amount = models.FloatField()
    min_total = models.FloatField()

    def __str__(self):
        return self.code


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ref_code = models.CharField(max_length=20, blank=True, null=True)
    items = models.ManyToManyField(OrderItem)
    start_date = models.DateTimeField(auto_now_add=True)
    ordered_date = models.DateTimeField()
    ordered = models.BooleanField(default=False)
    shipping_address = models.ForeignKey(Address, related_name='shipping_address', on_delete=models.SET_NULL, blank=True, null=True)
    payment = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, blank=True, null=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, blank=True, null=True)
    total_price = models.FloatField(blank=True, null=True, default=0)
    order_note = models.CharField(max_length=200, blank=True, null=True)
    status = models.IntegerField(choices=ORDER_STATUS, blank=True, null=True)
    total_profit_loss = models.FloatField(default=0)

    '''
    1. Item added to cart
    2. Adding a shipping address
    (Failed checkout)
    3. Payment
    (Preprocessing, processing, packaging etc.)
    4. Being delivered
    5. Received
    6. Refunds
    '''

    def __str__(self):
        return self.user.username

    def get_total_profit_loss(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.profit_loss
        return total

    def get_subtotal(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.get_final_price()
        return total

    def get_total(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.get_final_price()
        if self.coupon:
            total -= self.coupon.amount
        return round(total, 2)


class Refund(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    reason = models.TextField()
    accepted = models.BooleanField(default=False)
    email = models.EmailField()

    def __str__(self):
        return f"{self.pk}"


class Subscribe(models.Model):
    email = models.CharField(max_length=50)

    def __str__(self):
        return self.email

    
class Contact(models.Model):
    name = models.CharField(max_length=50)
    email = models.CharField(max_length=50)
    subject = models.CharField(max_length=200)
    message = models.TextField()

    def __str__(self):
        return self.name


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    rating = models.IntegerField()
    description = models.TextField()
    review_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name_plural = "Reviews"


class Post(models.Model):
    title = models.CharField(max_length=200, unique=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.CASCADE)
    content = models.TextField()
    image = models.ImageField(upload_to='blog')
    metades = models.CharField(max_length=300, default="new post")
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    slug = models.SlugField(max_length=200, unique=True)
    status = models.IntegerField(choices=STATUS, default=0)

    class Meta:
        ordering = ['-created_on']

    def __str__(self):
        return self.title
        
    def image_tag(self):
        return mark_safe(f'<img src="{self.image.url}" width="50" height="50" />')


class Offer(models.Model):
    title = models.CharField(max_length=100)
    sub_title = models.CharField(max_length=100, blank=True, null=True)
    offer_type = models.CharField(choices=OFFER_IMAGES, max_length=2)
    image = models.ImageField(upload_to='offers')

    def __str__(self):
        return self.title
        
    def image_tag(self):
        return mark_safe(f'<img src="{self.image.url}" width="50" height="50" />')

