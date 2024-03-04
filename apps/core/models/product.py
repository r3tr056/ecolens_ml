import base64
import zlib
import requests
from datetime import datetime
from io import BytesIO
from sqlalchemy import Integer, Boolean, String, Float, Date, ForeignKey, Column, Text, DateTime, Numeric, LargeBinary
from sqlalchemy.orm import relationship, class_mapper
from apps.core.db import Base
from PIL import Image

def to_dict(instance, include_relationships=True):
    """ Converts a SQL alchemy model instance to a dict """
    columns = [column.key for column in class_mapper(instance.__class__).columns]
    result = {column: getattr(instance, column) for column in columns}

    if include_relationships:
        for rel in class_mapper(instance.__class__).relationships:
            related_obj = getattr(instance, rel.key)
            if related_obj is not None:
                if rel.uselist:
                    result[rel.key] = [to_dict(obj, include_relationships=False) for obj in related_obj]
                else:
                    result[rel.key] = to_dict(related_obj, include_relationships=False)

    return result

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    
    products = relationship("Product", back_populates='category')

class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    desc = Column(String)
    country = Column(String)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    brand = relationship('Brand', backref='products')
    brand_id = Column(Integer, ForeignKey('brands.id'), nullable=False)
    barcode = Column(String, nullable=False, unique=True)
    # For the product images
    images = relationship('ProductImage', backref='product', lazy=True)
    marketplace_alternatives = relationship('MarketPlaceProduct', backref='product', lazy=True)
    epd = relationship('EnvironmentalProductDeclaration', backref='product', uselist=False, lazy='joined', cascade='all, delete-orphan')
    data_quality = Column(Boolean)
    # user reviews and ratings
    user_reviews = relationship('UserReview', backref='product', lazy=True)
    average_rating = Column(Float, default=0.0)

    def analyze_marketplace_alternatives(self):
        # Method for analyzing marketplace to find suitable alternatvies
        pass

    def analyze_data_quality(self):
        pass

    def update_epd(self, epd_data):
        pass

    def update_lca_metrics(self, metrics_data):
        pass

    def add_user_review(self, user_review):
        self.user_reviews.append(user_review)

    @classmethod
    def create_from_data(cls, product_name, product_desc, barcode_data, image_results):
        product_instance = cls(
            name=product_name,
            barcode=barcode_data if barcode_data else '',
            desc=product_desc,
        )

        for image_url in image_results:
            product_instance.images.append(ProductImage.create_from_url(
                product_id=product_instance.id,
                image_url=image_url,
            ))

        return cls

    def update_average_rating(self):
        total_ratings = len(self.user_reviews)
        if total_ratings == 0:
            self.average_rating = 0.0
        else:
            total_sum = sum(review.rating for review in self.user_reviews)
            self.average_rating = total_sum / total_ratings

    def convert_ratings_for_ml(self):
        pass

class MarketPlaceProduct(Product):
    __tablename__ = "marketplace_products"

    id = Column(Integer, ForeignKey('products.id'), primary_key=True)

    stock = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    pub_date = Column(DateTime, nullable=False, default=datetime.now())
    
    quantity = Column(Integer)
    expiry_date = Column(Date)
    date_of_manufacture = Column(Date)
    # Extra fields
    weight = Column(Numeric(6,2))
    dimensions = Column(String)
    color = Column(String)
    material = Column(String)

    def __init__(self, *args, **kwargs):
        super(MarketPlaceProduct, self).__init__(*args, **kwargs)


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    # the product image is base64 encoded and gzip compressed binary
    image = Column(LargeBinary, nullable=False)

    @classmethod
    def create_from_data(cls, product_id, image_data):
        compressed_image = cls.compress_and_encode(image_data)
        return cls(product_id=product_id, image=compressed_image)
    
    @staticmethod
    def compress_and_encode(data):
        compressed_data = zlib.compress(data)
        base64_encoded = base64.b64encode(compressed_data)
        return base64_encoded
    
    @classmethod
    def create_from_url(cls, product_id, image_url):
        response = requests.get(image_url)
        if response.status_code == 200:
            image_data = cls.read_image_data(response.content)
            return cls.create_from_data(product_id, image_data)
        else:
            raise Exception(f"Failed to download image from {image_url}, status code : {response.status_code}")
        
    @classmethod
    def read_image_data(image_content):
        image = Image.open(BytesIO(image_content))
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        return buffered.getvalue()

class EnvironmentTag(Base):
    __tablename__ = 'env_tag'

    id = Column(Integer, primary_key=True)
    name = Column(String)

    product_id = Column(Integer, ForeignKey('products.id'))
    product = relationship('Product', back_populates='details')

