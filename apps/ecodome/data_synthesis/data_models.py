from typing import List
from langchain_core.pydantic_v1 import BaseModel, Field, validator

class LCAMetricData(BaseModel):
    name: str = Field(..., description="name of the chemical")
    value: str = Field(..., description="the quantity it is used in the process (strictly in integers)")
    unit: str = Field(..., description="unit of measurment of the quantity")

    @validator('value')
    def validate_value(cls, value):
        if not value.isdigit():
            raise ValueError("Value must be a valid integer")
        return value
    
    @validator('unit')
    def validate_unit(cls, unit):
        if not unit.isalpha():
            raise ValueError('Unit must contain alphabets only')
        return unit

class LCAData(BaseModel):
    lca_metrics: List[LCAMetricData] = Field(..., description="break down each of these processes into seperate LCAMetricData")

class EPDData(BaseModel):
    description: str = Field(..., description="description of the environmental product data found on the internet")

class ReportData(BaseModel):
    summary: str = Field(..., description="summary of the EPD data and the LCA Metrics Data")

class EnvironmentTag(BaseModel):
    tag_name: str = Field(..., description="name of the environment tag")

class ProductEnvironmentTags(BaseModel):
    env_tags: List[EnvironmentTag] = Field(..., description="all the environment tags associated with this product")