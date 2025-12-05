from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .constants import CURRENCIES, COUNTRIES, TIMEZONES


@api_view(['GET'])
@permission_classes([AllowAny])
def currency_list(request):
    return Response({
        'success': True,
        'data': CURRENCIES,
        'count': len(CURRENCIES)
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def country_list(request):
    return Response({
        'success': True,
        'data': COUNTRIES,
        'count': len(COUNTRIES),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def timezone_list(request):
    return Response({
        'success': True,
        'data': TIMEZONES,
        'count': len(TIMEZONES)
    })
