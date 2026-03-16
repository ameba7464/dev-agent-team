"""
Pydantic v2 models for WB API responses.
"""
from pydantic import BaseModel
from typing import Optional


# --- nm-report models ---

class NmDayStat(BaseModel):
    startDate: str
    endDate: str
    views: int = 0
    clicks: int = 0
    addToCartCount: int = 0
    buyoutsCount: int = 0
    buyoutsSumRub: float = 0.0


class NmReportItem(BaseModel):
    nmID: int
    vendorCode: str
    imtName: str
    statistics: list[NmDayStat] = []

    # Aggregated totals — populated by wb_client after parsing
    total_views: int = 0
    total_clicks: int = 0
    total_cart: int = 0
    total_buyouts: int = 0
    total_sum_rub: float = 0.0


class NmReportResponse(BaseModel):
    data: list[NmReportItem] = []
    error: bool = False
    errorText: str = ""


# --- nm-report detail (for listing nm_ids) ---

class NmDetailCard(BaseModel):
    nmID: int
    vendorCode: str = ""
    imtName: str = ""


class NmDetailData(BaseModel):
    cards: list[NmDetailCard] = []
    isNextPage: bool = False


class NmDetailResponse(BaseModel):
    data: NmDetailData = NmDetailData()
    error: bool = False
    errorText: str = ""


# --- Advert API models ---

class AdvertCampaign(BaseModel):
    advertId: int
    name: str = ""
    status: int = 0
    type: int = 0


class AdvertNmStat(BaseModel):
    nmId: int
    views: int = 0
    clicks: int = 0
    sum: float = 0.0       # ad spend for this nm on this day
    atbs: int = 0
    orders: int = 0
    shks: int = 0
    sum_price: float = 0.0


class AdvertAppStat(BaseModel):
    appType: int
    nm: list[AdvertNmStat] = []


class AdvertDayStat(BaseModel):
    date: str
    apps: list[AdvertAppStat] = []


class AdvertCampaignStat(BaseModel):
    advertId: int
    days: list[AdvertDayStat] = []
