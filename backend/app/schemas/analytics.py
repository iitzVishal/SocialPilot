from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class EngagementMetricsSummary(BaseModel):
    total_engagements: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    clicks: int = 0
    views: int = 0
    impressions: int = 0
    reach: int = 0
    engagement_rate: float = 0.0


class EngagementAnalyticsResponse(BaseModel):
    period_days: int
    period_start: str
    period_end: str
    summary: EngagementMetricsSummary
    daily_trend: List[Dict[str, Any]]
    platform_breakdown: List[Dict[str, Any]]
    top_posts: List[Dict[str, Any]]
    available: bool = True
    notice: Optional[str] = None


class AudienceGrowthResponse(BaseModel):
    period_days: int
    period_start: str
    period_end: str
    total_followers: int = 0
    net_growth: int = 0
    growth_rate: float = 0.0
    by_platform: List[Dict[str, Any]]
    growth_trend: List[Dict[str, Any]]
    accounts: List[Dict[str, Any]]
    available: bool = True
    notice: Optional[str] = None


class CampaignROISummary(BaseModel):
    campaign_id: int
    name: str
    status: str
    budget: float = 0.0
    revenue: float = 0.0
    net_profit: float = 0.0
    roi_percentage: Optional[float] = None
    total_engagements: int = 0
    total_clicks: int = 0
    total_impressions: int = 0
    cost_per_engagement: Optional[float] = None
    cost_per_click: Optional[float] = None
    cost_per_mille: Optional[float] = None


class ROIAnalyticsResponse(BaseModel):
    period_days: int
    total_budget: float = 0.0
    total_revenue: float = 0.0
    total_net_profit: float = 0.0
    overall_roi_percentage: Optional[float] = None
    total_engagements: int = 0
    total_clicks: int = 0
    total_impressions: int = 0
    cost_per_engagement: Optional[float] = None
    cost_per_click: Optional[float] = None
    cost_per_mille: Optional[float] = None
    campaigns: List[CampaignROISummary]
    formula_explanation: Dict[str, str] = Field(
        default_factory=lambda: {
            "roi": "((Revenue - Budget) / Budget) * 100 when Budget > 0",
            "cpe": "Budget / Total Engagements when Engagements > 0",
            "cpc": "Budget / Total Clicks when Clicks > 0",
            "cpm": "(Budget / Impressions) * 1000 when Impressions > 0",
        }
    )


class AnalyticsSyncResponse(BaseModel):
    status: str
    team_id: int
    total_accounts: int
    synced_accounts: int
    failed_accounts: int
    account_results: List[Dict[str, Any]]
    post_metrics_synced: int = 0
    synced_at: str
