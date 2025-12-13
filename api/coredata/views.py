from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, inline_serializer
from .constants import CURRENCIES, COUNTRIES, TIMEZONES


@extend_schema(
    tags=['Core Data'],
    summary='列出貨幣 / List currencies',
    description='獲取系統支持的貨幣列表。\n\nGet list of supported currencies.',
    responses=inline_serializer(
        name='CurrencyListResponse',
        fields={
            'success': serializers.BooleanField(),
            'data': serializers.ListField(),
            'count': serializers.IntegerField(),
        }
    )
)
@api_view(['GET'])
@permission_classes([AllowAny])
def currency_list(request):
    return Response({
        'success': True,
        'data': CURRENCIES,
        'count': len(CURRENCIES)
    })


@extend_schema(
    tags=['Core Data'],
    summary='列出國家 / List countries',
    description='獲取系統支持的國家列表。\n\nGet list of supported countries.',
    responses=inline_serializer(
        name='CountryListResponse',
        fields={
            'success': serializers.BooleanField(),
            'data': serializers.ListField(),
            'count': serializers.IntegerField(),
        }
    )
)
@api_view(['GET'])
@permission_classes([AllowAny])
def country_list(request):
    return Response({
        'success': True,
        'data': COUNTRIES,
        'count': len(COUNTRIES),
    })


@extend_schema(
    tags=['Core Data'],
    summary='列出時區 / List timezones',
    description='獲取系統支持的時區列表。\n\nGet list of supported timezones.',
    responses=inline_serializer(
        name='TimezoneListResponse',
        fields={
            'success': serializers.BooleanField(),
            'data': serializers.ListField(),
            'count': serializers.IntegerField(),
        }
    )
)
@api_view(['GET'])
@permission_classes([AllowAny])
def timezone_list(request):
    return Response({
        'success': True,
        'data': TIMEZONES,
        'count': len(TIMEZONES)
    })
