from rest_framework import serializers


class ForecastQuerySerializer(serializers.Serializer):
    district = serializers.CharField(required=True)
    city = serializers.CharField(required=True)

    # ! Index dia
    #  0 = today,
    #  1 = tomorrow, ...,
    #  9 = +9 days
    index_day = serializers.IntegerField(
        required=True,
        min_value=0,
        max_value=9,
    )

    use_cache = serializers.BooleanField(required=False)
    use_selenium_for_locations = serializers.BooleanField(required=False)
