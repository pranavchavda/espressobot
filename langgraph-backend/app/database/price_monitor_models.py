from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, ForeignKey, Text, ARRAY
from sqlalchemy.types import DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class IdcProduct(Base):
    __tablename__ = "idc_products"
    
    id = Column(String, primary_key=True)
    shopify_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    vendor = Column(String, nullable=False)
    product_type = Column(String)
    handle = Column(String)
    sku = Column(String)
    price = Column(DECIMAL(10, 2))
    compare_at_price = Column(DECIMAL(10, 2))
    available = Column(Boolean, default=True, nullable=False)
    image_url = Column(String)
    description = Column(String)
    features = Column(String)
    embedding = Column(String)
    last_synced_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    brand_id = Column(String, ForeignKey("monitored_brands.id"), nullable=False)
    inventory_quantity = Column(Integer)
    
    # Relationships
    monitored_brand = relationship("MonitoredBrand", back_populates="idc_products")
    product_matches = relationship("ProductMatch", back_populates="idc_product", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )

class CompetitorProduct(Base):
    __tablename__ = "competitor_products"
    
    id = Column(String, primary_key=True)
    external_id = Column(String, nullable=False)
    competitor_id = Column(String, ForeignKey("competitors.id"), nullable=False)
    title = Column(String, nullable=False)
    vendor = Column(String)
    product_type = Column(String)
    handle = Column(String)
    sku = Column(String)
    price = Column(DECIMAL(10, 2))
    compare_at_price = Column(DECIMAL(10, 2))
    available = Column(Boolean, default=True, nullable=False)
    image_url = Column(String)
    product_url = Column(String)
    description = Column(String)
    features = Column(String)
    embedding = Column(String)
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    competitor = relationship("Competitor", back_populates="competitor_products")
    price_history = relationship("PriceHistory", back_populates="competitor_product", cascade="all, delete-orphan")
    product_matches = relationship("ProductMatch", back_populates="competitor_product", cascade="all, delete-orphan")
    
    # Indexes and constraints
    __table_args__ = (
        {"extend_existing": True}
    )

class ProductMatch(Base):
    __tablename__ = "product_matches"
    
    id = Column(String, primary_key=True)
    idc_product_id = Column(String, ForeignKey("idc_products.id", ondelete="CASCADE"), nullable=False)
    competitor_product_id = Column(String, ForeignKey("competitor_products.id", ondelete="CASCADE"), nullable=False)
    overall_score = Column(Float, nullable=False)
    brand_similarity = Column(Float)
    title_similarity = Column(Float)
    embedding_similarity = Column(Float)
    price_similarity = Column(Float)
    price_difference = Column(DECIMAL(10, 2))
    price_difference_percent = Column(Float)
    is_map_violation = Column(Boolean, default=False, nullable=False)
    violation_amount = Column(DECIMAL(10, 2))
    violation_percentage = Column(Float)
    first_violation_date = Column(DateTime)
    last_checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_manual_match = Column(Boolean, default=False, nullable=False)
    is_rejected = Column(Boolean, default=False, nullable=False)
    confidence_level = Column(String, default="low", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    idc_product = relationship("IdcProduct", back_populates="product_matches")
    competitor_product = relationship("CompetitorProduct", back_populates="product_matches")
    price_alerts = relationship("PriceAlert", back_populates="product_match", cascade="all, delete-orphan")
    violation_history = relationship("ViolationHistory", back_populates="product_match", cascade="all, delete-orphan")
    
    # Indexes and constraints
    __table_args__ = (
        {"extend_existing": True}
    )

class Competitor(Base):
    __tablename__ = "competitors"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    domain = Column(String, unique=True, nullable=False)
    collections = Column(ARRAY(String), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    scrape_schedule = Column(String)
    rate_limit_ms = Column(Integer, default=2000, nullable=False)
    last_scraped_at = Column(DateTime)
    total_products = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    exclude_patterns = Column(ARRAY(String), default=[], nullable=False)
    scraping_strategy = Column(String, default="collections", nullable=False)
    search_terms = Column(ARRAY(String), default=[], nullable=False)
    url_patterns = Column(ARRAY(String), default=[], nullable=False)
    
    # Relationships
    competitor_products = relationship("CompetitorProduct", back_populates="competitor", cascade="all, delete-orphan")
    scrape_jobs = relationship("ScrapeJob", back_populates="competitor", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )

class MonitoredBrand(Base):
    __tablename__ = "monitored_brands"
    
    id = Column(String, primary_key=True)
    brand_name = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    idc_products = relationship("IdcProduct", back_populates="monitored_brand", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )

class MonitoredCollection(Base):
    __tablename__ = "monitored_collections"
    
    id = Column(String, primary_key=True)
    collection_name = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )

class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(String, primary_key=True)
    competitor_product_id = Column(String, ForeignKey("competitor_products.id", ondelete="CASCADE"), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    compare_at_price = Column(DECIMAL(10, 2))
    available = Column(Boolean, default=True, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    competitor_product = relationship("CompetitorProduct", back_populates="price_history")
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )

class PriceAlert(Base):
    __tablename__ = "price_alerts"
    
    id = Column(String, primary_key=True)
    product_match_id = Column(String, ForeignKey("product_matches.id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    severity = Column(String, default="medium", nullable=False)
    old_price = Column(DECIMAL(10, 2))
    new_price = Column(DECIMAL(10, 2))
    price_change = Column(DECIMAL(10, 2))
    status = Column(String, default="unread", nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    product_match = relationship("ProductMatch", back_populates="price_alerts")
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )

class ViolationHistory(Base):
    __tablename__ = "violation_history"
    
    id = Column(String, primary_key=True)
    product_match_id = Column(String, ForeignKey("product_matches.id", ondelete="CASCADE"), nullable=False)
    violation_type = Column(String, nullable=False)
    competitor_price = Column(DECIMAL(10, 2), nullable=False)
    idc_price = Column(DECIMAL(10, 2), nullable=False)
    violation_amount = Column(DECIMAL(10, 2), nullable=False)
    violation_percent = Column(Float, nullable=False)
    previous_price = Column(DECIMAL(10, 2))
    price_change = Column(DECIMAL(10, 2))
    screenshot_url = Column(String)
    competitor_url = Column(String)
    notes = Column(String)
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    product_match = relationship("ProductMatch", back_populates="violation_history")
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )

class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"
    
    id = Column(String, primary_key=True)
    competitor_id = Column(String, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="pending", nullable=False)
    collections = Column(ARRAY(String), nullable=False)
    products_found = Column(Integer)
    products_updated = Column(Integer)
    products_created = Column(Integer)
    errors = Column(String)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    competitor = relationship("Competitor", back_populates="scrape_jobs")
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )