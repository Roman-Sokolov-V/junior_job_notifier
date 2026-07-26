# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.
from .conversion_rate import ConversionRateSpider
from .epam import EpamSpider
from .newxel import NewxelSpider
from .star_global import StarGlobalSpider
from .thingsboard import ThingsboardSpider
from .breezy import BreezySpider
from .tieto import TietoSpider
from .anderson import AndersonSpider
from .gen_tech import GenTechSpider
from .svitla import SvitlaSpider



__all__ = [
    ConversionRateSpider,
    EpamSpider,
    NewxelSpider,
    StarGlobalSpider,
    ThingsboardSpider,
    BreezySpider,
    TietoSpider,
    AndersonSpider,
    GenTechSpider,
    SvitlaSpider,
]
