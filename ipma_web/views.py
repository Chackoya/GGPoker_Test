# ipma_web/views.py

import requests
from bs4 import BeautifulSoup
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

from .serializers import ForecastQuerySerializer
from ipma_web.utils.scraping import IpmaWebScriptLib
from ipma_web.utils.configs import ALLOWED_DISTRICTS


class ForecastAPIView(APIView):

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="district",
                description="Name district (example 'Coimbra')",
                required=True,
                type=str,
                examples=[OpenApiExample("Exemplo de Distrito", value="Coimbra")],
            ),
            OpenApiParameter(
                name="city",
                description="Name city (example 'Figueira da Foz')",
                required=True,
                type=str,
                examples=[
                    OpenApiExample(
                        "Exemplo de Cidade/Localidade", value="Figueira da Foz"
                    )
                ],
            ),
            OpenApiParameter(
                name="index_day",
                description="Day index (0 = today, 1 = tomorrow, 2 = after tomorrow..., 9 = +9 days)",
                required=True,
                type=int,
                examples=[OpenApiExample("Hoje", value=0)],
            ),
            OpenApiParameter(
                name="use_cache",
                description="Option to use the cache from Django (bool). Default is False.",
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="use_selenium_for_locations",
                description="Option to use selenium for the locations. Default is False (which means we use the URL fragments directly).",
                required=False,
                type=bool,
            ),
        ],
        responses={
            200: OpenApiExample("Forecast", value={"temp_min": "1", "temp_max": "35"})
        },
    )
    def get(self, request, format=None):
        """
        # API to fetch the weather forecast in IPMA website for a give location and a day (today to +9 days).

        ## Query Parameters
        - district (str): Name of the district.

            Must be in Title Case (first letter capitalized, examples: 'Coimbra', 'São Jorge', 'Setúbal'...).
            The API will reject any request with an invalid district.

        - city (str): Name of the city/local (example: 'Figueira da Foz').

            Currently there is no pre-validation of the input city as there are many options, it's better to stick with valid inputs.

            Example: 'Figueira da Foz' for Coimbra, 'Cuba' for Beja etc.

        - index_day (int): Index of the day to fetch forecast for:
                0 = today, 1 = tomorrow, ..., up to 9.

        - use_cache (boolean): Optional parameter, default is False.

            Control the usage of the Django cache. By default, Selenium is used to collect the data.
            If it's set to True then we use the cache to query previous results of a same query...

        - use_selenium_for_locations (boolean): Optional parameter, default is False.

            Control the usage of Selenium to manipulate the locations on the IPMA website. By default, we use a faster approach, that relies on the URL fragments.
            If it's set to True, we will use Selenium to interact with the locations options (slower).

        ## Result
        - JSON with Forecast data including date, temperatures, weather description, and precipitation... Example:


                {
                "forecast": {
                    "district": "Coimbra",
                    "city_selected": "Figueira da Foz",
                    "date": "Quinta, 19",
                    "temp_min": "17°",
                    "temp_max": "28°",
                    "weather": "Aguaceiros e possibilidade de trovoada",
                    "precipitation": "59%",
                    "wind_dir": "NW",
                    "iuv": "IUV: 7"
                },
                "used_cache": false
                }




        ## Additional notes

        ### NOTE 1:
            The parameters 'use_cache' & 'use_selenium_for_locations' are for dev/testing purposes, to be able to test different setups for this small project without modifying the codebase.

        ### NOTE 2:
            There is no additional check being done for city parameter, but unreliable results could appear if the user uses any invalid input.
            So in the current version it's important to use the right city for the right district.
            Specially when using 'use_selenium_for_locations' boolean:
              - as False, and if the city is invalid, the weather output will be for Lisboa/Lisboa...
              - as True, and the city is invalid input, the result will be the default city option for the district provided by IPMA. (Example: Setúbal/Setúbal or Lisboa/Lisboa)



        ### NOTE 3:
            IPMA website only shows the weather for 10 days, so to make things easier, an index (int 0 to 9) is used to select the day, with 0 being "today".
        """

        serializer = ForecastQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        district = serializer.validated_data["district"]
        city = serializer.validated_data["city"]
        index_day = serializer.validated_data["index_day"]
        use_cache = serializer.validated_data.get("use_cache", False)

        use_selenium_for_locations = serializer.validated_data.get(
            "use_selenium_for_locations", False
        )

        if district not in ALLOWED_DISTRICTS:
            return Response(
                {"detail": f"District not OK. Use: {ALLOWED_DISTRICTS}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # TODO: improve on 'city' parameter validation

        try:

            ipma = IpmaWebScriptLib()
            forecast_weather = ipma.run_script(
                district=district,
                city=city,
                day_index=index_day,
                using_cache=use_cache,
                use_selenium_for_locations=use_selenium_for_locations,
            )

            return Response({"forecast": forecast_weather, "used_cache": use_cache})

        except Exception as e:
            return Response(
                {"detail": f"Exception triggered, error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
