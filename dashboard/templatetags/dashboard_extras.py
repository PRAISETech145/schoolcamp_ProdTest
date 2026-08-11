"""
Custom template tags for dashboard app.
Provides filters for chart data serialization.
"""

from django import template

register = template.Library()


@register.filter
def get_xp_labels(monthly_stats):
    """Extract month labels for XP chart."""
    return [ms['month'] for ms in monthly_stats]


@register.filter
def get_xp_data(monthly_stats):
    """Extract XP data for XP chart."""
    return [ms['xp'] for ms in monthly_stats]


@register.filter
def get_labels(type_stats):
    """Extract activity type labels for doughnut chart."""
    return [ts['activity_type'].replace('_', ' ').title() for ts in type_stats]


@register.filter
def get_counts(type_stats):
    """Extract activity counts for doughnut chart."""
    return [ts['count'] for ts in type_stats]


@register.filter
def get_months(xp_progression):
    """Extract month labels for progression chart."""
    return [xp['month'] for xp in xp_progression]


@register.filter
def get_cumulative(xp_progression):
    """Extract cumulative XP data for progression chart."""
    return [xp['cumulative_xp'] for xp in xp_progression]


@register.filter
def get_sum_attrs(items, attr):
    """Sum a specific attribute across a list of objects/dicts."""
    try:
        return sum(getattr(item, attr, item.get(attr, 0)) for item in items)
    except (TypeError, AttributeError):
        return 0