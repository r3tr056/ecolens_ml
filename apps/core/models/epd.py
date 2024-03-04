from sqlalchemy import Integer, String, Float, Date, ForeignKey, Column, Text, DateTime, Numeric
from sqlalchemy.orm import relationship
from apps.core.db import Base

class EnvironmentalProductDecleration(Base):
    __tablename__ = "epds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product = relationship('Product', backref='epd')
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    description = Column(String)
    lca_metrics = relationship('LCAMetric', backref='epd')

    @classmethod
    def from_epd_data(cls, epd_data, product_id):
        return cls(
            product_id=product_id,
            description=epd_data.description
        )

class LCAMetric(Base):
    __tablename__ = "lca_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    value = Column(Numeric(10, 2))
    unit = Column(String)
    epd_id = Column(Integer, ForeignKey('epds.id'), nullable=False)
    epd = relationship('EnvironmentalProductDecleration', backref='lca_metrics')

    @classmethod
    def from_lca_metric_data(cls, lca_metric_data, epd_id):
        return cls(
            name=lca_metric_data.name,
            value=float(lca_metric_data.value),
            unit=lca_metric_data.unit,
            epd_id=epd_id
        )